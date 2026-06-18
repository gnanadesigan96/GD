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
import sys
import base64
import json
import datetime
import io
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec


def fmt_day(dt) -> str:
    """Format day without leading zero — works on Linux, macOS, Windows."""
    return str(dt.day)


def fmt_date(dt) -> str:
    """e.g. Wednesday, June 18, 2026 — cross-platform."""
    return f"{dt.strftime('%A, %B')} {fmt_day(dt)}, {dt.year}"


def fmt_mon(dt) -> str:
    """e.g. '18 Jun' — cross-platform."""
    return f"{fmt_day(dt)} {dt.strftime('%b')}"


def fmt_month_day(ms) -> str:
    """e.g. 'June 18' (no leading zero) — matches working script output."""
    if not ms:
        return "—"
    d = datetime.datetime.fromtimestamp(ms / 1000, PACIFIC)
    return d.strftime("%B %d").replace(" 0", " ")

# ─── CONFIG ──────────────────────────────────────────────────────────────────

ADO_ORG     = "CoreStack-Tech"
ADO_PROJECT = "Product_Mgmt"
ADO_PAT       = os.environ.get("ADO_PAT", "")
PENDO_API_KEY = os.environ.get("PENDO_API_KEY", "")

# ── Local credentials override (never committed) ──────────────────────────
# Create a file called  credentials.py  in the same folder with:
#   ADO_PAT       = "your-ado-pat"
#   PENDO_API_KEY = "your-pendo-key"
try:
    from credentials import ADO_PAT as _A, PENDO_API_KEY as _P  # type: ignore
    if _A: ADO_PAT = _A
    if _P: PENDO_API_KEY = _P
except ImportError:
    pass
PENDO_REGION_EU      = "portal.corestack.io"
PENDO_REGION_USEAST  = "useast.corestack.io"
PENDO_EXCLUDED_EMAIL = None   # set to an email string to exclude, or None to include all
PENDO_WINDOW_DAYS    = 3

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
    if not ADO_PAT:
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
              AND [System.WorkItemType] = 'Incident'
              AND [System.State] IN ('New', 'In Progress', 'Awaiting Deployment')
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
            "state": "New",
            "priority": 2,
            "tags": "Blackstone; FinOps",
            "workItemType": "Bug",
            "areaPath": "Product_Mgmt\\FinOps",
        },
        {
            "id": 131076,
            "title": "Blackstone - RBAC permission issue on tenant view",
            "assignedTo": "Aadhithya Shanmugapriyan",
            "state": "Awaiting Deployment",
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

PENDO_ENV_VALUES  = ["Blackstone-USeast", "Blackstone-Useast"]
PACIFIC           = datetime.timezone(datetime.timedelta(hours=-7))  # PDT

def pendo_headers():
    return {
        "x-pendo-integration-key": PENDO_API_KEY,
        "Content-Type": "application/json",
    }


def _pendo_agg(pipeline, label="", rows_per_page=5000):
    url = "https://app.pendo.io/api/v1/aggregation"
    all_results = []
    start_row = 0
    while True:
        payload = {
            "response": {"mimeType": "application/json", "rowsPerPage": rows_per_page, "startRow": start_row},
            "request":  {"pipeline": pipeline},
        }
        resp = requests.post(url, headers=pendo_headers(), json=payload)
        if not resp.ok:
            print(f"  [Pendo{' ' + label if label else ''}] {resp.status_code}: {resp.text[:400]}")
            break
        data = resp.json()
        page_results = data.get("results", [])
        all_results.extend(page_results)
        total = data.get("total", len(all_results))
        if len(all_results) >= total or not page_results:
            break
        start_row += rows_per_page
    return all_results


def _fetch_blackstone_accounts() -> dict:
    """
    Resolve the 2 Blackstone accounts via metadata.custom.environment.
    Returns {accountId: region_label} where region is "eu" or "useast".
    """
    flt = " || ".join(f'metadata.custom.environment=="{v}"' for v in PENDO_ENV_VALUES)
    rows = _pendo_agg([
        {"source": {"accounts": None}},
        {"filter": f"({flt})"},
        {"select": {"accountId": "accountId", "env": "metadata.custom.environment"}},
    ], "accounts")
    result = {}
    for r in rows:
        aid = r.get("accountId")
        env = (r.get("env") or "").lower()
        region = "useast" if "useast" in env else "eu"
        result[aid] = region
    print(f"  [Pendo] Blackstone accounts found: {len(result)}")
    return result


def _discover_apps(acct_ids: list) -> list:
    """
    Find every Pendo app touched by the segment by inspecting auto_<appId>
    metadata keys on visitors — matches the dashboard's All-Apps numbers.
    """
    import re
    apps = set()
    for aid in acct_ids:
        rows = _pendo_agg([
            {"source": {"visitors": None}},
            {"filter": f'metadata.auto.accountid=="{aid}"'},
        ], f"apps_{aid[:8]}", rows_per_page=50)
        for r in rows:
            for key in (r.get("metadata") or {}):
                m = re.fullmatch(r"auto_(_?\d+)", key)
                if not m:
                    continue
                raw = m.group(1)
                apps.add(-int(raw[1:]) if raw.startswith("_") else int(raw))
    return sorted(apps) if apps else [None]


def fetch_pendo_all_visitors(accounts: dict = None, window_days: int = PENDO_WINDOW_DAYS):
    """
    Fetch all Blackstone segment members + their activity for the window.
    Logic mirrors generate_blackstone_pendo_report.py exactly:
      - members listed per-account (same visitor appears once per Blackstone account)
      - events/minutes/days summed across all discovered apps (hourRange, matches dashboard)
      - display name: full name if it has a space, else email prefix
      - last seen: "June 18" format (US Pacific)
      - support email included (PENDO_EXCLUDED_EMAIL=None by default)
    """
    if not PENDO_API_KEY:
        return _fake_pendo_visitors()

    accounts  = accounts or {}
    acct_set  = set(accounts.keys())
    if not acct_set:
        return []

    # ── Window: US Pacific day buckets, same as dashboard ────────────────────
    now      = datetime.datetime.now(datetime.timezone.utc)
    today_pt = datetime.datetime.now(PACIFIC).date()
    start_pt = datetime.datetime.combine(
        today_pt - datetime.timedelta(days=window_days - 1),
        datetime.time(0, 0), PACIFIC)
    start_ms = int(start_pt.timestamp() * 1000)
    end_ms   = int(now.timestamp() * 1000)

    # ── Step 1: list all segment members ─────────────────────────────────────
    # visitor source uses metadata.auto.accountid; events source uses top-level accountId
    visitor_filter = " || ".join(f'metadata.auto.accountid=="{a}"' for a in acct_set)
    events_filter  = " || ".join(f'accountId=="{a}"' for a in acct_set)
    member_rows = _pendo_agg([
        {"source": {"visitors": None}},
        {"filter": visitor_filter},
        {"select": {
            "visitorId": "visitorId",
            "email":     "metadata.agent.email",
            "name":      "metadata.agent.name",
            "last":      "metadata.auto.lastvisit",
            "accountId": "metadata.auto.accountid",
            "server":    "metadata.auto.lastservername",
        }},
    ], "members")
    print(f"  [Pendo] segment members found: {len(member_rows)}")

    member_vids = {r["visitorId"] for r in member_rows if r.get("visitorId")}

    # ── Step 2: sum events/minutes/days across all apps ───────────────────────
    apps = _discover_apps(list(acct_set))
    print(f"  [Pendo] apps (All Apps): {apps}")
    from collections import defaultdict
    ev_sum   = defaultdict(int)
    min_sum  = defaultdict(int)
    day_sets = defaultdict(set)
    ts = {"period": "hourRange", "first": start_ms, "last": end_ms}
    for app in apps:
        src = {"events": ({"appId": app} if app is not None else None), "timeSeries": ts}
        rows = _pendo_agg([
            {"source": src},
            {"filter": events_filter},   # top-level accountId for events source
            {"identified": "visitorId"},
        ], f"events_app_{app}")
        for r in rows:
            vid = r.get("visitorId")
            if vid not in member_vids:
                continue
            ev_sum[vid]  += r.get("numEvents", 0)
            min_sum[vid] += r.get("numMinutes", 0)
            hour_ms = r.get("hour")
            if hour_ms:
                day_sets[vid].add(
                    datetime.datetime.fromtimestamp(hour_ms / 1000, PACIFIC).strftime("%Y-%m-%d"))
    days_active = {v: len(d) for v, d in day_sets.items()}
    print(f"  [Pendo] visitors active in window: {len(ev_sum)}")
    servers = {(r.get("server") or "").lower() for r in member_rows}
    print(f"  [Pendo] distinct lastservername values: {sorted(servers)[:10]}")

    # ── Step 3: build result rows (one per member row = one per account) ──────
    results = []
    for meta in member_rows:
        vid   = meta.get("visitorId")
        email = (meta.get("email") or "").strip()
        if not vid:
            continue
        if PENDO_EXCLUDED_EMAIL and email == PENDO_EXCLUDED_EMAIL:
            continue

        # mirrors working script's display_name(): full name if multi-word, else email prefix
        name = (meta.get("name") or "").strip()
        if name and " " in name:
            display = name
        elif email and "@" in email:
            display = email.split("@")[0]
        else:
            display = name or vid
        domain = email.split("@")[1] if "@" in email else "—"

        server = (meta.get("server") or "").lower()
        region = ("eu"     if PENDO_REGION_EU    in server else
                  "useast" if PENDO_REGION_USEAST in server else
                  accounts.get(meta.get("accountId"), "unknown"))

        last_seen  = fmt_month_day(meta.get("last"))   # "June 18" format
        num_events = ev_sum.get(vid, 0)
        results.append({
            "visitorId":  vid,
            "visitor":    display,
            "domain":     domain,
            "events":     num_events if num_events else "-",
            "daysActive": days_active.get(vid, 0) if num_events else "-",
            "minutes":    int(min_sum.get(vid, 0)) if num_events else "-",
            "lastSeen":   last_seen,
            "region":     region,
        })

    # active first (events desc), then inactive alphabetically
    results.sort(key=lambda r: (-(r["events"] if isinstance(r["events"], int) else 0),
                                str(r["visitor"]).lower()))
    print(f"  [Pendo] total Blackstone visitor rows: {len(results)}")
    return results


def split_visitors_by_region(visitors):
    eu     = [v for v in visitors if v["region"] == "eu"]
    useast = [v for v in visitors if v["region"] == "useast"]
    other  = [v for v in visitors if v["region"] not in ("eu", "useast")]
    return eu, useast, other


def fetch_pendo_top_pages(accounts: dict = None, window_days: int = PENDO_WINDOW_DAYS, top_n: int = 10):
    """Top pages for Blackstone accounts using pageEvents across all apps."""
    if not PENDO_API_KEY:
        return _fake_pendo_pages()

    accounts  = accounts or {}
    acct_set  = set(accounts.keys())
    if not acct_set:
        return []

    now      = datetime.datetime.now(datetime.timezone.utc)
    today_pt = datetime.datetime.now(PACIFIC).date()
    start_pt = datetime.datetime.combine(
        today_pt - datetime.timedelta(days=window_days - 1), datetime.time(0, 0), PACIFIC)
    start_ms = int(start_pt.timestamp() * 1000)
    end_ms   = int(now.timestamp() * 1000)

    acct_filter = " || ".join(f'accountId=="{a}"' for a in acct_set)
    apps        = _discover_apps(list(acct_set))
    ts          = {"period": "hourRange", "first": start_ms, "last": end_ms}

    page_views: dict = {}
    for app in apps:
        src = {"pageEvents": ({"appId": app} if app is not None else None), "timeSeries": ts}
        rows = _pendo_agg([
            {"source": src},
            {"filter": acct_filter},
            {"group": {"group": ["pageId"], "fields": [{"views": {"sum": "numEvents"}}]}},
        ], f"pages_app_{app}")
        for r in rows:
            pid = r.get("pageId")
            if not pid or pid in ("allevents", "allfeatures"):
                continue
            page_views[pid] = page_views.get(pid, 0) + (r.get("views") or 0)

    sorted_pages = sorted(page_views.items(), key=lambda x: x[1], reverse=True)[:top_n]
    if not sorted_pages:
        return []

    # Resolve page IDs → names via REST
    try:
        all_pages = {p["id"]: p.get("name", p["id"])
                     for p in requests.get("https://app.pendo.io/api/v1/page",
                                           headers=pendo_headers()).json()}
    except Exception:
        all_pages = {}
    return [{"page": all_pages.get(pid, pid), "views": v} for pid, v in sorted_pages]


def _fake_pendo_visitors():
    return [
        {"visitor": "robert young",          "domain": "bluemantis.com",  "events": 152, "daysActive": 1, "minutes": 10, "lastSeen": "16 Jun", "region": "useast"},
        {"visitor": "adam schutska",         "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "15 Jun", "region": "useast"},
        {"visitor": "bhavana prabhuswamy",   "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "15 Jun", "region": "useast"},
        {"visitor": "rj gravel",             "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "19 May", "region": "useast"},
        {"visitor": "abagchi",               "domain": "corestack.io",    "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "2 Jun",  "region": "useast"},
        {"visitor": "cspbillingapi",         "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "26 May", "region": "useast"},
        {"visitor": "timo pantsari",         "domain": "blackstone.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "15 Jun", "region": "eu"},
        {"visitor": "alex",                  "domain": "aliando.com",     "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "1 Jun",  "region": "eu"},
        {"visitor": "dipali koche",          "domain": "bluemantis.com",  "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "1 Jun",  "region": "eu"},
        {"visitor": "chris",                 "domain": "aliando.com",     "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "4 Jun",  "region": "eu"},
        {"visitor": "dene donovan",          "domain": "ingrammicro.com", "events": "—", "daysActive": "—", "minutes": "—", "lastSeen": "9 Jun",  "region": "eu"},
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

# ─── CHART GENERATORS ────────────────────────────────────────────────────────

BRAND_COLORS = ["#1F6FBF", "#2EA8CC", "#5CC8A0", "#F4A460", "#E05C5C", "#9B59B6", "#F39C12", "#1ABC9C"]
FONT_FAMILY  = "DejaVu Sans"

def _chart_png(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_pendo_top_pages(pages: list) -> io.BytesIO:
    """Horizontal bar chart — top pages by views."""
    names  = [p["page"] for p in pages]
    views  = [p["views"] for p in pages]
    colors = [BRAND_COLORS[i % len(BRAND_COLORS)] for i in range(len(names))]

    fig, ax = plt.subplots(figsize=(6, max(2.5, len(names) * 0.45)))
    bars = ax.barh(names[::-1], views[::-1], color=colors[::-1], edgecolor="none", height=0.6)
    for bar, val in zip(bars, views[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", ha="left", fontsize=9, color="#444")
    ax.set_xlabel("Page views", fontsize=9)
    ax.set_title("Top pages visited", fontsize=11, fontweight="bold", pad=10, color="#1F2937")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=9)
    ax.tick_params(axis="x", labelsize=8)
    ax.set_xlim(0, max(views) * 1.25 if views else 10)
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return _chart_png(fig)


def chart_pendo_visitor_activity(visitors: list) -> io.BytesIO:
    """Bar chart — events per active visitor (only those with events)."""
    active = [(v["visitor"].title(), v["events"]) for v in visitors if isinstance(v["events"], int)]
    if not active:
        # Return a simple "no activity" placeholder chart
        fig, ax = plt.subplots(figsize=(5, 1.5))
        ax.text(0.5, 0.5, "No visitor activity in this window",
                ha="center", va="center", fontsize=10, color="#999", transform=ax.transAxes)
        ax.axis("off")
        return _chart_png(fig)

    names  = [a[0] for a in active]
    events = [a[1] for a in active]

    fig, ax = plt.subplots(figsize=(max(4, len(names) * 1.2), 3.2))
    bars = ax.bar(names, events, color=BRAND_COLORS[0], edgecolor="none", width=0.55)
    for bar, val in zip(bars, events):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(val), ha="center", va="bottom", fontsize=9, color="#444")
    ax.set_ylabel("Events (3-day window)", fontsize=9)
    ax.set_title("Visitor activity", fontsize=11, fontweight="bold", pad=10, color="#1F2937")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=9, rotation=15)
    ax.tick_params(axis="y", labelsize=8)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return _chart_png(fig)


def chart_ado_by_state(ado_items: list) -> io.BytesIO:
    """Donut chart — work items by state."""
    state_order  = ["New", "In Progress", "Awaiting Deployment"]
    state_colors = {"New": "#2EA8CC", "In Progress": "#1F6FBF", "Awaiting Deployment": "#5CC8A0"}

    counts = {s: 0 for s in state_order}
    for item in ado_items:
        s = item["state"]
        if s in counts:
            counts[s] += 1

    labels = [s for s in state_order if counts[s] > 0]
    sizes  = [counts[s] for s in labels]
    colors = [state_colors[s] for s in labels]

    fig, ax = plt.subplots(figsize=(4.5, 3.2))
    if not sizes:
        ax.text(0.5, 0.5, "No items", ha="center", va="center",
                fontsize=11, color="#999", transform=ax.transAxes)
        ax.axis("off")
    else:
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, colors=colors, autopct="%1.0f%%",
            startangle=90, wedgeprops={"width": 0.55, "edgecolor": "white", "linewidth": 2},
            pctdistance=0.75,
        )
        for at in autotexts:
            at.set_fontsize(10)
            at.set_color("white")
            at.set_fontweight("bold")
        legend_patches = [mpatches.Patch(color=colors[i], label=f"{labels[i]} ({sizes[i]})")
                          for i in range(len(labels))]
        ax.legend(handles=legend_patches, loc="lower center", bbox_to_anchor=(0.5, -0.18),
                  ncol=len(labels), fontsize=8.5, frameon=False)
    ax.set_title("ADO items by state", fontsize=11, fontweight="bold", pad=10, color="#1F2937")
    fig.tight_layout()
    return _chart_png(fig)


def chart_ado_by_priority(ado_items: list) -> io.BytesIO:
    """Bar chart — work items by priority."""
    priority_map = {1: "P1 – Critical", 2: "P2 – High", 3: "P3 – Medium", 4: "P4 – Low"}
    pri_colors   = {"P1 – Critical": "#E05C5C", "P2 – High": "#F4A460",
                    "P3 – Medium": "#2EA8CC",   "P4 – Low": "#5CC8A0"}

    counts: dict = {}
    for item in ado_items:
        label = priority_map.get(item["priority"], f"P{item['priority']}" if item["priority"] else "—")
        counts[label] = counts.get(label, 0) + 1

    ordered = [p for p in priority_map.values() if p in counts]
    values  = [counts[p] for p in ordered]
    colors  = [pri_colors.get(p, "#aaa") for p in ordered]

    fig, ax = plt.subplots(figsize=(4.5, 3.2))
    if not ordered:
        ax.text(0.5, 0.5, "No items", ha="center", va="center",
                fontsize=11, color="#999", transform=ax.transAxes)
        ax.axis("off")
    else:
        bars = ax.bar(ordered, values, color=colors, edgecolor="none", width=0.5)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                    str(val), ha="center", va="bottom", fontsize=10, fontweight="bold", color="#444")
        ax.set_ylabel("Work items", fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=8.5)
        ax.tick_params(axis="y", labelsize=8)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        ax.set_ylim(0, max(values) + 1)
    ax.set_title("ADO items by priority", fontsize=11, fontweight="bold", pad=10, color="#1F2937")
    fig.tight_layout()
    return _chart_png(fig)


# ─── DOCX HELPERS ────────────────────────────────────────────────────────────

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# Brand colours
C_DARK   = (0x1F, 0x29, 0x37)
C_WHITE  = (0xFF, 0xFF, 0xFF)
C_ACCENT = (0x00, 0x70, 0xC0)
C_GREY   = (0xF2, 0xF2, 0xF2)
C_MUTED  = (0x75, 0x75, 0x75)
C_GREEN  = (0x70, 0xAD, 0x47)
C_RED    = (0xFF, 0x00, 0x00)


def _set_cell_bg(cell, rgb: RGBColor):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    hex_color = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)


def _set_cell_border(cell, border_side="bottom", color="CCCCCC", sz="4"):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBdr = tcPr.find(qn("w:tcBdr"))
    if tcBdr is None:
        tcBdr = OxmlElement("w:tcBdr")
        tcPr.append(tcBdr)
    side = OxmlElement(f"w:{border_side}")
    side.set(qn("w:val"),   "single")
    side.set(qn("w:sz"),    sz)
    side.set(qn("w:space"), "0")
    side.set(qn("w:color"), color)
    tcBdr.append(side)


def _para_fmt(para, space_before=0, space_after=0, align=WD_ALIGN_PARAGRAPH.LEFT):
    para.paragraph_format.space_before = Pt(space_before)
    para.paragraph_format.space_after  = Pt(space_after)
    para.alignment = align


def _run(para, text, bold=False, italic=False, size=10,
         color=None, font="Calibri"):
    run = para.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.name = font
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor(*color)
    return run


def _heading(doc, text, level_size=12, color=C_DARK):
    p = doc.add_paragraph()
    _para_fmt(p, space_before=10, space_after=2)
    _run(p, text, bold=True, size=level_size, color=color)
    return p


def _add_table(doc, headers, rows, col_widths=None, zebra=True, header_bg=C_DARK):
    """Generic styled table."""
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Header row
    hdr_cells = tbl.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = ""
        p = hdr_cells[i].paragraphs[0]
        _run(p, h, bold=True, size=9, color=C_WHITE)
        _set_cell_bg(hdr_cells[i], header_bg)
        hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # Data rows
    for r_idx, row in enumerate(rows):
        cells = tbl.rows[r_idx + 1].cells
        bg = C_GREY if (zebra and r_idx % 2 == 0) else C_WHITE
        for c_idx, val in enumerate(row):
            cells[c_idx].text = ""
            p = cells[c_idx].paragraphs[0]
            _run(p, str(val), size=9)
            _set_cell_bg(cells[c_idx], bg)

    # Column widths
    if col_widths:
        for row in tbl.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Inches(w)

    return tbl


# ─── REPORT RENDERER ─────────────────────────────────────────────────────────

def render_docx(ado_items, eu_visitors, useast_visitors, other_visitors, pages, metrics):
    """
    Single-page scrum report matching the June 17 layout.
    Pendo section shows all visitors (EU + USEast combined) with a Region column
    and an EU / USEast count summary. ADO incidents appear once.
    """
    doc = Document()

    section = doc.sections[0]
    section.top_margin    = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin   = Cm(1.8)
    section.right_margin  = Cm(1.8)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)

    today    = datetime.date.today()
    now_ist  = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    date_str = fmt_date(today)
    time_str = now_ist.strftime("%I:%M %p IST").lstrip("0")

    pendo_end   = today
    pendo_start = today - datetime.timedelta(days=PENDO_WINDOW_DAYS - 1)
    pendo_range = f"{fmt_mon(pendo_start)}–{fmt_mon(pendo_end)}"

    n2  = metrics["n2"]
    svc = metrics["cost"]
    open_incidents = [i for i in ado_items if i["state"] in ("New", "In Progress", "Awaiting Deployment")]

    # ── Title ─────────────────────────────────────────────────────────────────
    title_p = doc.add_paragraph()
    _para_fmt(title_p, space_before=0, space_after=2)
    _run(title_p, "Blackstone — daily scrum update", bold=True, size=16, color=C_DARK)

    sub_p = doc.add_paragraph()
    _para_fmt(sub_p, space_before=0, space_after=6)
    _run(sub_p, f"{date_str}   ·   Report generated {time_str}", size=9, color=C_MUTED)

    # ── At a glance KPI ───────────────────────────────────────────────────────
    _heading(doc, "At a glance")
    kpi_tbl = doc.add_table(rows=2, cols=4)
    kpi_tbl.style = "Table Grid"
    kpi_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    kpi_headers = ["Compliance", "API requests", "Slow req ≥30s", "Open incidents"]
    open_ids    = ", ".join([f"#{i['id']}" for i in open_incidents[:3]]) or "None"
    kpi_vals    = [
        n2["compliance_pct"],
        f"{svc['total_requests_24h']}\nMax {svc['max_response_sec']}s resp.",
        str(svc["slow_requests_30s"]),
        f"{len(open_incidents)}\n{open_ids}",
    ]
    for i, h in enumerate(kpi_headers):
        c = kpi_tbl.rows[0].cells[i]
        c.text = ""
        _run(c.paragraphs[0], h, bold=True, size=9, color=C_WHITE)
        _set_cell_bg(c, C_DARK)
    for i, v in enumerate(kpi_vals):
        c = kpi_tbl.rows[1].cells[i]
        c.text = ""
        _run(c.paragraphs[0], v, bold=True, size=13, color=C_ACCENT)
        _set_cell_bg(c, C_GREY)
    kpi_w = [1.5, 1.8, 1.8, 1.8]
    for row in kpi_tbl.rows:
        for i, w in enumerate(kpi_w):
            row.cells[i].width = Inches(w)
    doc.add_paragraph()

    # ── Platform performance ──────────────────────────────────────────────────
    _heading(doc, "Platform performance  (N-2 metric)")
    _add_table(doc,
        headers=["Metric", "Value"],
        rows=[
            ("Total accounts",       n2["total_accounts"]),
            ("Completed jobs (24h)", n2["completed_jobs_24h"]),
            ("Tenants impacted",     n2["tenants_impacted"]),
            ("Pending N-2 accts",    n2["pending_n2_accts"]),
            ("Older backlog",        n2["older_backlog"]),
            ("Compliance %",         n2["compliance_pct"]),
        ],
        col_widths=[3.5, 1.5],
    )
    doc.add_paragraph()

    # ── Service metric (COST) ─────────────────────────────────────────────────
    _heading(doc, "Service metric (COST)")
    _add_table(doc,
        headers=["Metric", "Value"],
        rows=[
            ("Total requests (24h)",  svc["total_requests_24h"]),
            ("Max response time",     f"{svc['max_response_sec']} sec"),
            ("Slow requests ≥30s",    svc["slow_requests_30s"]),
            ("Users impacted",        svc["users_impacted"]),
            ("Health status",         svc["health_status"]),
        ],
        col_widths=[3.5, 1.5],
    )
    doc.add_paragraph()

    # ── Pendo engagement (all visitors; EU + USEast counted separately) ──────
    all_visitors = eu_visitors + useast_visitors + other_visitors
    _heading(doc, f"Pendo engagement — Blackstone segment  ·  last {PENDO_WINDOW_DAYS} days ({pendo_range})")

    note_p = doc.add_paragraph()
    _para_fmt(note_p, space_before=0, space_after=4)
    _run(note_p,
         f"Source: Blackstone Pendo segment only.  {PENDO_EXCLUDED_EMAIL} excluded from all counts.  "
         f"Grey rows = segment members with no activity in this window.",
         size=8, italic=True, color=C_MUTED)

    # EU / USEast count summary line
    trend_p = doc.add_paragraph()
    _para_fmt(trend_p, space_before=0, space_after=6)
    _run(trend_p, f"EU (portal.corestack.io): ", bold=True, size=9, color=C_DARK)
    _run(trend_p, f"{len(eu_visitors)} active visitor{'s' if len(eu_visitors) != 1 else ''}",
         size=9, color=C_ACCENT)
    _run(trend_p, "     USEast (useast.corestack.io): ", bold=True, size=9, color=C_DARK)
    _run(trend_p, f"{len(useast_visitors)} active visitor{'s' if len(useast_visitors) != 1 else ''}",
         size=9, color=C_ACCENT)

    _heading(doc, "Active visitors", level_size=10)
    visitor_rows = []
    for v in all_visitors:
        ev = str(v["events"])     if isinstance(v["events"],     int) else "-"
        da = str(v["daysActive"]) if isinstance(v["daysActive"], int) else "-"
        mn = str(v["minutes"])    if isinstance(v["minutes"],    int) else "-"
        visitor_rows.append((v["visitor"], v["domain"], ev, da, mn, v["lastSeen"]))

    _add_table(doc,
        headers=["Visitor (Blackstone segment)", "Domain", "Events (3d)", "Days active", "Minutes", "Last seen"],
        rows=visitor_rows or [("—", "No activity in this window.", "", "", "", "")],
        col_widths=[1.8, 1.8, 1.0, 1.0, 0.8, 0.9],
    )
    doc.add_paragraph()

    activity_img = chart_pendo_visitor_activity(all_visitors)
    pages_img    = chart_pendo_top_pages(pages)

    chart_tbl = doc.add_table(rows=1, cols=2)
    chart_tbl.style = "Table Grid"
    chart_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    left_cell  = chart_tbl.rows[0].cells[0]
    right_cell = chart_tbl.rows[0].cells[1]
    _set_cell_bg(left_cell,  C_WHITE)
    _set_cell_bg(right_cell, C_WHITE)
    left_cell.paragraphs[0].add_run().add_picture(activity_img, width=Inches(3.3))
    right_cell.paragraphs[0].add_run().add_picture(pages_img,   width=Inches(3.3))
    for cell in [left_cell, right_cell]:
        cell.width = Inches(3.4)
    doc.add_paragraph()

    _heading(doc, "Top pages visited", level_size=10)
    _add_table(doc,
        headers=["Page", "Views"],
        rows=[(p["page"], p["views"]) for p in pages] or [("—", "—")],
        col_widths=[4.5, 0.8],
    )
    doc.add_paragraph()

    # ── ADO incidents ─────────────────────────────────────────────────────────
    ado_url = (
        f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_workitems?"
        f"filter=tags+eq+'Blackstone'"
    )
    _heading(doc, "Blackstone incidents — ADO status")
    link_p = doc.add_paragraph()
    _para_fmt(link_p, space_before=0, space_after=4)
    _run(link_p, "ADO query: ", size=9, color=C_MUTED)
    _run(link_p, ado_url, size=9, color=C_ACCENT)

    ado_rows = []
    for item in ado_items:
        pri = f"P{item['priority']}" if item["priority"] else "—"
        ado_rows.append((
            str(item["id"]),
            item["title"],
            item["assignedTo"],
            item.get("areaPath", "").split("\\")[-1] or "—",
            pri,
            item["state"],
            item["workItemType"],
        ))
    if not ado_rows:
        ado_rows = [("—", "No active Blackstone incidents found.", "", "", "", "", "")]

    _add_table(doc,
        headers=["ID", "Title", "Assigned to", "Bundle", "Pri", "State", "Classification"],
        rows=ado_rows,
        col_widths=[0.6, 2.8, 1.4, 0.9, 0.4, 1.0, 0.7],
    )
    doc.add_paragraph()

    state_img = chart_ado_by_state(ado_items)
    pri_img   = chart_ado_by_priority(ado_items)

    ado_chart_tbl = doc.add_table(rows=1, cols=2)
    ado_chart_tbl.style = "Table Grid"
    ado_chart_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    sc = ado_chart_tbl.rows[0].cells[0]
    pc = ado_chart_tbl.rows[0].cells[1]
    _set_cell_bg(sc, C_WHITE)
    _set_cell_bg(pc, C_WHITE)
    sc.paragraphs[0].add_run().add_picture(state_img, width=Inches(3.3))
    pc.paragraphs[0].add_run().add_picture(pri_img,   width=Inches(3.3))
    for cell in [sc, pc]:
        cell.width = Inches(3.4)

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_p = doc.add_paragraph()
    _para_fmt(footer_p, space_before=12, space_after=0)
    _run(footer_p,
         "CoreStack · Cloud Operations Intelligence  ·  Daily scrum report  ·  "
         "N-2 = jobs created 24h–48h ago  ·  Slow = request ≥30s",
         size=8, color=C_MUTED, italic=True)

    return doc


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    using_fake = []
    if not ADO_PAT:
        using_fake.append("ADO   → using FAKE data  (add ADO_PAT to credentials.py)")
    else:
        print("✓ ADO PAT detected — will fetch live work items")

    if not PENDO_API_KEY:
        using_fake.append("Pendo → using FAKE data  (set env var: export PENDO_API_KEY=...)")
    else:
        print("✓ Pendo API key detected — will fetch live visitors")

    if using_fake:
        print("\n⚠️  WARNING — missing credentials:")
        for msg in using_fake:
            print(f"   {msg}")
        print()

    print("Fetching ADO Blackstone work items...")
    ado_items = fetch_ado_blackstone_incidents()

    print("Fetching Pendo engagement...")
    accounts     = _fetch_blackstone_accounts()
    all_visitors = fetch_pendo_all_visitors(accounts=accounts)
    eu_visitors, useast_visitors, other_visitors = split_visitors_by_region(all_visitors)
    print(f"  → EU visitors: {len(eu_visitors)}  |  USEast visitors: {len(useast_visitors)}  |  unclassified: {len(other_visitors)}")

    print("Fetching platform metrics...")
    metrics = fetch_platform_metrics()

    pages = fetch_pendo_top_pages(accounts=accounts)

    doc = render_docx(ado_items, eu_visitors, useast_visitors, other_visitors, pages, metrics)

    out_file = f"Blackstone_Scrum_{datetime.date.today().strftime('%Y%m%d')}.docx"
    doc.save(out_file)
    print(f"\n✓ Saved to {out_file}")


if __name__ == "__main__":
    main()
