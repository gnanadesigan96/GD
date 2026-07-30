"""
sample_data.py
Generates a synthetic Zoho-ticket-shaped dataset so the dashboard can be
previewed before real Zoho data is wired in. Includes a few noise tickets
(notify-sre, gmail, Gartner) to demonstrate the filter working.

This is DEMO DATA ONLY — replace with fetch_tickets.py's live output (or a
Zoho Desk CSV export) for the real report.

Usage:
    python3 sample_data.py --out data/sample_tickets_raw.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import date, timedelta

random.seed(42)

CUSTOMERS = [
    ("Otsuka", "Platinum"), ("Neurealm", "Platinum"), ("Taylor Farms", "Platinum"),
    ("Kyndryl", "Gold"), ("Synopsys", "Gold"), ("Logicalis", "Gold"), ("Hitachi", "Gold"),
    ("Okta", "Gold"), ("Getronics", "Silver"), ("Virtusa", "Silver"), ("Sonata", "Silver"),
    ("Cloud Kinetics", "Silver"), ("Microland", "Silver"),
]

BUNDLES = ["FinOps", "CloudOps", "SecOps", "GRC", "Multi-Cloud Governance", "Automation"]

TYPE_SUBJECTS = {
    "Cost / Billing": [
        "Cost is not getting processed for {m}", "Cost data missing for last billing cycle",
        "Cost allocation report showing incorrect totals",
    ],
    "Onboarding": [
        "Onboarding issue - new subscription not visible", "Unable to complete onboarding for new account",
        "Onboarding steps stuck at account linking",
    ],
    "Budgets": [
        "Budget alerts not triggering as configured", "Unable to create a new budget for {m}",
        "Budget vs actual report mismatch",
    ],
    "Performance / Slowness": [
        "Page is not loading on the dashboard", "Facing slowness while loading cost reports",
        "Timeout when opening the governance dashboard",
    ],
    "Access / Login": [
        "SSO login failing for new users", "Access denied error for read-only role",
    ],
    "Data Sync / Integration": [
        "AWS account not syncing latest resource data", "Integration with ServiceNow not syncing tickets",
    ],
    "Reporting": [
        "Unable to export the monthly report", "Custom report showing stale data",
    ],
    "Bug / Error": [
        "Error when applying a new tag policy", "Exception seen while running compliance scan",
    ],
}

PRIORITY_WEIGHTS = [("Critical", 0.08), ("High", 0.27), ("Medium", 0.45), ("Low", 0.20)]


def weighted_choice(weights):
    r = random.random()
    acc = 0
    for val, w in weights:
        acc += w
        if r <= acc:
            return val
    return weights[-1][0]


def month_name(d: date) -> str:
    return d.strftime("%B")


def make_ticket(idx: int, customer: str, bundle: str, ttype: str, d: date, priority: str | None = None) -> dict:
    subj = random.choice(TYPE_SUBJECTS[ttype]).format(m=month_name(d))
    domain = customer.lower().replace(" ", "") + ".com"
    return {
        "id": str(100000 + idx),
        "ticketNumber": str(9000 + idx),
        "subject": subj,
        "priority": priority or weighted_choice(PRIORITY_WEIGHTS),
        "status": random.choice(["Closed", "Closed", "Closed", "Resolved", "Open", "In Progress"]),
        "createdTime": f"{d.isoformat()}T09:{random.randint(10,59):02d}:00+0530",
        "email": f"user{random.randint(1,9)}@{domain}",
        "account": {"accountName": customer},
        "category": bundle,
        "cf": {"cf_customer": customer},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "data", "sample_tickets_raw.json"))
    ap.add_argument("--year", type=int, default=2026)
    args = ap.parse_args()

    tickets = []
    idx = 0

    def add(customer, bundle, ttype, d, priority=None):
        nonlocal idx
        idx += 1
        tickets.append(make_ticket(idx, customer, bundle, ttype, d, priority))

    # The narrative example from the brief: Otsuka, 2 tickets in Q1 (cost + onboarding),
    # 6 tickets in Q2 (budgets, onboarding, slowness, ...)
    add("Otsuka", "FinOps", "Cost / Billing", date(args.year, 2, 10), priority="Critical")
    add("Otsuka", "CloudOps", "Onboarding", date(args.year, 3, 3), priority="High")
    add("Otsuka", "FinOps", "Budgets", date(args.year, 4, 5))
    add("Otsuka", "CloudOps", "Onboarding", date(args.year, 4, 18))
    add("Otsuka", "GRC", "Performance / Slowness", date(args.year, 5, 2), priority="High")
    add("Otsuka", "FinOps", "Budgets", date(args.year, 5, 20))
    add("Otsuka", "SecOps", "Performance / Slowness", date(args.year, 6, 8))
    add("Otsuka", "CloudOps", "Bug / Error", date(args.year, 6, 25))

    # Spread realistic-ish volume across the rest of the customers, Jan 1 - Jul 30
    start = date(args.year, 1, 1)
    end = date(args.year, 7, 30)
    days = (end - start).days
    ttypes = list(TYPE_SUBJECTS.keys())
    for customer, band in CUSTOMERS:
        if customer == "Otsuka":
            continue
        n = {"Platinum": random.randint(10, 16), "Gold": random.randint(5, 10), "Silver": random.randint(2, 6)}[band]
        for _ in range(n):
            d = start + timedelta(days=random.randint(0, days))
            bundle = random.choice(BUNDLES)
            ttype = random.choice(ttypes)
            add(customer, bundle, ttype, d)

    # Noise tickets that MUST be filtered out by normalize.is_noise()
    tickets.append(make_ticket(9001, "Internal", "FinOps", "Bug / Error", date(args.year, 3, 12)))
    tickets[-1]["email"] = "notify-sre-ops@corestack.io"
    tickets[-1]["subject"] = "[INC-5211] Request received"

    tickets.append(make_ticket(9002, "Random Person", "CloudOps", "Access / Login", date(args.year, 4, 2)))
    tickets[-1]["email"] = "someone@gmail.com"

    tickets.append(make_ticket(9003, "Gartner Inc", "GRC", "Reporting", date(args.year, 5, 15)))
    tickets[-1]["account"] = {"accountName": "Gartner Inc"}
    tickets[-1]["email"] = "analyst@gartner.com"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(tickets, f, indent=2)
    print(f"Wrote {len(tickets)} synthetic tickets ({len(tickets)-3} real + 3 noise) to {args.out}")


if __name__ == "__main__":
    main()
