"""
gen_report_test.py
TEST SCRIPT — extends gen_report_live.py with an Alert Summary widget.
Once approved, merge the alert logic into gen_report_live.py.

Extra widget added after ticket detail section:
  - Alert breakdown by Environment × Alert Type
  - Today count | Yesterday count | Last 7-day count
  - Next-day forecast (7-day average)

Alerts are identified by email = notify-sre-ops@corestack.io
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "azure-function"))

import logging
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone, timedelta

import requests

from report_generator import parse_ticket, generate_html, generate_excel
from sharepoint_client import upload_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ── Credentials ────────────────────────────────────────────────────────────────
ZOHO_CLIENT_ID     = os.environ.get("ZOHO_CLIENT_ID",     "1000.LXE6HGZAW4FWRED50ZUZ42CHUFHVEO")
ZOHO_CLIENT_SECRET = os.environ.get("ZOHO_CLIENT_SECRET", "7d84eb43d93d42648ad05636b2b7310652361722e9")
ZOHO_REFRESH_TOKEN = os.environ.get("ZOHO_REFRESH_TOKEN", "1000.ca586bbc38413c0661c0e67e78378449.72ac1952b7eb013374cc87e8544475a4")

SHAREPOINT_TENANT_ID     = os.environ.get("SHAREPOINT_TENANT_ID",     "")
SHAREPOINT_CLIENT_ID     = os.environ.get("SHAREPOINT_CLIENT_ID",     "abb2a8fa-4603-4aff-80b2-bf614beb173b")
SHAREPOINT_CLIENT_SECRET = os.environ.get("SHAREPOINT_CLIENT_SECRET", "")
SHAREPOINT_SITE_URL      = os.environ.get("SHAREPOINT_SITE_URL",      "cloudenablersinc.sharepoint.com/sites/SupportTeam")
SHAREPOINT_HTML_FOLDER   = os.environ.get("SHAREPOINT_HTML_FOLDER",   "General/Daily-Incident-Report/Template")
SHAREPOINT_EXCEL_FOLDER  = os.environ.get("SHAREPOINT_EXCEL_FOLDER",  "General/Daily-Incident-Report/Excel")

try:
    from credentials_zoho import (        # type: ignore
        SHAREPOINT_TENANT_ID     as _T,
        SHAREPOINT_CLIENT_SECRET as _S,
    )
    if _T: SHAREPOINT_TENANT_ID     = _T
    if _S: SHAREPOINT_CLIENT_SECRET = _S
except ImportError:
    pass

os.environ["SHAREPOINT_TENANT_ID"]     = SHAREPOINT_TENANT_ID
os.environ["SHAREPOINT_CLIENT_ID"]     = SHAREPOINT_CLIENT_ID
os.environ["SHAREPOINT_CLIENT_SECRET"] = SHAREPOINT_CLIENT_SECRET
os.environ["SHAREPOINT_SITE_URL"]      = SHAREPOINT_SITE_URL
os.environ["SHAREPOINT_HTML_FOLDER"]   = SHAREPOINT_HTML_FOLDER
os.environ["SHAREPOINT_EXCEL_FOLDER"]  = SHAREPOINT_EXCEL_FOLDER

ZOHO_ORG_ID        = "60019389025"
ZOHO_DEPT_ID       = "100599000000010772"
PENTAGON_ACCOUNT   = "100599000037212179"
ALERT_EMAIL        = "notify-sre-ops@corestack.io"

ZOHO_TOKEN_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_API_BASE  = "https://desk.zoho.in/api/v1"
IST = timedelta(hours=5, minutes=30)


# ── Zoho helpers ───────────────────────────────────────────────────────────────
def get_token() -> str:
    resp = requests.post(ZOHO_TOKEN_URL, params={
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id":     ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type":    "refresh_token",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def hdrs(token: str) -> dict:
    return {"Authorization": f"Zoho-oauthtoken {token}", "orgId": ZOHO_ORG_ID}


def fetch_by_status(status: str, token: str) -> list[dict]:
    tickets, from_ = [], 0
    while True:
        resp = requests.get(f"{ZOHO_API_BASE}/tickets", headers=hdrs(token), params={
            "departmentId": ZOHO_DEPT_ID, "status": status,
            "sortBy": "createdTime", "limit": 50, "from": from_,
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data: break
        tickets.extend(data)
        if len(data) < 50: break
        from_ += 50
    return tickets


def fetch_detail(ticket_id: str, token: str) -> dict:
    resp = requests.get(
        f"{ZOHO_API_BASE}/tickets/{ticket_id}",
        headers=hdrs(token),
        params={"include": "contacts,assignee"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_alerts_for_range(token: str, from_ist: datetime, to_ist: datetime) -> list[dict]:
    """Fetch all alert tickets created in a given IST date range."""
    from_utc = (from_ist - IST).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    to_utc   = (to_ist   - IST).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    tickets, from_ = [], 0
    while True:
        resp = requests.get(f"{ZOHO_API_BASE}/tickets", headers=hdrs(token), params={
            "departmentId":    ZOHO_DEPT_ID,
            "sortBy":          "createdTime",
            "limit":           100,
            "from":            from_,
            "createdTimeRange": f"{from_utc},{to_utc}",
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data: break
        tickets.extend(data)
        if len(data) < 100: break
        from_ += 100
    # Keep only SRE alert tickets
    return [t for t in tickets
            if (t.get("email") or t.get("contactEmail") or "").lower() == ALERT_EMAIL]


# ── Alert parsing ──────────────────────────────────────────────────────────────
_ENV_PATTERNS = [
    (r"prd-us3|us3",                        "US3"),
    (r"prd-us-app|prd-us-web|prd-us\b",     "ProdUS"),
    (r"useast|us4|useast-app|useast-web",   "USEast / US4"),
    (r"prd-eu|prod-eu|eu\.corestack",        "ProdEU"),
    (r"msprod|ms.prod",                      "MSProd"),
    (r"kyndryl",                             "Kyndryl"),
    (r"prodin|prd-in|prod-in",               "ProdIN"),
]

_ALERT_PATTERNS = [
    (r"cpu usage|cpu utilisation|cpu utilization",           "CPU"),
    (r"memory usage|memory utilisation|memory utilization",  "Memory"),
    (r"oomkilled|oom",                                       "OOM"),
    (r"vm availability|availability is below",               "VM Availability"),
    (r"missing service|service.*down",                       "Service Down"),
    (r"url.*down|is down|unreachable",                       "URL Down"),
    (r"disk|storage",                                        "Disk"),
    (r"pod.*restart|restartcount",                           "Pod Restart"),
    (r"db alert|database",                                   "Database"),
]


def parse_alert(subject: str) -> tuple[str, str]:
    """Return (environment, alert_type) from subject line."""
    s = subject.lower()
    env = "Other"
    for pattern, label in _ENV_PATTERNS:
        if re.search(pattern, s):
            env = label
            break
    alert_type = "Other"
    for pattern, label in _ALERT_PATTERNS:
        if re.search(pattern, s):
            alert_type = label
            break
    return env, alert_type


# ── Alert HTML widget ─────────────────────────────────────────────────────────
def build_alert_widget(today_alerts: list, yesterday_alerts: list, week_alerts: list) -> str:
    """Build the HTML alert summary widget."""

    # Count by env × alert_type for each period
    def count_by(alerts):
        counts = defaultdict(lambda: defaultdict(int))
        for t in alerts:
            env, atype = parse_alert(t.get("subject") or "")
            counts[env][atype] += 1
        return counts

    today_c     = count_by(today_alerts)
    yesterday_c = count_by(yesterday_alerts)
    week_c      = count_by(week_alerts)

    # All envs and types seen across all periods
    all_envs   = sorted(set(list(today_c) + list(yesterday_c) + list(week_c)))
    all_types  = sorted(set(
        t for c in [today_c, yesterday_c, week_c] for env in c for t in c[env]
    ))

    if not all_envs:
        return (
            '<tr><td style="padding-bottom:14px;">'
            '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            'style="background:#fff;border:1px solid #E4E8EF;border-radius:10px;">'
            '<tr><td style="background:#F8FAFC;border-bottom:1px solid #E4E8EF;padding:8px 14px;">'
            '<span style="font-size:13px;font-weight:700;color:#0F172A;">&#128680; SRE Alert Summary</span>'
            '</td></tr>'
            '<tr><td style="padding:14px;font-size:12px;color:#64748B;">No alerts recorded today.</td></tr>'
            '</table></td></tr>\n'
        )

    # Forecast = 7-day avg (week count / 7), rounded
    def forecast(env, atype):
        total = week_c.get(env, {}).get(atype, 0)
        return round(total / 7, 1)

    # Summary counts
    n_today     = len(today_alerts)
    n_yesterday = len(yesterday_alerts)
    n_week      = len(week_alerts)
    n_forecast  = round(n_week / 7, 1)

    # Build table rows
    rows = ""
    for i, env in enumerate(all_envs):
        bg = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
        for atype in all_types:
            td = today_c.get(env, {}).get(atype, 0)
            yd = yesterday_c.get(env, {}).get(atype, 0)
            wd = week_c.get(env, {}).get(atype, 0)
            fc = forecast(env, atype)
            if td == 0 and yd == 0 and wd == 0:
                continue
            td_color = "#EF4444" if td > 5 else ("#F59E0B" if td > 2 else "#10B981")
            rows += (
                f'<tr style="background:{bg};">'
                f'<td style="padding:5px 10px;font-size:11px;font-weight:600;color:#334155;border-bottom:1px solid #F1F5F9;">{env}</td>'
                f'<td style="padding:5px 10px;font-size:11px;color:#475569;border-bottom:1px solid #F1F5F9;">{atype}</td>'
                f'<td style="padding:5px 10px;text-align:center;border-bottom:1px solid #F1F5F9;"><span style="font-size:11px;font-weight:700;color:{td_color};">{td}</span></td>'
                f'<td style="padding:5px 10px;text-align:center;font-size:11px;color:#64748B;border-bottom:1px solid #F1F5F9;">{yd}</td>'
                f'<td style="padding:5px 10px;text-align:center;font-size:11px;color:#64748B;border-bottom:1px solid #F1F5F9;">{wd}</td>'
                f'<td style="padding:5px 10px;text-align:center;border-bottom:1px solid #F1F5F9;"><span style="font-size:11px;font-weight:600;color:#8B5CF6;">{fc}</span></td>'
                f'</tr>'
            )

    widget = (
        '<tr><td style="padding-bottom:14px;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="background:#fff;border:1px solid #E4E8EF;border-radius:10px;">'

        # Header
        '<tr><td style="background:#F8FAFC;border-bottom:1px solid #E4E8EF;padding:8px 14px;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="font-size:13px;font-weight:700;color:#0F172A;">&#128680; SRE Alert Summary</td>'
        f'<td align="right">'
        f'<span style="font-size:10px;background:#FEE2E2;color:#B91C1C;padding:2px 8px;border-radius:4px;margin-left:6px;">Today: {n_today}</span>'
        f'<span style="font-size:10px;background:#FEF3C7;color:#B45309;padding:2px 8px;border-radius:4px;margin-left:6px;">Yesterday: {n_yesterday}</span>'
        f'<span style="font-size:10px;background:#DBEAFE;color:#1D4ED8;padding:2px 8px;border-radius:4px;margin-left:6px;">Last 7d: {n_week}</span>'
        f'<span style="font-size:10px;background:#EDE9FE;color:#6D28D9;padding:2px 8px;border-radius:4px;margin-left:6px;">Forecast: ~{n_forecast}/day</span>'
        f'</td>'
        '</tr></table></td></tr>'

        # Table
        '<tr><td><table width="100%" cellpadding="0" cellspacing="0" border="0">'
        '<tr style="background:#F8FAFC;">'
        '<th style="padding:5px 10px;font-size:9px;font-weight:700;color:#94A3B8;text-transform:uppercase;text-align:left;border-bottom:1px solid #E4E8EF;width:18%;">Environment</th>'
        '<th style="padding:5px 10px;font-size:9px;font-weight:700;color:#94A3B8;text-transform:uppercase;text-align:left;border-bottom:1px solid #E4E8EF;width:20%;">Alert Type</th>'
        '<th style="padding:5px 10px;font-size:9px;font-weight:700;color:#94A3B8;text-transform:uppercase;text-align:center;border-bottom:1px solid #E4E8EF;width:12%;">Today</th>'
        '<th style="padding:5px 10px;font-size:9px;font-weight:700;color:#94A3B8;text-transform:uppercase;text-align:center;border-bottom:1px solid #E4E8EF;width:12%;">Yesterday</th>'
        '<th style="padding:5px 10px;font-size:9px;font-weight:700;color:#94A3B8;text-transform:uppercase;text-align:center;border-bottom:1px solid #E4E8EF;width:12%;">Last 7 days</th>'
        '<th style="padding:5px 10px;font-size:9px;font-weight:700;color:#94A3B8;text-transform:uppercase;text-align:center;border-bottom:1px solid #E4E8EF;width:12%;">Forecast (next day)</th>'
        '</tr>'
        + rows +
        '</table></td></tr>'
        '</table></td></tr>\n'
    )
    return widget


def generate_html_with_alerts(tickets, today, excel_url, alert_widget) -> str:
    """Generate the standard HTML and inject the alert widget after the ticket section."""
    html = generate_html(tickets, today, excel_url=excel_url)
    # Inject alert widget just before the Excel footer link
    inject_before = '<tr><td><table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F0F9FF'
    html = html.replace(inject_before, alert_widget + inject_before, 1)
    return html


def is_pentagon(t: dict) -> bool:
    acc = (t.get("account") or {})
    acc_id = acc.get("id") or acc.get("accountId") or t.get("accountId") or ""
    if str(acc_id) == PENTAGON_ACCOUNT: return True
    subj  = (t.get("subject") or "").lower()
    email = (t.get("email") or t.get("contactEmail") or "").lower()
    if "clouddesk@pentagon" in email: return True
    if "[inc-52" in subj and ("request resolved" in subj or "request received" in subj): return True
    return False


def is_alert(t: dict) -> bool:
    email = (t.get("email") or t.get("contactEmail") or "").lower()
    return ALERT_EMAIL in email


def main():
    today_ist = datetime.now(timezone.utc) + IST
    today     = today_ist.date()
    logging.info("Generating TEST report for %s", today)

    token = get_token()
    logging.info("Token obtained.")

    # ── Fetch active incident tickets ─────────────────────────────────────────
    statuses = ["Open", "In Progress", "On Hold", "Awaiting Resolution Confirmation"]
    raw = []
    for s in statuses:
        batch = fetch_by_status(s, token)
        logging.info("  %s: %d tickets", s, len(batch))
        raw.extend(batch)

    raw = [t for t in raw if not is_pentagon(t) and not is_alert(t)]
    logging.info("After filters: %d tickets", len(raw))

    def enrich(t: dict) -> dict:
        tid = t.get("id") or t.get("ticketId") or ""
        if not tid: return t
        try:
            detail = fetch_detail(str(tid), token)
            t["cf"] = detail.get("cf") or {}
            t["customFields"] = detail.get("customFields") or {}
            for f in ("contacts", "contact", "assignee", "account"):
                if detail.get(f): t[f] = detail[f]
            if detail.get("resolution") and not t.get("resolution"):
                t["resolution"] = detail["resolution"]
            if detail.get("ticketType"): t["ticketType"] = detail["ticketType"]
        except Exception as e:
            logging.warning("Detail fetch failed for %s: %s", tid, e)
        return t

    logging.info("Enriching tickets…")
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(enrich, t): t for t in raw}
        enriched = [f.result() for f in as_completed(futures)]
    logging.info("Enrichment done.")

    enriched = [t for t in enriched
                if ((t.get("cf") or {}).get("cf_request_type") or "").lower() in ("incident request", "")]
    logging.info("After incident-only filter: %d tickets", len(enriched))

    tickets = [parse_ticket(t, today) for t in enriched]

    # ── Fetch alert tickets for today / yesterday / last 7 days ───────────────
    logging.info("Fetching SRE alert tickets…")

    def _day_range(d: date):
        start = datetime(d.year, d.month, d.day, 0, 0, 0) + IST
        end   = datetime(d.year, d.month, d.day, 23, 59, 59) + IST
        return start, end

    today_alerts     = fetch_alerts_for_range(token, *_day_range(today))
    yesterday_alerts = fetch_alerts_for_range(token, *_day_range(today - timedelta(days=1)))
    week_alerts      = []
    for i in range(1, 8):
        week_alerts += fetch_alerts_for_range(token, *_day_range(today - timedelta(days=i)))

    logging.info("Alerts — today: %d  yesterday: %d  last 7 days: %d",
                 len(today_alerts), len(yesterday_alerts), len(week_alerts))

    alert_widget = build_alert_widget(today_alerts, yesterday_alerts, week_alerts)

    # ── Generate files ────────────────────────────────────────────────────────
    date_tag   = today.strftime("%Y-%m-%d")
    html_path  = f"CS_Daily_Incident_Report_{date_tag}_TEST.html"
    excel_path = f"CS_Daily_Incident_Report_{date_tag}_TEST.xlsx"

    with open(excel_path, "wb") as f:
        f.write(generate_excel(tickets, today))
    logging.info("Excel written: %s", excel_path)

    sp_html_folder  = os.environ["SHAREPOINT_HTML_FOLDER"]
    sp_excel_folder = os.environ["SHAREPOINT_EXCEL_FOLDER"]
    excel_sp_url = ""
    try:
        logging.info("Uploading Excel to SharePoint…")
        excel_sp_url = upload_file(excel_path, sp_excel_folder, excel_path)
        logging.info("Excel uploaded: %s", excel_sp_url)
    except Exception as e:
        logging.error("SharePoint Excel upload failed: %s", e)

    html_content = generate_html_with_alerts(tickets, today, excel_sp_url, alert_widget)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logging.info("HTML written: %s", html_path)

    try:
        logging.info("Uploading HTML to SharePoint…")
        html_url = upload_file(html_path, sp_html_folder, html_path)
        logging.info("HTML uploaded: %s", html_url)
    except Exception as e:
        logging.error("SharePoint HTML upload failed: %s", e)
        logging.info("Files saved locally.")

    logging.info("Done. %d tickets | Today alerts: %d", len(tickets), len(today_alerts))


if __name__ == "__main__":
    main()
