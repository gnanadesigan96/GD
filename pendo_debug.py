"""Run this on your local machine to diagnose visitor field paths."""
import requests, json

try:
    from credentials import PENDO_API_KEY
except ImportError:
    import os; PENDO_API_KEY = os.environ.get("PENDO_API_KEY", "")

hdrs = {"x-pendo-integration-key": PENDO_API_KEY, "Content-Type": "application/json"}
URL  = "https://app.pendo.io/api/v1/aggregation"

def agg(pipeline, rpp=3):
    r = requests.post(URL, headers=hdrs,
        json={"response": {"mimeType": "application/json", "rowsPerPage": rpp, "startRow": 0},
              "request":  {"pipeline": pipeline}})
    print(f"  HTTP {r.status_code}  total={r.json().get('total') if r.ok else '?'}")
    return r.json().get("results", []) if r.ok else []

# Test 1: raw visitors source — no select, see what keys come back
print("\n=== Test 1: raw visitors source (no select) ===")
rows = agg([{"source": {"visitors": None}}])
if rows:
    print("  Keys:", list(rows[0].keys()))
    print("  Row 0:", json.dumps(rows[0], indent=4))

# Test 2: explicitly select every likely path
print("\n=== Test 2: try all common email field paths ===")
paths = {
    "email_v1":    "visitor.agent.email",
    "email_v2":    "agent.email",
    "email_v3":    "metadata.agent.email",
    "email_v4":    "visitor.metadata.agent.email",
    "server_v1":   "visitor.auto.lastservername",
    "server_v2":   "auto.lastservername",
    "acctId_v1":   "visitor.auto.accountid",
    "acctId_v2":   "accountId",
    "acctId_v3":   "auto.accountid",
}
rows = agg([
    {"source": {"visitors": None}},
    {"select": {"visitorId": "visitorId", **paths}},
], rpp=5)
for row in rows:
    print("  Row:", {k: v for k, v in row.items() if v is not None})

# Test 3: get one visitor via REST to see metadata structure
print("\n=== Test 3: sample visitor via REST API ===")
sample_rows = agg([{"source": {"visitors": None}}, {"select": {"visitorId": "visitorId"}}], rpp=1)
if sample_rows:
    vid = sample_rows[0]["visitorId"]
    r = requests.get(
        f"https://app.pendo.io/api/v1/visitor/{requests.utils.quote(str(vid), safe='')}",
        headers=hdrs)
    print(f"  Visitor: {vid}")
    print(f"  HTTP {r.status_code}")
    if r.ok:
        meta = r.json().get("metadata", {})
        for bucket, fields in meta.items():
            if isinstance(fields, dict):
                print(f"  metadata.{bucket}: {fields}")
