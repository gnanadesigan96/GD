"""
Display visitors active in the last 3 days with time on app and page events.
"""
import requests, json
from datetime import datetime, timezone, timedelta

try:
    from credentials import PENDO_API_KEY
except ImportError:
    import os; PENDO_API_KEY = os.environ.get("PENDO_API_KEY", "")

HDR = {"x-pendo-integration-key": PENDO_API_KEY, "Content-Type": "application/json"}
URL = "https://app.pendo.io/api/v1/aggregation"

now = datetime.now(timezone.utc)
three_days_ago_ms = int((now - timedelta(days=3)).timestamp() * 1000)
now_ms = int(now.timestamp() * 1000)

def agg(pipeline, rpp=500):
    r = requests.post(URL, headers=HDR,
        json={"response": {"mimeType": "application/json", "rowsPerPage": rpp, "startRow": 0},
              "request":  {"pipeline": pipeline}})
    if not r.ok:
        print(f"  HTTP {r.status_code}: {r.text[:300]}")
        return []
    return r.json().get("results", [])

# ── Step 1: visitors active in last 3 days with time on app ──────────────────
print(f"\n=== Visitors active in last 3 days (since {(now - timedelta(days=3)).strftime('%Y-%m-%d %H:%M UTC')}) ===\n")

visitor_rows = agg([
    {"source": {"visitors": None}},
    {"select": {
        "visitorId":   "visitorId",
        "email":       "metadata.agent.email",
        "name":        "metadata.agent.name",
        "lastVisit":   "metadata.auto.lastvisit",
        "firstVisit":  "metadata.auto.firstvisit",
        "totalTime":   "metadata.auto.totaltimeinapp",
        "lastServer":  "metadata.auto.lastservername",
        "accountId":   "metadata.auto.accountid",
        "browser":     "metadata.auto.lastbrowsername",
        "os":          "metadata.auto.lastoperatingsystem",
    }},
    {"filter": f"lastVisit >= {three_days_ago_ms}"},
    {"sort": ["-lastVisit"]},
])

print(f"Found {len(visitor_rows)} active visitors\n")

visitor_map = {}
for v in visitor_rows:
    vid = v.get("visitorId")
    last_ms = v.get("lastVisit")
    last_str = datetime.fromtimestamp(last_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if last_ms else "—"
    total_min = round(v.get("totalTime", 0) / 60000, 1) if v.get("totalTime") else 0
    visitor_map[vid] = {
        "email":      v.get("email") or v.get("visitorId"),
        "name":       v.get("name", ""),
        "lastVisit":  last_str,
        "totalMin":   total_min,
        "server":     v.get("lastServer", ""),
        "browser":    v.get("browser", ""),
        "os":         v.get("os", ""),
    }

# ── Step 2: page events for last 3 days ─────────────────────────────────────
print("=== Fetching page events for last 3 days ===\n")

page_rows = agg([
    {"source": {"pageEvents": {
        "timeSeries": {
            "first": int((now - timedelta(days=3)).timestamp() * 1000),
            "last":  int(now.timestamp() * 1000),
            "period": "ms"
        }
    }}},
    {"select": {
        "visitorId":  "visitorId",
        "pageId":     "pageId",
        "pageName":   "page.name",
        "numEvents":  "numEvents",
        "numMinutes": "numMinutes",
    }},
    {"group": {
        "group":  ["visitorId", "pageId", "pageName"],
        "fields": [
            {"numEvents":  {"sum": "numEvents"}},
            {"numMinutes": {"sum": "numMinutes"}},
        ]
    }},
    {"sort": ["-numEvents"]},
])

print(f"Found {len(page_rows)} visitor-page combinations\n")

# group page events by visitor
from collections import defaultdict
events_by_visitor = defaultdict(list)
for row in page_rows:
    vid = row.get("visitorId")
    if vid in visitor_map:
        events_by_visitor[vid].append({
            "page":    row.get("pageName") or row.get("pageId", "Unknown"),
            "visits":  int(row.get("numEvents", 0)),
            "minutes": round(float(row.get("numMinutes", 0)), 1),
        })

# sort each visitor's pages by visits desc
for vid in events_by_visitor:
    events_by_visitor[vid].sort(key=lambda x: x["visits"], reverse=True)

# ── Step 3: print summary ────────────────────────────────────────────────────
print("=" * 90)
print(f"{'VISITOR':<35} {'LAST VISIT':<22} {'TOTAL(min)':>10}  TOP PAGES")
print("=" * 90)

for v in visitor_rows:
    vid = v.get("visitorId")
    info = visitor_map[vid]
    pages = events_by_visitor.get(vid, [])
    page_summary = "  |  ".join(
        f"{p['page']} ({p['visits']}x, {p['minutes']}min)"
        for p in pages[:3]
    ) or "(no page events)"

    label = info["email"] if info["email"] != vid else vid[:30]
    print(f"{label:<35} {info['lastVisit']:<22} {info['totalMin']:>10}  {page_summary}")

print("=" * 90)
print(f"\nTotal visitors: {len(visitor_rows)}")
