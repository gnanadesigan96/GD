#!/usr/bin/env python3
"""
CoreStack Platform Performance Report Generator
Single-file: connects OpenVPN, queries all 7 MongoDB environments,
generates HTML + CSV, uploads both to SharePoint, disconnects VPN.

Setup:
  pip install pymongo requests
  sudo apt install openvpn        # or brew install openvpn on macOS

Usage:
  sudo python3 generate_perf_report.py                          # uses default VPN path
  sudo python3 generate_perf_report.py --ovpn /path/to/file.ovpn
  sudo python3 generate_perf_report.py --no-vpn                 # skip VPN (already connected)
  sudo python3 generate_perf_report.py --no-upload              # skip SharePoint upload

Cron (daily 6:30 PM IST = 13:00 UTC):
  0 13 * * * /usr/bin/sudo /usr/bin/python3 /path/to/generate_perf_report.py >> /var/log/perf_report.log 2>&1
"""
import sys
import csv
import html as _html
import os
import signal
import subprocess
import time
import argparse
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient

# ============================================================
#  CONFIGURATION
# ============================================================

OUTPUT_FILE = "corestack-performance-report.html"

# ── OpenVPN ──────────────────────────────────────────────────
OVPN_CONFIG_PATH = "/etc/openvpn/client.ovpn"  # default; override with --ovpn
VPN_CONNECT_TIMEOUT = 60  # seconds to wait for tun0

# ── SharePoint (Microsoft Graph API — client credentials) ───
SHAREPOINT_TENANT_ID     = "<your-azure-tenant-id>"
SHAREPOINT_CLIENT_ID     = "<your-azure-app-client-id>"
SHAREPOINT_CLIENT_SECRET = "<your-azure-app-client-secret>"
SHAREPOINT_SITE_URL      = "cloudenablersinc.sharepoint.com/sites/SupportTeam"
SHAREPOINT_REPORT_FOLDER = "General/Cost-Performance-Report"
SHAREPOINT_CSV_FOLDER    = "General/Cost-Performance-Report/Dump"

GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_BASE      = "https://graph.microsoft.com/v1.0"

# ── MongoDB Environments ────────────────────────────────────
ENVIRONMENTS = {
    "prod_india": {"label": "Prod India", "host": "4.213.1.249",   "port": 27017, "username": "demo", "password": "5dejlcYxqgqo5LEp", "auth_source": "admin"},
    "us_east":    {"label": "US East",    "host": "52.154.142.32",  "port": 27017, "username": "demo", "password": "Fd7Wv5ftLO5}k8",  "auth_source": "admin"},
    "mea":        {"label": "MEA",        "host": "74.162.91.2",    "port": 1200,  "username": "demo", "password": "EcgH1HbgyxXWI8O9","auth_source": "admin"},
    "prod_us":    {"label": "Prod US",    "host": "20.112.121.242", "port": 1200,  "username": "demo", "password": "TY0rwn1skOwtQA9z", "auth_source": "admin"},
    "prod_eu":    {"label": "Prod EU",    "host": "4.180.107.93",    "port": 1200,  "username": "demo", "password": "3av7uJLv7lkBvAl0", "auth_source": "admin"},
    "ms_prod":    {"label": "MSPROD",     "host": "40.76.52.237",   "port": 27017, "username": "demo", "password": "XL6NWKZqTaxBROER", "auth_source": "admin"},
    "us3":        {"label": "US3",        "host": "20.83.185.233",  "port": 27017, "username": "demo", "password": "Vn9kABFChZg0o_h",  "auth_source": "admin"},
}

DB = {
    "billing":   "billing_and_cost_analytics",
    "heatstack": "heatstack",
    "audit":     "audit_log",
}

COLL = {
    "jobs":  "background_jobs",
    "sa":    "service_account_details",
    "audit": "request_audit",
}

FIELD_MAP = {
    "background_job": {
        "payload_type":        "payload.__type",
        "payload_type_value":  "BackgroundJobPayloadForCloudUsageBilling",
        "status":              "status",
        "status_completed":    "Completed",
        "updated_at":          "updated_at",
        "created_at":          "created_at",
        "service_account_id":  "payload.service_account_id",
    },
    "service_account_details": {
        "id":        "_id",
        "tenant_id": "tenant_id",
    },
    "request_audit": {
        "created_at":   "start_time",
        "duration":     "duration",
        "service_name": "executor",
        "user":         "user_name",
        "slow_s":       30,
    },
}

CONN_TIMEOUT_MS = 20000

EXCLUDED_USERS = [
    "admin", "automation_in", "cs-metering",
    "automation_us", "automation_user", "automation_ingram",
    "validation", "qa_test", "apiautomation_produs", "validation2", "qa_user",
    "automation_mea", "venkatesh-in", "ui_automation",
    "saranya_us", "automation_eu", "cs-mahalakshmi", "venkatesh_cloud",
    "gayathri", "cs_adf_pipeline", "maha_us", "maha_testing",
    "qa_automation", "test_in", "test_us", "test_mea", "test_msprod",
]

INTERNAL_USERNAMES = {
    "admin.taylorfarms", "parthu_cs4cs", "cs-vidyasagar",
    "ganeshan-cs-qa", "admin.otsuka", "admin.convergetech", "blackstone",
    "csum.ashok", "satyabrata.chowdhury", "jayven.couch",
    "anaranya.bagchi", "admin.psteam", "cs-kamal",
    "vijay-cs-implement-integ", "cs-gd", "nagalakshmi.n",
    "csum.jawad", "csum.deovrat", "cs-govern", "cs-vn", "cs-udhay",
}

BILLING_PATHS = [
    "/v1/billing_plans",
    "/v1/billing_plans/batch_definitions",
    "/v1/billing_plans/batch_versions",
    "/v1/cost/billing/aggregation/trend",
    "/v1/cost/estimated_cost",
    "/v1/internal/dimension/validate_grouping_rule_filters",
    "/v1/providers/billing/request_aggregate",
    "/v1/providers/billing/request_aggregate_trend",
    "/v1/providers/billing/request_rate_aggregate_trend",
    "/v1/providers/billing/request_usage_aggregate_trend",
    "/v2/billing/aggregation",
    "/v2/billing/aggregation/batch",
    "/v2/billing/aggregation/trend",
    "/v2/billing/extras",
    "/v2/billing/line_items_summary",
    "/v2/billing/platform/tags",
    "/v2/billing/tags",
    "/v2/billing_metrics/batch",
    "/v2/billing_metrics/list",
    "/v2/budget/dashboard/list_cloud_account_type",
    "/v2/budget/view/cloud_account",
    "/v2/budget/view/tenant",
    "/v2/budgets/threshold_alerts/view",
    "/v2/cost_anomaly/billing_cost_anomaly",
    "/v2/cost_anomaly/billing_cost_anomaly_resources",
    "/v3/budget/dashboard",
    "/v3/budget/dashboard/filters",
    "/v3/budget/dashboard/list_budgets",
    "/v3/budget/dashboard/list_currency",
    "/v3/budget/insights",
    "/v2/savings/filter",
    "/v2/savings/summary",
]

ENV_COLORS = {
    "prod_india": "#10b981",
    "us_east":    "#3b82f6",
    "mea":        "#f59e0b",
    "prod_us":    "#ef4444",
    "prod_eu":    "#6366f1",
    "ms_prod":    "#06b6d4",
    "us3":        "#8b5cf6",
}

RAW_DATA_URL = (
    "https://cloudenablersinc.sharepoint.com/sites/SupportTeam/_layouts/15/guestaccess.aspx"
    "?share=IgAOVyAx1g4hSr83T73ZPkgHAXY5Kkg6fhZfYz-6ZXBaYg0&e=mTZjTd"
)


# ============================================================
#  OPENVPN CONNECT / DISCONNECT
# ============================================================

_vpn_process = None


def vpn_connect(ovpn_path: str) -> None:
    global _vpn_process
    if not os.path.isfile(ovpn_path):
        print(f"ERROR: OpenVPN config not found: {ovpn_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[VPN] Starting OpenVPN with {ovpn_path} ...")
    _vpn_process = subprocess.Popen(
        ["openvpn", "--config", ovpn_path, "--writepid", "/tmp/openvpn_report.pid"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    elapsed = 0
    while elapsed < VPN_CONNECT_TIMEOUT:
        result = subprocess.run(
            ["ip", "addr", "show", "tun0"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"[VPN] Connected (tun0 up after {elapsed}s)")
            return
        time.sleep(2)
        elapsed += 2

    print(f"ERROR: VPN did not connect within {VPN_CONNECT_TIMEOUT}s", file=sys.stderr)
    if _vpn_process.stdout:
        out = _vpn_process.stdout.read(4096)
        if out:
            print(out.decode(errors="replace"), file=sys.stderr)
    vpn_disconnect()
    sys.exit(1)


def vpn_disconnect() -> None:
    global _vpn_process
    if _vpn_process:
        print("[VPN] Disconnecting ...")
        _vpn_process.terminate()
        try:
            _vpn_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _vpn_process.kill()
        _vpn_process = None
        print("[VPN] Disconnected")

    pid_file = "/tmp/openvpn_report.pid"
    if os.path.isfile(pid_file):
        try:
            pid = int(open(pid_file).read().strip())
            os.kill(pid, signal.SIGTERM)
        except (ValueError, ProcessLookupError, PermissionError):
            pass
        try:
            os.remove(pid_file)
        except OSError:
            pass


# ============================================================
#  SHAREPOINT UPLOAD (Microsoft Graph API)
# ============================================================

def _get_graph_token() -> str:
    url = GRAPH_TOKEN_URL.format(tenant_id=SHAREPOINT_TENANT_ID)
    resp = requests.post(url, data={
        "client_id":     SHAREPOINT_CLIENT_ID,
        "client_secret": SHAREPOINT_CLIENT_SECRET,
        "scope":         "https://graph.microsoft.com/.default",
        "grant_type":    "client_credentials",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_site_id(token: str) -> str:
    parts = SHAREPOINT_SITE_URL.replace("https://", "").split("/sites/")
    hostname = parts[0]
    site_name = parts[1] if len(parts) > 1 else ""
    resp = requests.get(
        f"{GRAPH_BASE}/sites/{hostname}:/sites/{site_name}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _get_drive_id(token: str, site_id: str) -> str:
    resp = requests.get(
        f"{GRAPH_BASE}/sites/{site_id}/drive",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def upload_to_sharepoint(local_path: str, sp_folder: str, filename: str) -> str:
    token    = _get_graph_token()
    site_id  = _get_site_id(token)
    drive_id = _get_drive_id(token, site_id)
    folder   = sp_folder.lstrip("/")

    with open(local_path, "rb") as fh:
        file_bytes = fh.read()

    file_size = len(file_bytes)

    if file_size > 4 * 1024 * 1024:
        return _upload_large(token, drive_id, folder, filename, file_bytes)

    upload_url = f"{GRAPH_BASE}/drives/{drive_id}/root:/{folder}/{filename}:/content"
    resp = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        },
        data=file_bytes,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("webUrl", "")


def _upload_large(token: str, drive_id: str, folder: str,
                  filename: str, file_bytes: bytes) -> str:
    session_url = (
        f"{GRAPH_BASE}/drives/{drive_id}/root:/{folder}/{filename}"
        f":/createUploadSession"
    )
    resp = requests.post(
        session_url,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
        timeout=30,
    )
    resp.raise_for_status()
    upload_url = resp.json()["uploadUrl"]

    chunk_size = 10 * 1024 * 1024
    total = len(file_bytes)
    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)
        chunk = file_bytes[start:end]
        headers = {
            "Content-Length": str(len(chunk)),
            "Content-Range": f"bytes {start}-{end - 1}/{total}",
        }
        resp = requests.put(upload_url, headers=headers, data=chunk, timeout=120)
        resp.raise_for_status()

    return resp.json().get("webUrl", "")


# ============================================================
#  DATABASE CONNECTION
# ============================================================

def make_client(env_key: str) -> MongoClient:
    cfg = ENVIRONMENTS[env_key]
    if cfg.get("username"):
        uri = (f"mongodb://{cfg['username']}:{cfg['password']}"
               f"@{cfg['host']}:{cfg['port']}"
               f"/?authSource={cfg['auth_source']}&directConnection=true")
    else:
        uri = f"mongodb://{cfg['host']}:{cfg['port']}/?directConnection=true"
    return MongoClient(uri, serverSelectionTimeoutMS=CONN_TIMEOUT_MS,
                       socketTimeoutMS=30000)


def get_field(doc: dict, dotpath: str):
    val = doc
    for part in dotpath.split("."):
        if not isinstance(val, dict):
            return None
        val = val.get(part)
    return val


# ============================================================
#  JOB METRICS  (per environment)
# ============================================================

def get_job_metrics(env_key: str, now: datetime) -> dict:
    jf = FIELD_MAP["background_job"]
    sf = FIELD_MAP["service_account_details"]

    cutoff_24h = now - timedelta(hours=24)
    cutoff_48h = now - timedelta(hours=48)
    n2_window = {jf["created_at"]: {"$gt": cutoff_48h, "$lte": cutoff_24h}}

    result = {
        "env_key": env_key, "label": ENVIRONMENTS[env_key]["label"],
        "total_accts": 0, "completed_24h": 0,
        "tenants_impacted": 0, "n2_pending": 0,
        "older_backlog": 0, "compliance_pct": 0.0, "error": None,
    }
    client = None
    try:
        client = make_client(env_key)
        jobs = client[DB["billing"]][COLL["jobs"]]
        sa_c = client[DB["heatstack"]][COLL["sa"]]

        base = {jf["payload_type"]: jf["payload_type_value"]}

        all_n2_ids  = jobs.distinct(jf["service_account_id"], {**base, **n2_window})
        total_accts = len([x for x in all_n2_ids if x is not None])

        completed_24h = jobs.count_documents({
            **base,
            jf["status"]:     jf["status_completed"],
            jf["updated_at"]: {"$gte": cutoff_24h},
        })

        n2_pending_docs = list(jobs.find(
            {**base,
             jf["status"]:   {"$in": ["Ready", "Pending", "Waiting"]},
             **n2_window},
            {jf["service_account_id"]: 1, "_id": 0},
        ))
        n2_pending_ids = set()
        for doc in n2_pending_docs:
            sa_id = get_field(doc, jf["service_account_id"])
            if sa_id is not None:
                n2_pending_ids.add(sa_id)
        n2_pending = len(n2_pending_ids)

        older_backlog_docs = list(jobs.find(
            {**base,
             jf["status"]:     {"$in": ["Ready", "Pending", "Waiting"]},
             jf["created_at"]: {"$lt": cutoff_48h}},
            {jf["service_account_id"]: 1, "_id": 0},
        ))
        older_backlog_ids = set()
        for doc in older_backlog_docs:
            sa_id = get_field(doc, jf["service_account_id"])
            if sa_id is not None:
                older_backlog_ids.add(sa_id)
        older_backlog = len(older_backlog_docs)

        combined_ids = n2_pending_ids | older_backlog_ids
        tenants_impacted = 0
        if combined_ids:
            sa_docs = list(sa_c.find(
                {sf["id"]: {"$in": list(combined_ids)}},
                {sf["id"]: 1, sf["tenant_id"]: 1},
            ))
            tenant_set = {str(d[sf["tenant_id"]]) for d in sa_docs if d.get(sf["tenant_id"])}
            tenants_impacted = len(tenant_set)

        if total_accts == 0:
            compliance_pct = 0.0
        elif n2_pending == 0:
            compliance_pct = 100.0
        else:
            compliance_pct = round((1 - n2_pending / total_accts) * 100, 1)

        result.update({
            "total_accts":      total_accts,
            "completed_24h":    completed_24h,
            "tenants_impacted": tenants_impacted,
            "n2_pending":       n2_pending,
            "older_backlog":    older_backlog,
            "compliance_pct":   compliance_pct,
        })

    except Exception as exc:
        result["error"] = str(exc)
        print(f"  [WARN] jobs/{env_key}: {exc}", file=sys.stderr)
    finally:
        if client:
            client.close()
    return result


# ============================================================
#  AUDIT METRICS  (per environment)
# ============================================================

def get_audit_metrics(env_key: str, now: datetime) -> dict:
    af         = FIELD_MAP["request_audit"]
    cutoff_24h = now - timedelta(hours=24)

    result = {
        "env_key": env_key, "label": ENVIRONMENTS[env_key]["label"],
        "total_requests": 0, "avg_slow_s": 0.0, "max_s": 0.0,
        "slow_count": 0, "total_users": 0,
        "p95_good": True, "p99_good": True,
        "health": "Good", "error": None,
    }
    client = None
    try:
        client = make_client(env_key)
        coll = client[DB["audit"]][COLL["audit"]]

        time_q = {
            af["created_at"]: {"$gte": cutoff_24h, "$lte": now},
            "executor":  "COST",
            "path":      {"$in": BILLING_PATHS},
            "user_name": {"$exists": True, "$nin": EXCLUDED_USERS},
            "source_ip": {"$ne": "127.0.0.1"},
        }

        def _run_agg(pipeline):
            try:
                return list(coll.aggregate(pipeline, allowDiskUse=True))
            except Exception:
                stripped = [{k: v for k, v in s.items()} for s in pipeline]
                for stage in stripped:
                    if "$group" in stage:
                        stage["$group"].pop("all_users", None)
                return list(coll.aggregate(stripped))

        u_field = f"${af['user']}"
        d_field = f"${af['duration']}"
        agg = _run_agg([
            {"$match": time_q},
            {"$group": {
                "_id":         None,
                "total":       {"$sum": 1},
                "max_ms":      {"$max": d_field},
                "slow_count":  {"$sum": {"$cond": [
                    {"$gte": [d_field, af["slow_s"]]}, 1, 0
                ]}},
                "slow_sum_ms": {"$sum": {"$cond": [
                    {"$gte": [d_field, af["slow_s"]]}, d_field, 0
                ]}},
                "all_users": {"$addToSet": {"$cond": {
                    "if":   {"$gte": [d_field, af["slow_s"]]},
                    "then": u_field,
                    "else": "$$REMOVE",
                }}},
            }},
        ])
        if agg:
            row        = agg[0]
            total      = row.get("total") or 0
            slow_count = row.get("slow_count") or 0
            slow_sum   = row.get("slow_sum_ms") or 0
            all_users  = [u for u in (row.get("all_users") or []) if u]
            avg_slow_s = round(slow_sum / slow_count, 2) if slow_count else 0.0
            health     = "Bad" if slow_count > 0 else "Good"
            p95_good   = (slow_count / total <= 0.05) if total > 0 else True
            p99_good   = (slow_count / total <= 0.01) if total > 0 else True
            result.update({
                "total_requests": total,
                "avg_slow_s":     avg_slow_s,
                "max_s":          round(row.get("max_ms") or 0, 2),
                "slow_count":     slow_count,
                "total_users":    len(all_users),
                "p95_good":       p95_good,
                "p99_good":       p99_good,
                "health":         health,
            })

    except Exception as exc:
        result["error"] = str(exc)
        print(f"  [WARN] audit/{env_key}: {exc}", file=sys.stderr)
    finally:
        if client:
            client.close()
    return result


# ============================================================
#  HTML HELPERS
# ============================================================

def e(v) -> str:
    return _html.escape(str(v) if v is not None else "—")

def fmt_s(seconds: float) -> str:
    if seconds <= 0:    return "0.00s"
    if seconds >= 3600: return f"{seconds/3600:.1f}h"
    if seconds >= 60:   return f"{seconds/60:.1f}m"
    return f"{seconds:.2f}s"

def compliance_color(pct: float) -> str:
    return "#16a34a" if pct >= 98 else ("#d97706" if pct >= 90 else "#dc2626")

def compliance_bg(pct: float) -> str:
    return "#dcfce7" if pct >= 98 else ("#fef3c7" if pct >= 90 else "#fee2e2")

def health_colors(h: str) -> tuple:
    return {"Bad": ("#dc2626", "#fee2e2")}.get(h, ("#16a34a", "#dcfce7"))

def percentile_badge(is_good: bool) -> str:
    fg   = "#16a34a" if is_good else "#dc2626"
    bg   = "#dcfce7" if is_good else "#fee2e2"
    text = "Good"    if is_good else "Bad"
    return (
        f'<span style="background-color:{bg};color:{fg};font-size:11px;'
        f'font-weight:bold;padding:3px 10px;font-family:Arial,Helvetica,sans-serif;">'
        f'{text}</span>'
    )

def env_label_cell(env_key: str, label_text: str) -> str:
    color = ENV_COLORS.get(env_key, "#94a3b8")
    return (
        f'<table cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td width="10" height="10" style="background-color:{color};font-size:1px;line-height:1px;vertical-align:middle;">&nbsp;</td>'
        f'<td style="padding-left:7px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:12px;font-weight:bold;color:#0f172a;white-space:nowrap;">{e(label_text)}</td>'
        f'</tr></table>'
    )

def th_cell(text: str, align: str = "left") -> str:
    return (
        f'<th style="text-align:{align};padding:9px 11px;font-size:10px;font-weight:bold;'
        f'color:#64748b;text-transform:uppercase;letter-spacing:0.4px;'
        f'background-color:#f1f5f9;border-bottom:2px solid #e2e8f0;white-space:nowrap;'
        f'font-family:Arial,Helvetica,sans-serif;">{text}</th>'
    )

def td_cell(text, align: str = "left", color: str = "#334155",
            bold: bool = False, extra: str = "") -> str:
    fw = "bold" if bold else "normal"
    return (
        f'<td style="padding:9px 11px;font-size:12px;text-align:{align};color:{color};'
        f'font-weight:{fw};border-bottom:1px solid #f1f5f9;vertical-align:middle;'
        f'font-family:Arial,Helvetica,sans-serif;{extra}">{text}</td>'
    )

def section_header(num: str, title: str, subtitle: str, color: str = "#6366f1") -> str:
    return f"""<tr><td style="padding:28px 28px 14px;background-color:#ffffff;">
  <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
    <td width="4" style="background-color:{color};font-size:1px;line-height:1px;">&nbsp;</td>
    <td style="padding-left:12px;">
      <p style="margin:0;padding:0;font-size:10px;font-weight:bold;text-transform:uppercase;
                letter-spacing:0.8px;color:{color};font-family:Arial,Helvetica,sans-serif;">{num}</p>
      <p style="margin:3px 0 0;padding:0;font-size:16px;font-weight:bold;color:#0f172a;
                font-family:Arial,Helvetica,sans-serif;">{title}</p>
      <p style="margin:3px 0 0;padding:0;font-size:11px;color:#94a3b8;
                font-family:Arial,Helvetica,sans-serif;">{subtitle}</p>
    </td>
  </tr></table>
</td></tr>"""

def callout_box(border_color: str, bg_color: str,
                title: str, title_color: str,
                body: str,  body_color: str,
                note: str,  note_color: str) -> str:
    note_p = (
        f'<p style="margin:2px 0 0;padding:0;font-size:11px;color:{note_color};'
        f'font-family:Arial,Helvetica,sans-serif;">{note}</p>'
        if note else ""
    )
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>'
        f'<td width="3" style="background-color:{border_color};font-size:1px;line-height:1px;">&nbsp;</td>'
        f'<td style="background-color:{bg_color};padding:10px 14px;">'
        f'<p style="margin:0;padding:0;font-size:10px;font-weight:bold;text-transform:uppercase;'
        f'color:{title_color};font-family:Arial,Helvetica,sans-serif;">{title}</p>'
        f'<p style="margin:4px 0 0;padding:0;font-size:12px;font-weight:bold;color:{body_color};'
        f'font-family:Arial,Helvetica,sans-serif;">{body}</p>'
        f'{note_p}'
        f'</td></tr></table>'
    )

def render_callout_boxes(boxes: list) -> str:
    if not boxes:
        return ""
    rows_html = ""
    for i in range(0, len(boxes), 2):
        left  = boxes[i]
        right = boxes[i + 1] if i + 1 < len(boxes) else None
        if rows_html:
            rows_html += '<tr><td colspan="3" height="8" style="font-size:1px;line-height:1px;">&nbsp;</td></tr>'
        if right:
            rows_html += (
                f'<tr>'
                f'<td width="49%" valign="top">{left}</td>'
                f'<td width="2%" style="font-size:1px;">&nbsp;</td>'
                f'<td width="49%" valign="top">{right}</td>'
                f'</tr>'
            )
        else:
            rows_html += f'<tr><td colspan="3">{left}</td></tr>'
    return (
        f'<tr><td style="padding:14px 28px 0;">'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%">'
        f'{rows_html}'
        f'</table></td></tr>'
    )


# ============================================================
#  SECTION 1 TABLE: Cost Processing Compliance (N-2)
# ============================================================

def build_section1_table(job_results: list) -> str:
    rows = ""
    for jm in job_results:
        env_key = jm["env_key"]

        if jm["error"]:
            rows += (
                f'<tr><td colspan="7" style="padding:10px 12px;font-size:12px;color:#94a3b8;'
                f'border-bottom:1px solid #f1f5f9;font-family:Arial,Helvetica,sans-serif;">'
                f'{e(jm["label"])} &#8212; Error: {e(str(jm["error"])[:120])}'
                f'</td></tr>'
            )
            continue

        cp     = jm["compliance_pct"]
        cp_col = compliance_color(cp)
        cp_bg  = compliance_bg(cp)

        compliance_badge = (
            f'<span style="background-color:{cp_bg};color:{cp_col};font-size:12px;'
            f'font-weight:bold;padding:3px 8px;font-family:Arial,Helvetica,sans-serif;">'
            f'{cp}%</span>'
        )

        pending_col = "#dc2626" if jm["n2_pending"] > 0 else "#334155"
        backlog_col = "#d97706" if jm["older_backlog"] > 0 else "#334155"

        rows += (
            f'<tr>'
            f'<td style="padding:9px 11px;border-bottom:1px solid #f1f5f9;vertical-align:middle;">'
            f'{env_label_cell(env_key, jm["label"])}'
            f'</td>'
            f'{td_cell(str(jm["total_accts"]),     "center", "#334155", bold=True)}'
            f'{td_cell(str(jm["completed_24h"]),   "center")}'
            f'{td_cell(str(jm["tenants_impacted"]),"center")}'
            f'{td_cell(str(jm["n2_pending"]),      "center", pending_col, bold=jm["n2_pending"] > 0)}'
            f'{td_cell(str(jm["older_backlog"]),   "center", backlog_col, bold=jm["older_backlog"] > 0)}'
            f'<td style="padding:9px 11px;border-bottom:1px solid #f1f5f9;vertical-align:middle;">'
            f'{compliance_badge}</td>'
            f'</tr>'
        )

    return (
        f'<tr><td style="padding:0 28px;">'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%"'
        f' style="border-collapse:collapse;border:1px solid #e2e8f0;">'
        f'<thead><tr>'
        f'{th_cell("Environment")}'
        f'{th_cell("Total Accts", "center")}'
        f'{th_cell("Completed Jobs 24h", "center")}'
        f'{th_cell("Tenants Impacted", "center")}'
        f'{th_cell("Pending (N-2) Accts", "center")}'
        f'{th_cell("Older Backlog", "center")}'
        f'{th_cell("Compliance %", "center")}'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table></td></tr>'
    )


def build_section1_callouts(job_results: list) -> str:
    valid = [jm for jm in job_results if not jm["error"]]
    if not valid:
        return ""

    critical_envs = [jm for jm in valid if jm["compliance_pct"] < 90]
    warning_envs  = [jm for jm in valid if 90 <= jm["compliance_pct"] < 98]
    good_envs     = [jm for jm in valid if jm["compliance_pct"] >= 98]
    most_backlog  = max(valid, key=lambda x: x["older_backlog"])

    boxes = []

    if critical_envs:
        names = ", ".join(jm["label"] for jm in critical_envs)
        boxes.append(callout_box(
            "#dc2626", "#fee2e2", "Critical Compliance", "#dc2626",
            e(names), "#7f1d1d",
            "Compliance below 90% - immediate attention required", "#991b1b",
        ))

    if warning_envs:
        names = ", ".join(jm["label"] for jm in warning_envs)
        boxes.append(callout_box(
            "#d97706", "#fef3c7", "Warning - Elevated Pending", "#d97706",
            e(names), "#78350f",
            "Compliance 90-97% - monitor closely", "#92400e",
        ))

    if good_envs and not critical_envs and not warning_envs:
        boxes.append(callout_box(
            "#16a34a", "#dcfce7", "All Environments Healthy", "#16a34a",
            f"All {len(good_envs)} environments at 98%+ compliance", "#14532d",
            "", "",
        ))

    if most_backlog["older_backlog"] > 0:
        boxes.append(callout_box(
            "#f59e0b", "#fef3c7", "Largest Older Backlog", "#d97706",
            e(most_backlog["label"]), "#78350f",
            f"{most_backlog['older_backlog']} jobs older than 48h still queued", "#92400e",
        ))

    return render_callout_boxes(boxes)


# ============================================================
#  SECTION 2 TABLE: Dashboard & Service Performance
# ============================================================

def build_section2_table(audit_results: list) -> str:
    rows = ""
    for am in audit_results:
        env_key = am["env_key"]

        if am["error"]:
            rows += (
                f'<tr><td colspan="8" style="padding:10px 12px;font-size:12px;color:#94a3b8;'
                f'border-bottom:1px solid #f1f5f9;font-family:Arial,Helvetica,sans-serif;">'
                f'{e(am["label"])} &#8212; Error: {e(str(am["error"])[:120])}'
                f'</td></tr>'
            )
            continue

        slow_col   = "#dc2626" if am["slow_count"] > 0 else "#16a34a"
        slow_bg    = "#fee2e2" if am["slow_count"] > 0 else "#dcfce7"
        slow_badge = (
            f'<span style="background-color:{slow_bg};color:{slow_col};font-size:11px;'
            f'font-weight:bold;padding:3px 10px;font-family:Arial,Helvetica,sans-serif;">'
            f'{am["slow_count"]}</span>'
        )

        avg_slow_display = fmt_s(am["avg_slow_s"]) if am["slow_count"] > 0 else "&#8212;"
        avg_slow_color   = "#d97706" if am["slow_count"] > 0 else "#94a3b8"
        users_col        = "#334155"
        max_col          = "#dc2626" if am["max_s"] >= 30 else "#334155"

        rows += (
            f'<tr>'
            f'<td style="padding:9px 11px;border-bottom:1px solid #f1f5f9;vertical-align:middle;">'
            f'{env_label_cell(env_key, am["label"])}'
            f'</td>'
            f'{td_cell(str(am["total_requests"]),  "center")}'
            f'{td_cell(avg_slow_display,           "center", avg_slow_color)}'
            f'{td_cell(fmt_s(am["max_s"]),         "center", max_col)}'
            f'{td_cell(str(am["total_users"]),     "center", users_col)}'
            f'<td style="padding:9px 11px;border-bottom:1px solid #f1f5f9;'
            f'vertical-align:middle;text-align:center;">{slow_badge}</td>'
            f'<td style="padding:9px 11px;border-bottom:1px solid #f1f5f9;'
            f'vertical-align:middle;text-align:center;">{percentile_badge(am["p95_good"])}</td>'
            f'<td style="padding:9px 11px;border-bottom:1px solid #f1f5f9;'
            f'vertical-align:middle;text-align:center;">{percentile_badge(am["p99_good"])}</td>'
            f'</tr>'
        )

    return (
        f'<tr><td style="padding:0 28px;">'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%"'
        f' style="border-collapse:collapse;border:1px solid #e2e8f0;">'
        f'<thead><tr>'
        f'{th_cell("Environment")}'
        f'{th_cell("Total Requests", "center")}'
        f'{th_cell("Avg Slow Duration", "center")}'
        f'{th_cell("Max Duration", "center")}'
        f'{th_cell("Total Users Impacted", "center")}'
        f'{th_cell("Slow Req (&ge;30s)", "center")}'
        f'{th_cell("P95 (&lt;30s)", "center")}'
        f'{th_cell("P99 (&lt;30s)", "center")}'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table></td></tr>'
    )


def build_section2_callouts(audit_results: list) -> str:
    valid = [am for am in audit_results if not am["error"]]
    if not valid:
        return ""

    p95_bad_envs = [am for am in valid if not am["p95_good"]]
    p99_bad_envs = [am for am in valid if not am["p99_good"]]
    all_good     = all(am["p95_good"] and am["p99_good"] for am in valid)
    most_users   = max(valid, key=lambda x: x["total_users"])

    boxes = []

    if p95_bad_envs:
        names = ", ".join(am["label"] for am in p95_bad_envs)
        boxes.append(callout_box(
            "#dc2626", "#fee2e2", "P95 Threshold Exceeded", "#dc2626",
            e(names), "#7f1d1d",
            "More than 5% of requests exceeded the 30s threshold in the last 24h", "#991b1b",
        ))

    if p99_bad_envs:
        names = ", ".join(am["label"] for am in p99_bad_envs)
        boxes.append(callout_box(
            "#f59e0b", "#fef3c7", "P99 Threshold Exceeded", "#d97706",
            e(names), "#78350f",
            "More than 1% of requests exceeded the 30s threshold in the last 24h", "#92400e",
        ))

    if all_good:
        boxes.append(callout_box(
            "#16a34a", "#dcfce7", "All Services Healthy", "#16a34a",
            "P95 and P99 within threshold across all environments", "#14532d",
            "", "",
        ))

    if most_users["total_users"] > 0:
        boxes.append(callout_box(
            "#dc2626", "#fee2e2", "Total Users Impacted", "#dc2626",
            e(most_users["label"]), "#7f1d1d",
            f"{most_users['total_users']} distinct user(s) experienced slow requests (&ge;30s)", "#991b1b",
        ))

    return render_callout_boxes(boxes)


# ============================================================
#  GLOSSARY
# ============================================================

def build_glossary() -> str:
    terms = [
        ("Total Accts",
         "Cloud accounts that had billing jobs in the 24-48h window (N-2 period)."),
        ("Pending (N-2) Accts",
         "Cloud accounts whose jobs are still in Ready/Pending/Waiting state in the 24-48h window."),
        ("Older Backlog",
         "Jobs older than 48h still stuck in Ready/Pending/Waiting — not yet processed."),
        ("Compliance %",
         "Formula: (1 - Pending N-2 Accts / Total Accts) x 100. Shows what percentage of accounts have completed their billing jobs. Higher is better. 100% when no pending accounts."),
        ("Avg Slow Duration",
         "Average response time of COST billing requests that exceeded the 30s threshold. Shown only when slow requests exist. Based on last 24h data."),
        ("Max Duration (sec)",
         "The highest single request duration (in seconds) recorded among all filtered COST billing-path requests in the last 24h. Displayed in red when &ge; 30s."),
        ("Total Users Impacted",
         "Distinct users (both customer and internal CoreStack users combined) who experienced at least one slow COST request (&ge;30s) in the last 24h. Source IP 127.0.0.1 and automation accounts excluded."),
        ("Slow Req (&ge;30s)",
         "Count of COST billing API requests where response time was 30 seconds or more in the last 24h. Green badge = 0 slow; Red badge = slow requests detected."),
        ("P95 (&lt;30s)",
         "Percentile check: Good (green) if 95% or more of all requests completed in under 30s (i.e. at most 5% were slow). Bad (red) if more than 5% of requests exceeded 30s."),
        ("P99 (&lt;30s)",
         "Percentile check: Good (green) if 99% or more of all requests completed in under 30s (i.e. at most 1% were slow). Bad (red) if more than 1% of requests exceeded 30s."),
    ]

    term_rows = ""
    for i, (term, desc) in enumerate(terms):
        bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
        term_rows += (
            f'<tr style="background-color:{bg};">'
            f'<td width="190" style="padding:7px 14px;font-size:11px;font-weight:bold;color:#475569;'
            f'white-space:nowrap;border-bottom:1px solid #f1f5f9;vertical-align:top;'
            f'font-family:Arial,Helvetica,sans-serif;">{term}</td>'
            f'<td style="padding:7px 14px;font-size:11px;color:#64748b;'
            f'border-bottom:1px solid #f1f5f9;font-family:Arial,Helvetica,sans-serif;">{desc}</td>'
            f'</tr>'
        )

    return (
        f'<tr><td style="padding:20px 28px 0;">'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>'
        f'<td width="3" style="background-color:#cbd5e1;font-size:1px;line-height:1px;">&nbsp;</td>'
        f'<td style="padding-left:8px;">'
        f'<p style="margin:0;padding:0;font-size:10px;font-weight:bold;text-transform:uppercase;'
        f'letter-spacing:0.6px;color:#94a3b8;font-family:Arial,Helvetica,sans-serif;">Glossary</p>'
        f'</td></tr></table>'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%">'
        f'<tr><td height="8" style="font-size:1px;line-height:1px;">&nbsp;</td></tr></table>'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%"'
        f' style="border-collapse:collapse;border:1px solid #e2e8f0;">'
        f'<tbody>{term_rows}</tbody>'
        f'</table>'
        f'</td></tr>'
    )


def build_raw_data_link() -> str:
    return (
        f'<tr><td style="padding:16px 28px 0;">'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>'
        f'<td width="3" style="background-color:#3b82f6;font-size:1px;line-height:1px;">&nbsp;</td>'
        f'<td style="background-color:#eff6ff;padding:10px 14px;">'
        f'<p style="margin:0;padding:0;font-size:10px;font-weight:bold;text-transform:uppercase;'
        f'letter-spacing:0.6px;color:#1d4ed8;font-family:Arial,Helvetica,sans-serif;">Raw Data Reference</p>'
        f'<p style="margin:4px 0 0;padding:0;font-size:12px;color:#1e40af;'
        f'font-family:Arial,Helvetica,sans-serif;">'
        f'<a href="{RAW_DATA_URL}" style="color:#1d4ed8;text-decoration:underline;'
        f'font-family:Arial,Helvetica,sans-serif;">'
        f'Click here to access the raw data dump on SharePoint</a>'
        f'</p>'
        f'</td></tr></table>'
        f'</td></tr>'
    )


# ============================================================
#  FULL HTML ASSEMBLER
# ============================================================

def build_html(now: datetime, job_results: list, audit_results: list) -> str:
    ist_now     = now + timedelta(hours=5, minutes=30)
    gen_time    = ist_now.strftime("%d %b %Y, %I:%M %p IST")
    report_date = ist_now.strftime("%A, %d %B %Y")

    header = (
        f'<tr><td style="background-color:#1a4080;padding:26px 32px 22px;">'
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%">'
        f'<tr><td>'
        f'<p style="margin:0;padding:0;font-size:24px;font-weight:bold;color:#ffffff;'
        f'font-family:Arial,Helvetica,sans-serif;">CoreStack Platform Performance Report</p>'
        f'<p style="margin:16px 0 0;padding:0;">'
        f'<span style="background-color:#1e50a0;color:#bfdbfe;font-size:11px;font-weight:bold;'
        f'padding:4px 10px;font-family:Arial,Helvetica,sans-serif;">{report_date}</span>'
        f'&nbsp;&nbsp;'
        f'<span style="background-color:#1e50a0;color:#bfdbfe;font-size:11px;font-weight:bold;'
        f'padding:4px 10px;font-family:Arial,Helvetica,sans-serif;">{len(ENVIRONMENTS)} Environments</span>'
        f'&nbsp;&nbsp;'
        f'<span style="background-color:#1e50a0;color:#bfdbfe;font-size:11px;font-weight:bold;'
        f'padding:4px 10px;font-family:Arial,Helvetica,sans-serif;">Generated: {gen_time}</span>'
        f'</p>'
        f'</td></tr>'
        f'</table></td></tr>'
    )

    s1_header = section_header(
        "Section 01", "Dashboard &amp; Service Performance",
        "API request health &mdash; Slow threshold &ge;30s &middot; Last 24h"
        " &nbsp;|&nbsp; P95: Good = &le;5% slow &nbsp;|&nbsp; P99: Good = &le;1% slow",
        "#06b6d4",
    )
    s1_table    = build_section2_table(audit_results)
    s1_callouts = build_section2_callouts(audit_results)

    s2_header = section_header(
        "Section 02", "Cost Processing Compliance (N-2)",
        "N-2 window = jobs created between 24h and 48h ago"
        " &nbsp;|&nbsp; Compliance % = ( 1 &minus; Pending N-2 Accts &divide; Total Accts ) &times; 100",
        "#6366f1",
    )
    s2_table    = build_section1_table(job_results)
    s2_callouts = build_section1_callouts(job_results)

    glossary      = build_glossary()
    raw_data_link = build_raw_data_link()

    footer = (
        f'<tr><td style="background-color:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 28px;">'
        f'<p style="margin:0;padding:0;font-size:12px;font-weight:bold;color:#64748b;'
        f'font-family:Arial,Helvetica,sans-serif;">CoreStack &middot; Cloud Operations Intelligence</p>'
        f'<p style="margin:6px 0 0;padding:0;font-size:11px;color:#94a3b8;line-height:1.7;'
        f'font-family:Arial,Helvetica,sans-serif;">'
        f'Automated daily report &middot; Generated: {gen_time}<br />'
        f'N-2 = jobs created 24h&ndash;48h ago &middot; Older Backlog = jobs &gt;48h old, still queued &middot; Slow = request &ge;30s<br />'
        f'<strong>Section 1 filter:</strong> executor=COST &middot; cost/billing endpoints only'
        f' &middot; authenticated real users only (system &amp; automation accounts excluded)'
        f' &middot; source_ip 127.0.0.1 excluded<br />'
        f'P95 Good = &le;5% of requests slow &middot; P99 Good = &le;1% of requests slow'
        f' &middot; Total Users Impacted = distinct users (customer &amp; internal) who experienced slow requests (&ge;30s)'
        f'</p>'
        f'</td></tr>'
    )

    spacer = '<tr><td height="24" style="height:24px;font-size:1px;line-height:1px;">&nbsp;</td></tr>'

    return (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n'
        '  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" lang="en">\n'
        '<head>\n'
        '  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n'
        f'  <title>CoreStack Platform Performance Report - {report_date}</title>\n'
        '</head>\n'
        '<body style="margin:0;padding:0;background-color:#e8edf2;'
        'font-family:Arial,Helvetica,sans-serif;">\n'
        '<table cellpadding="0" cellspacing="0" border="0" width="100%"'
        ' style="width:100%;background-color:#e8edf2;">\n'
        '<tr><td align="center" style="padding:20px 12px 40px;">\n'
        '<table cellpadding="0" cellspacing="0" border="0" width="980"'
        ' style="width:980px;background-color:#ffffff;">\n'
        f'{header}\n'
        f'{s1_header}\n'
        f'{s1_table}\n'
        f'{s1_callouts}\n'
        f'{spacer}\n'
        f'{s2_header}\n'
        f'{s2_table}\n'
        f'{s2_callouts}\n'
        f'{glossary}\n'
        f'{raw_data_link}\n'
        f'{spacer}\n'
        f'{footer}\n'
        '</table>\n'
        '</td></tr></table>\n'
        '</body>\n'
        '</html>'
    )


# ============================================================
#  RAW DATA EXPORT
# ============================================================

def get_audit_raw_data(env_key: str, now: datetime) -> list:
    af         = FIELD_MAP["request_audit"]
    cutoff_24h = now - timedelta(hours=24)
    slow_s     = af["slow_s"]
    ist_offset = timedelta(hours=5, minutes=30)
    label      = ENVIRONMENTS[env_key]["label"]

    rows   = []
    client = None
    try:
        client = make_client(env_key)
        coll   = client[DB["audit"]][COLL["audit"]]

        time_q = {
            af["created_at"]: {"$gte": cutoff_24h, "$lte": now},
            "executor":  "COST",
            "path":      {"$in": BILLING_PATHS},
            "user_name": {"$exists": True, "$nin": EXCLUDED_USERS},
            "source_ip": {"$ne": "127.0.0.1"},
        }

        projection = {
            "user_name": 1, "user_id": 1, "executor": 1, "path": 1,
            "method": 1, "status_code": 1, "duration": 1,
            "start_time": 1, "end_time": 1, "source_ip": 1,
            "request_id": 1, "_id": 0,
        }

        for doc in coll.find(time_q, projection).sort("start_time", 1):
            dur   = doc.get("duration") or 0
            st    = doc.get("start_time")
            et    = doc.get("end_time")
            uname = doc.get("user_name", "")
            is_internal = (
                uname.startswith("cs.") or
                uname.lower().endswith("@corestack.io") or
                uname in INTERNAL_USERNAMES
            )
            rows.append({
                "environment":    label,
                "user_name":      uname,
                "user_type":      "Internal" if is_internal else "External",
                "user_id":        str(doc.get("user_id", "")),
                "executor":       doc.get("executor", ""),
                "path":           doc.get("path", ""),
                "method":         doc.get("method", ""),
                "status_code":    doc.get("status_code", ""),
                "duration_sec":   round(dur, 4),
                "is_slow":        "Yes" if dur >= slow_s else "No",
                "start_time_ist": (st + ist_offset).strftime("%Y-%m-%d %H:%M:%S") if st else "",
                "end_time_ist":   (et + ist_offset).strftime("%Y-%m-%d %H:%M:%S") if et else "",
                "source_ip":      doc.get("source_ip", ""),
                "request_id":     doc.get("request_id", ""),
            })
    except Exception as exc:
        print(f"  [WARN] raw_data/{env_key}: {exc}", file=sys.stderr)
    finally:
        if client:
            client.close()
    return rows


CSV_FIELDS = [
    "environment", "user_name", "user_type", "user_id", "executor", "path",
    "method", "status_code", "duration_sec", "is_slow",
    "start_time_ist", "end_time_ist", "source_ip", "request_id",
]


# ============================================================
#  MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="CoreStack Performance Report")
    parser.add_argument("--ovpn", default=OVPN_CONFIG_PATH,
                        help="Path to .ovpn config file (default: /etc/openvpn/client.ovpn)")
    parser.add_argument("--no-vpn", action="store_true",
                        help="Skip VPN connect/disconnect (use if already connected)")
    parser.add_argument("--no-upload", action="store_true",
                        help="Skip SharePoint upload (just generate files locally)")
    args = parser.parse_args()

    now = datetime.utcnow()
    ist = now + timedelta(hours=5, minutes=30)
    print("=" * 60)
    print("CoreStack Platform Performance Report Generator")
    print(f"Time  : {ist.strftime('%d %b %Y %I:%M %p IST')}")
    print(f"Envs  : {list(ENVIRONMENTS.keys())}")
    print(f"VPN   : {'skip' if args.no_vpn else args.ovpn}")
    print(f"Upload: {'skip' if args.no_upload else 'SharePoint'}")
    print("=" * 60)
    print()

    # ── Step 1: Connect VPN ──────────────────────────────────
    if not args.no_vpn:
        vpn_connect(args.ovpn)
        print()

    try:
        # ── Step 2: Gather metrics ───────────────────────────
        job_results   = []
        audit_results = []

        for env_key in ENVIRONMENTS:
            print(f"  [{env_key}] jobs  ...", end=" ", flush=True)
            jm = get_job_metrics(env_key, now)
            job_results.append(jm)
            if jm["error"]:
                print(f"ERROR: {jm['error'][:70]}")
            else:
                print(f"total_accts={jm['total_accts']}  "
                      f"n2_pending={jm['n2_pending']}  "
                      f"backlog={jm['older_backlog']}  "
                      f"compliance={jm['compliance_pct']}%")

            print(f"  [{env_key}] audit ...", end=" ", flush=True)
            am = get_audit_metrics(env_key, now)
            audit_results.append(am)
            if am["error"]:
                print(f"ERROR: {am['error'][:70]}")
            else:
                print(f"requests={am['total_requests']}  "
                      f"slow={am['slow_count']}  "
                      f"total_users={am['total_users']}  "
                      f"p95={'Good' if am['p95_good'] else 'Bad'}  "
                      f"p99={'Good' if am['p99_good'] else 'Bad'}")

        # ── Step 3: Build HTML ───────────────────────────────
        print()
        print("Building HTML ...")
        final_html = build_html(now, job_results, audit_results)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(final_html)

        kb = len(final_html.encode()) // 1024
        print(f"Written -> {OUTPUT_FILE}  ({kb} KB)")

        # ── Step 4: Build CSV ────────────────────────────────
        print()
        print("Exporting Section 1 raw data CSV ...")
        csv_name = f"corestack_section1_raw_{ist.strftime('%d%b%Y_%I%M%p')}.csv"
        all_rows = []
        for env_key in ENVIRONMENTS:
            print(f"  [{env_key}] raw data ...", end=" ", flush=True)
            rows = get_audit_raw_data(env_key, now)
            all_rows.extend(rows)
            print(f"{len(rows)} records")

        with open(csv_name, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"Written -> {csv_name}  ({len(all_rows)} total records)")

    finally:
        # ── Step 5: Disconnect VPN ───────────────────────────
        if not args.no_vpn:
            print()
            vpn_disconnect()

    # ── Step 6: Upload to SharePoint ─────────────────────────
    if not args.no_upload:
        print()
        print("Uploading to SharePoint ...")
        try:
            print(f"  HTML -> {SHAREPOINT_REPORT_FOLDER}/{OUTPUT_FILE}")
            html_url = upload_to_sharepoint(OUTPUT_FILE, SHAREPOINT_REPORT_FOLDER, OUTPUT_FILE)
            print(f"  OK: {html_url}")

            print(f"  CSV  -> {SHAREPOINT_CSV_FOLDER}/{csv_name}")
            csv_url = upload_to_sharepoint(csv_name, SHAREPOINT_CSV_FOLDER, csv_name)
            print(f"  OK: {csv_url}")
        except Exception as exc:
            print(f"  [ERROR] SharePoint upload failed: {exc}", file=sys.stderr)

    # ── Summary ──────────────────────────────────────────────
    print()
    print("Summary:")
    for jm in job_results:
        if jm["error"]:
            print(f"  {jm['label']:<14} ERROR")
        else:
            print(f"  {jm['label']:<14} total={jm['total_accts']}  "
                  f"pending={jm['n2_pending']}  compliance={jm['compliance_pct']}%")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
