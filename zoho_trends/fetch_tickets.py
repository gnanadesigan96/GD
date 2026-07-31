"""
fetch_tickets.py
Pulls Zoho Desk tickets created in a date window (default: current quarter +
previous 2 quarters, i.e. a rolling 3-quarter window) and writes them to
data/tickets_raw.json for build_dashboard.py to consume.

Uses the /tickets/search endpoint with createdTimeRange so the date filter
happens server-side — no per-ticket detail enrichment call is needed, since
search/list responses already embed `cf` and `customFields` (confirmed
against live data: cf_bundle, cf_feature, cf_customer, contact.account are
all present inline).

Usage:
    pip install requests
    export ZOHO_CLIENT_ID=...
    export ZOHO_CLIENT_SECRET=...
    export ZOHO_REFRESH_TOKEN=...
    export ZOHO_ORG_ID=60019389025          # optional, this is the default
    export ZOHO_DEPT_ID=100599000000010772  # optional, this is the default
    python3 fetch_tickets.py [--start-date 2026-01-01] [--end-date 2026-07-31] [--out data/tickets_raw.json]

Do NOT hardcode credentials in this file — pass them via environment
variables only (see the note in README.md about the leaked credentials in
gen_report_live.py).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date, datetime

import requests

from normalize import rolling_window

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ZOHO_TOKEN_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_API_BASE = "https://desk.zoho.in/api/v1"
ZOHO_ORG_ID = os.environ.get("ZOHO_ORG_ID", "60019389025")
ZOHO_DEPT_ID = os.environ.get("ZOHO_DEPT_ID", "100599000000010772")


def get_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    resp = requests.post(
        ZOHO_TOKEN_URL,
        params={
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _headers(token: str, org_id: str) -> dict:
    return {"Authorization": f"Zoho-oauthtoken {token}", "orgId": org_id}


def fetch_range(token: str, org_id: str, dept_id: str, start: date, end: date) -> list[dict]:
    """Fetch every ticket (any status) created in [start, end], inclusive."""
    created_range = f"{start.isoformat()}T00:00:00.000Z,{end.isoformat()}T23:59:59.000Z"
    tickets, from_ = [], 0
    while True:
        resp = requests.get(
            f"{ZOHO_API_BASE}/ticketsSearch",
            headers=_headers(token, org_id),
            params={
                "departmentId": dept_id,
                "createdTimeRange": created_range,
                "sortBy": "createdTime",
                "limit": 100,
                "from": from_,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            break
        tickets.extend(data)
        logging.info("  fetched %d (running total %d)", len(data), len(tickets))
        if len(data) < 100:
            break
        from_ += 100
        if from_ >= 100000:
            logging.warning("Hit Zoho's from+limit<=100000 pagination ceiling for this range")
            break
    return tickets


def fetch_all(client_id: str, client_secret: str, refresh_token: str, start: date, end: date,
              org_id: str = ZOHO_ORG_ID, dept_id: str = ZOHO_DEPT_ID) -> list[dict]:
    token = get_token(client_id, client_secret, refresh_token)
    logging.info("Token obtained. Fetching tickets %s -> %s ...", start, end)
    tickets = fetch_range(token, org_id, dept_id, start, end)
    statuses_seen = sorted({t.get("status", "") for t in tickets})
    logging.info("Total tickets fetched: %d. Distinct statuses: %s", len(tickets), statuses_seen)
    return tickets


def main():
    today = date.today()
    default_start, default_end = rolling_window(today, quarters_back=2)

    ap = argparse.ArgumentParser()
    ap.add_argument("--start-date", default=default_start.isoformat(), help=f"default: {default_start.isoformat()} (current quarter - 2)")
    ap.add_argument("--end-date", default=default_end.isoformat(), help=f"default: {default_end.isoformat()} (today)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "data", "tickets_raw.json"))
    args = ap.parse_args()

    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    tickets = fetch_all(
        os.environ["ZOHO_CLIENT_ID"], os.environ["ZOHO_CLIENT_SECRET"], os.environ["ZOHO_REFRESH_TOKEN"],
        start, end,
    )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(tickets, f, indent=2, default=str)
    logging.info("Wrote %d tickets to %s", len(tickets), args.out)


if __name__ == "__main__":
    main()
