"""
build_dashboard.py
Loads normalized tickets (from a fetch_tickets.py JSON dump or a Zoho Desk
CSV export) and renders the self-contained trend-analysis HTML dashboard.

Usage:
    python3 build_dashboard.py --in data/tickets_raw.json --out trend_dashboard.html
    python3 build_dashboard.py --in tickets_export.csv --start-date 2026-01-01
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timezone

from normalize import load_tickets, rolling_window
from dashboard_template import render


def main():
    default_start, _ = rolling_window(date.today(), quarters_back=2)

    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="tickets_raw.json (from fetch_tickets.py) or a Zoho Desk CSV export")
    ap.add_argument("--out", default="trend_dashboard.html")
    ap.add_argument("--start-date", default=default_start.isoformat(), help=f"default: {default_start.isoformat()} (current quarter - 2)")
    args = ap.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    records = load_tickets(args.inp, start_date=start_date)
    if not records:
        raise SystemExit(f"No tickets loaded from {args.inp} (after the noise filter and >= {start_date} cutoff). Nothing to render.")

    end_date = max(date.fromisoformat(r["created_date"]) for r in records)
    meta = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": os.path.basename(args.inp),
    }

    html = render(records, meta)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {args.out} ({len(records)} tickets, {meta['start_date']} -> {meta['end_date']})")


if __name__ == "__main__":
    main()
