"""
fetch_tickets.py
Pulls ALL Zoho Desk tickets created from START_DATE to today (every status,
not just the "active" ones used by the daily incident report), and writes
them to data/tickets_raw.json for build_dashboard.py to consume.

This mirrors the auth/pagination pattern already used in
azure-function/zoho_client.py and gen_report_live.py, so it will work
wherever those already work (i.e. an environment with network access to
desk.zoho.in / accounts.zoho.in).

Usage:
    pip install requests
    export ZOHO_CLIENT_ID=...
    export ZOHO_CLIENT_SECRET=...
    export ZOHO_REFRESH_TOKEN=...
    export ZOHO_ORG_ID=60019389025          # optional, this is the default
    export ZOHO_DEPT_ID=100599000000010772  # optional, this is the default
    python3 fetch_tickets.py [--start-date 2026-01-01] [--out data/tickets_raw.json]

Do NOT hardcode credentials in this file — pass them via environment
variables only (see the note in README.md about the leaked credentials in
gen_report_live.py).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ZOHO_TOKEN_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_API_BASE = "https://desk.zoho.in/api/v1"
ZOHO_ORG_ID = os.environ.get("ZOHO_ORG_ID", "60019389025")
ZOHO_DEPT_ID = os.environ.get("ZOHO_DEPT_ID", "100599000000010772")

# Every status this Zoho Desk department is known to use. The list endpoint
# is also queried once with no status filter (Zoho's default view), and the
# two result sets are merged/de-duped by ticket id, so a status missing from
# this list still gets picked up as long as it's in Zoho's default view.
KNOWN_STATUSES = [
    "Open",
    "In Progress",
    "On Hold",
    "Awaiting Resolution Confirmation",
    "Escalated",
    "Awaiting your Response",
    "Closed",
    "Resolved",
]


def get_token() -> str:
    resp = requests.post(
        ZOHO_TOKEN_URL,
        params={
            "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
            "client_id": os.environ["ZOHO_CLIENT_ID"],
            "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Zoho-oauthtoken {token}", "orgId": ZOHO_ORG_ID}


def fetch_by_status(status: str | None, token: str) -> list[dict]:
    tickets, from_ = [], 0
    while True:
        params = {
            "departmentId": ZOHO_DEPT_ID,
            "sortBy": "createdTime",
            "limit": 50,
            "from": from_,
            "include": "contacts",
        }
        if status:
            params["status"] = status
        resp = requests.get(f"{ZOHO_API_BASE}/tickets", headers=_headers(token), params=params, timeout=30)
        if resp.status_code == 400:
            logging.warning("Status %r not valid for this department, skipping.", status)
            break
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            break
        tickets.extend(data)
        if len(data) < 50:
            break
        from_ += 50
        if from_ >= 100000:
            logging.warning("Hit Zoho's from+limit<=100000 pagination ceiling for status=%r", status)
            break
    return tickets


def fetch_ticket_detail(ticket_id: str, token: str) -> dict:
    resp = requests.get(
        f"{ZOHO_API_BASE}/tickets/{ticket_id}",
        headers=_headers(token),
        params={"include": "contacts,assignee"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all(start_date: date) -> list[dict]:
    token = get_token()
    logging.info("Token obtained.")

    by_id: dict[str, dict] = {}

    # Broadest pass: default view, no status filter
    default_view = fetch_by_status(None, token)
    logging.info("Default view (no status filter): %d tickets", len(default_view))
    for t in default_view:
        by_id[str(t.get("id"))] = t

    # Explicit statuses, in case the default view excludes some (e.g. Closed)
    for s in KNOWN_STATUSES:
        batch = fetch_by_status(s, token)
        logging.info("  status=%s: %d tickets", s, len(batch))
        for t in batch:
            by_id.setdefault(str(t.get("id")), t)

    all_tickets = list(by_id.values())
    logging.info("Total unique tickets fetched (all statuses): %d", len(all_tickets))

    def _created(t: dict) -> date | None:
        s = t.get("createdTime")
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        except Exception:
            return None

    all_tickets = [t for t in all_tickets if (_created(t) or date.min) >= start_date]
    logging.info("After start-date filter (>= %s): %d tickets", start_date, len(all_tickets))

    def _enrich(ticket: dict) -> dict:
        tid = ticket.get("id") or ticket.get("ticketId") or ""
        if not tid:
            return ticket
        try:
            detail = fetch_ticket_detail(str(tid), token)
            ticket["cf"] = detail.get("cf") or {}
            ticket["customFields"] = detail.get("customFields") or {}
            for key in ("contacts", "contact", "assignee", "account", "category", "subCategory", "resolution"):
                if detail.get(key) and not ticket.get(key):
                    ticket[key] = detail[key]
        except Exception as exc:
            logging.warning("Could not fetch detail for ticket %s: %s", tid, exc)
        return ticket

    logging.info("Enriching %d tickets with custom fields / category…", len(all_tickets))
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_enrich, t): t for t in all_tickets}
        enriched = [f.result() for f in as_completed(futures)]
    logging.info("Enrichment complete.")

    statuses_seen = sorted({t.get("status", "") for t in enriched})
    logging.info("Distinct statuses in result set: %s", statuses_seen)
    return enriched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-date", default=f"{date.today().year}-01-01")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "data", "tickets_raw.json"))
    args = ap.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    tickets = fetch_all(start_date)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(tickets, f, indent=2, default=str)
    logging.info("Wrote %d tickets to %s", len(tickets), args.out)


if __name__ == "__main__":
    main()
