"""
Blackstone Daily Scrum Report Generator
Fetches data from:
  - Azure DevOps (work items tagged Blackstone)
  - Pendo (visitor engagement for Blackstone segment)
  - Platform metrics (pluggable — fill in your source)

Usage:
  python3 blackstone_scrum.py

Required env vars (or edit the CONFIG block below):
  ADO_PAT          - Azure DevOps Personal Access Token (Work Items: Read)
  PENDO_API_KEY    - Pendo Integration key (Settings > Integrations > Integration keys)
  PENDO_SEGMENT_ID_EU      - Pendo segment ID for Blackstone EU
  PENDO_SEGMENT_ID_USEAST  - Pendo segment ID for Blackstone USEast
"""

import os
import base64
import json
import datetime
import requests

# ─── CONFIG ──────────────────────────────────────────────────────────────────

ADO_ORG     = "CoreStack-Tech"
ADO_PROJECT = "Product_Mgmt"
ADO_PAT     = os.environ.get("ADO_PAT", "YOUR_PAT_HERE")  # <-- paste your PAT here

PENDO_API_KEY           = os.environ.get("PENDO_API_KEY", "YOUR_PENDO_API_KEY")  # <-- paste your key here
PENDO_SUBSCRIPTION_ID   = "5122158603141120"
PENDO_SEGMENT_ID_USEAST = "dJzveERO2XLsAMSv8nEAKmftlVQ"
PENDO_SEGMENT_ID_EU     = os.environ.get("PENDO_SEGMENT_ID_EU", "YOUR_EU_SEGMENT_ID")   # <-- add EU segment ID if separate

# Exclude this visitor from all counts (internal support account)
PENDO_EXCLUDED_EMAIL = "cs.support.blackstone@corestack.io"

# Report date window for Pendo (last N days)
PENDO_WINDOW_DAYS = 3

# ─── ADO ─────────────────────────────────────────────────────────────────────

def ado_headers():
    token = base64.b64encode(f":{ADO_PAT}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }

def fetch_ado_blackstone_incidents():
    """
    Runs a WIQL query to fetch all active Blackstone work items.
    Filters by tag = 'Blackstone' and state != Closed/Removed.
    Returns list of dicts with id, title, assignedTo, state, priority, tags, workItemType.
    """
    if ADO_PAT == "YOUR_PAT_HERE":
        # Return fake data so the script runs without a real PAT
        return _fake_ado_data()

    url = f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_apis/wit/wiql?api-version=7.1"

    wiql = {
        "query": """
            SELECT [System.Id], [System.Title], [System.AssignedTo],
                   [System.State], [Microsoft.VSTS.Common.Priority],
                   [System.Tags], [System.WorkItemType],
                   [System.AreaPath]
            FROM WorkItems
            WHERE [System.TeamProject] = @project
              AND [System.Tags] CONTAINS 'Blackstone'
              AND [System.State] NOT IN ('Closed', 'Removed', 'Done')
            ORDER BY [Microsoft.VSTS.Common.Priority] ASC,
                     [System.ChangedDate] DESC
        """
    }

    resp = requests.post(url, headers=ado_headers(), json=wiql)
    resp.raise_for_status()
    ids = [str(item["id"]) for item in resp.json().get("workItems", [])]

    if not ids:
        return []

    # Batch fetch details (max 200 per call)
    details_url = (
        f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_apis/wit/workitems"
        f"?ids={','.join(ids[:200])}"
        f"&fields=System.Id,System.Title,System.AssignedTo,System.State,"
        f"Microsoft.VSTS.Common.Priority,System.Tags,System.WorkItemType,System.AreaPath"
        f"&api-version=7.1"
    )
    resp2 = requests.get(details_url, headers=ado_headers())
    resp2.raise_for_status()

    results = []
    for wi in resp2.json().get("value", []):
        f = wi["fields"]
        assigned = f.get("System.AssignedTo", {})
        results.append({
            "id":           wi["id"],
            "title":        f.get("System.Title", ""),
            "assignedTo":   assigned.get("displayName", "Unassigned") if isinstance(assigned, dict) else str(assigned),
            "state":        f.get("System.State", ""),
            "priority":     f.get("Microsoft.VSTS.Common.Priority", ""),
            "tags":         f.get("System.Tags", ""),
            "workItemType": f.get("System.WorkItemType", ""),
            "areaPath":     f.get("System.AreaPath", ""),
        })
    return results

def _fake_ado_data():
    """Placeholder data — remove once ADO_PAT is set."""
    return [
        {
            "id": 134003,
            "title": "Assessment Report UI Error Despite Successful Report Generation",
            "assignedTo": "Zubair",
            "state": "In Progress",
            "priority": 2,
            "tags": "Blackstone; Analytics",
            "workItemType": "Bug",
            "areaPath": "Product_Mgmt\\Analytics",
        },
        {
            "id": 131077,
            "title": "Blackstone - Rover - Forecast data missing",
            "assignedTo": "Aadhithya Shanmugapriyan",
            "state": "Active",
            "priority": 2,
            "tags": "Blackstone; FinOps",
            "workItemType": "Bug",
            "areaPath": "Product_Mgmt\\FinOps",
        },
        {
            "id": 131076,
            "title": "Blackstone - RBAC permission issue on tenant view",
            "assignedTo": "Aadhithya Shanmugapriyan",
            "state": "Active",
            "priority": 3,
            "tags": "Blackstone; Core",
            "workItemType": "Bug",
            "areaPath": "Product_Mgmt\\Core",
        },
    ]

def bundle_from_area(area_path: str) -> str:
    mapping = {
        "FinOps": "FinOps",
        "Analytics": "Analytics",
        "CloudOps": "CloudOps",
        "Core": "Core",
    }
    for key, val in mapping.items():
        if key.lower() in area_path.lower():
            return val
    return "—"

# ─── PENDO ───────────────────────────────────────────────────────────────────

def pendo_headers():
    return {
        "x-pendo-integration-key": PENDO_API_KEY,
        "Content-Type": "application/json",
    }

def fetch_pendo_segment_visitors(segment_id: str, window_days: int = PENDO_WINDOW_DAYS):
    """
    Fetches visitors in a Pendo segment with engagement metrics for the last N days.
    Returns list of dicts per visitor.

    NOTE: Fill in PENDO_API_KEY and segment IDs to activate.
    """
    if PENDO_API_KEY == "YOUR_PENDO_API_KEY":
        return _fake_pendo_visitors()

    end_ms   = int(datetime.datetime.utcnow().timestamp() * 1000)
    start_ms = end_ms - (window_days * 86400 * 1000)

    url = "https://app.pendo.io/api/v1/aggregation"
    payload = {
        "response": {"mimeType": "application/json"},
        "request": {
            "pipeline": [
                {
                    "identified": {
                        "visitor": True,
                        "segmentId": segment_id,
                    }
                },
                {
                    "select": {
                        "visitorId":  "visitorId",
                        "email":      "visitor.email",
                        "lastName":   "visitor.lastName",
                        "firstName":  "visitor.firstName",
                        "domain":     "visitor.accountId",
                        "lastSeenAt": "visitor.lastSeenAt",
                    }
                },
                {
                    "join": {
                        "kind": "left",
                        "pipeline": [
                            {"source": {"events": None, "timeSeries": {"period": "dayRange", "first": start_ms, "last": end_ms}}},
                            {"group": {"group": ["visitorId"], "fields": [
                                {"numEvents": {"sum": "numEvents"}},
                                {"numMinutes": {"sum": "numMinutes"}},
                                {"daysActive": {"count": "day"}},
                            ]}}
                        ],
                        "keys": ["visitorId"],
                    }
                },
            ]
        }
    }

    resp = requests.post(url, headers=pendo_headers(), json=payload)
    resp.raise_for_status()
    results = []
    for row in resp.json().get("results", []):
        email = row.get("email", "")
        if email == PENDO_EXCLUDED_EMAIL:
            continue
        last_seen_ms = row.get("lastSeenAt")
        last_seen = (
            datetime.datetime.utcfromtimestamp(last_seen_ms / 1000).strftime("%-d %b")
            if last_seen_ms else "—"
        )
        results.append({
            "visitor":    (row.get("firstName") or "") + " " + (row.get("lastName") or ""),
            "domain":     row.get("domain", "—"),
            "events":     row.get("numEvents") or "—",
            "daysActive": row.get("daysActive") or "—",
            "minutes":    int(row.get("numMinutes") or 0) or "—",
            "lastSeen":   last_seen,
        })
    return results


def fetch_pendo_top_pages(segment_id: str, window_days: int = PENDO_WINDOW_DAYS, top_n: int = 10):
    """
    Fetches top pages (by page views) for a Pendo segment in the last N days.
    """
    if PENDO_API_KEY == "YOUR_PENDO_API_KEY":
        return _fake_pendo_pages()

    end_ms   = int(datetime.datetime.utcnow().timestamp() * 1000)
    start_ms = end_ms - (window_days * 86400 * 1000)

    url = "https://app.pendo.io/api/v1/aggregation"
    payload = {
        "response": {"mimeType": "application/json"},
        "request": {
            "pipeline": [
                {"source": {"pageEvents": None, "timeSeries": {"period": "dayRange", "first": start_ms, "last": end_ms}}},
                {"filter": f"segmentId == \"{segment_id}\""},
                {"group": {"group": ["pageId"], "fields": [{"views": {"sum": "numEvents"}}]}},
                {"join": {
                    "kind": "left",
                    "pipeline": [{"source": {"pages": None}}, {"select": {"pageId": "id", "pageName": "name"}}],
                    "keys": ["pageId"],
                }},
                {"sort": [{"views": -1}]},
                {"limit": top_n},
            ]
        }
    }

    resp = requests.post(url, headers=pendo_headers(), json=payload)
    resp.raise_for_status()
    return [{"page": r.get("pageName", r.get("pageId", "?")), "views": r.get("views", 0)}
            for r in resp.json().get("results", [])]


def _fake_pendo_visitors():
    return [
        {"visitor": "robert young",          "domain": "bluemantis.com",  "events": 152, "daysActive": 1, "minutes": 10, "lastSeen": "16 Jun"},
        {"visitor": "timo pantsari",         "domain": "blackstone.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "15 Jun"},
        {"visitor": "adam schutska",         "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "15 Jun"},
        {"visitor": "bhavana prabhuswamy",   "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "15 Jun"},
        {"visitor": "rj gravel",             "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "19 May"},
        {"visitor": "abagchi",               "domain": "corestack.io",    "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "2 Jun"},
        {"visitor": "cspbillingapi",         "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "26 May"},
        {"visitor": "alex",                  "domain": "aliando.com",     "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "1 Jun"},
        {"visitor": "dipali koche",          "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "1 Jun"},
        {"visitor": "chris",                 "domain": "aliando.com",     "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "4 Jun"},
        {"visitor": "dene donovan",          "domain": "ingrammicro.com", "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "9 Jun"},
    ]

def _fake_pendo_pages():
    return [
        {"page": "Cloud Account Governance", "views": 52},
        {"page": "Unified Governance",       "views": 9},
        {"page": "Inventory",                "views": 4},
        {"page": "Tenants",                  "views": 2},
        {"page": "Optimize Rate",            "views": 2},
        {"page": "Policies",                 "views": 1},
        {"page": "FinOps NexGen Reports",    "views": 1},
    ]

# ─── PLATFORM METRICS (plug in your source) ──────────────────────────────────

def fetch_platform_metrics():
    """
    Replace this with real data from your monitoring system.
    Expected keys match the N-2 / COST sections in the report.
    """
    return {
        "n2": {
            "total_accounts":    175,
            "completed_jobs_24h": 524,
            "tenants_impacted":  0,
            "pending_n2_accts":  0,
            "older_backlog":     0,
            "compliance_pct":    "100%",
        },
        "cost": {
            "total_requests_24h": 522,
            "max_response_sec":   3.76,
            "slow_requests_30s":  0,
            "users_impacted":     0,
            "health_status":      "Good",
        },
    }

# ─── REPORT RENDERER ─────────────────────────────────────────────────────────

def col(val, width):
    return str(val).ljust(width)[:width]

def render_report(ado_items, visitors, pages, metrics, region="US East"):
    today     = datetime.date.today()
    now_ist   = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    date_str  = today.strftime("%A, %B %-d, %Y")
    time_str  = now_ist.strftime("%I:%M %p IST")

    pendo_end   = today
    pendo_start = today - datetime.timedelta(days=PENDO_WINDOW_DAYS - 1)
    pendo_range = f"{pendo_start.strftime('%-d %b')} – {pendo_end.strftime('%-d %b')}"

    open_incidents = len([i for i in ado_items if i["state"] not in ("Closed", "Removed", "Done", "Resolved")])
    n2  = metrics["n2"]
    svc = metrics["cost"]

    ado_url = (
        f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_workitems?"
        f"filter=tags+eq+'Blackstone'"
    )

    lines = []
    W = 72

    def hr(char="─"):
        lines.append(char * W)

    def section(title):
        lines.append("")
        lines.append(f"  {title}")
        hr()

    # ── Header ────────────────────────────────────────────────────────────────
    lines.append("")
    lines.append(f"  Blackstone — daily scrum update  {region}")
    lines.append(f"  {date_str}   ·   Report generated {time_str}")
    hr("═")

    # ── At a glance ───────────────────────────────────────────────────────────
    section("At a glance")
    lines.append(f"  {'Compliance':<22} {'API requests':<20} {'Slow req ≥30s':<18} {'Open incidents'}")
    lines.append(f"  {n2['compliance_pct']:<22} {svc['total_requests_24h']:<20} {svc['slow_requests_30s']:<18} {open_incidents}")
    lines.append(f"  {'':22} {'Max ' + str(svc['max_response_sec']) + 's resp.':<20} {'':18} {', '.join(['#'+str(i['id']) for i in ado_items[:3]]) or 'None'}")

    # ── Platform performance ───────────────────────────────────────────────────
    section(f"Platform performance — {region}   (N-2 metric)")
    rows_n2 = [
        ("Total accounts",       n2["total_accounts"]),
        ("Completed jobs (24h)", n2["completed_jobs_24h"]),
        ("Tenants impacted",     n2["tenants_impacted"]),
        ("Pending N-2 accts",    n2["pending_n2_accts"]),
        ("Older backlog",        n2["older_backlog"]),
        ("Compliance %",         n2["compliance_pct"]),
    ]
    lines.append(f"  {'Metric':<35} {'Value'}")
    for label, val in rows_n2:
        lines.append(f"  {label:<35} {val}")

    # ── Service metric (COST) ─────────────────────────────────────────────────
    section("Service metric (COST)")
    rows_svc = [
        ("Total requests (24h)",  svc["total_requests_24h"]),
        ("Max response time",     f"{svc['max_response_sec']} sec"),
        ("Slow requests ≥30s",    svc["slow_requests_30s"]),
        ("Users impacted",        svc["users_impacted"]),
        ("Health status",         svc["health_status"]),
    ]
    lines.append(f"  {'Metric':<35} {'Value'}")
    for label, val in rows_svc:
        lines.append(f"  {label:<35} {val}")

    # ── Pendo engagement ──────────────────────────────────────────────────────
    section(f"Pendo engagement — Blackstone segment  ·  last {PENDO_WINDOW_DAYS} days ({pendo_range})")
    lines.append(f"  Source: Blackstone Pendo segment only.  {PENDO_EXCLUDED_EMAIL} excluded.")
    lines.append(f"  Grey rows = segment members with no activity in this window.")
    lines.append("")
    lines.append(f"  {'Visitor':<28} {'Domain':<22} {'Events':>7} {'Days':>5} {'Min':>6}  {'Last seen'}")
    hr("·")
    for v in visitors:
        ev  = str(v["events"])   if v["events"]   != "—" else "—"
        da  = str(v["daysActive"]) if v["daysActive"] != "—" else "—"
        mn  = str(v["minutes"])  if v["minutes"]  != "—" else "—"
        lines.append(f"  {v['visitor']:<28} {v['domain']:<22} {ev:>7} {da:>5} {mn:>6}  {v['lastSeen']}")

    lines.append("")
    lines.append(f"  Top pages visited")
    lines.append(f"  {'Page':<40} {'Views':>6}")
    hr("·")
    for p in pages:
        lines.append(f"  {p['page']:<40} {p['views']:>6}")

    # ── ADO incidents ─────────────────────────────────────────────────────────
    section("Blackstone incidents — ADO status")
    lines.append(f"  ADO query: {ado_url}")
    lines.append("")
    lines.append(f"  {'ID':<9} {'Title':<48} {'Assigned to':<22} {'Pri':<4} {'State':<15} {'Type'}")
    hr("·")
    for item in ado_items:
        pri = f"P{item['priority']}" if item["priority"] else "—"
        lines.append(
            f"  {str(item['id']):<9} "
            f"{item['title'][:46]:<48} "
            f"{item['assignedTo'][:20]:<22} "
            f"{pri:<4} "
            f"{item['state']:<15} "
            f"{item['workItemType']}"
        )
    if not ado_items:
        lines.append("  No active Blackstone work items found.")

    # ── Footer ────────────────────────────────────────────────────────────────
    lines.append("")
    hr("═")
    lines.append(f"  CoreStack · Cloud Operations Intelligence · Daily scrum report")
    lines.append(f"  N-2 = jobs created 24h–48h ago  ·  Slow = request ≥30s")
    lines.append("")

    return "\n".join(lines)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("Fetching ADO Blackstone work items...")
    ado_items = fetch_ado_blackstone_incidents()

    print("Fetching Pendo engagement (USEast segment)...")
    visitors = fetch_pendo_segment_visitors(PENDO_SEGMENT_ID_USEAST)
    pages    = fetch_pendo_top_pages(PENDO_SEGMENT_ID_USEAST)

    print("Fetching platform metrics...")
    metrics  = fetch_platform_metrics()

    report = render_report(ado_items, visitors, pages, metrics, region="US East")
    print(report)

    # Optionally save to file
    out_file = f"Blackstone_Scrum_{datetime.date.today().strftime('%Y%m%d')}.txt"
    with open(out_file, "w") as f:
        f.write(report)
    print(f"\n[Saved to {out_file}]")

if __name__ == "__main__":
    main()
