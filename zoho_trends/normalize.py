"""
normalize.py
Turns raw Zoho Desk ticket records (from fetch_tickets.py's JSON dump, or a
CSV exported from the Zoho Desk UI) into the flat shape build_dashboard.py
aggregates over, applying the customer/noise filter and the ticket-type
classifier along the way.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from typing import Any, Iterable

# ── Noise filter ───────────────────────────────────────────────────────────
# Per the brief: ignore anything from notify-sre, any @gmail.com sender, and
# any Gartner-related ticket (account name or email domain).
_NOISE_EMAIL_SUBSTRINGS = ("notify-sre", "notifysre", "@gmail.com")
_NOISE_NAME_SUBSTRINGS = ("gartner",)


def is_noise(email: str, account: str, subject: str) -> bool:
    email = (email or "").lower()
    account = (account or "").lower()
    subject = (subject or "").lower()
    if any(s in email for s in _NOISE_EMAIL_SUBSTRINGS):
        return True
    if any(s in account for s in _NOISE_NAME_SUBSTRINGS):
        return True
    if any(s in email for s in _NOISE_NAME_SUBSTRINGS):
        return True
    if any(s in subject for s in _NOISE_NAME_SUBSTRINGS):
        return True
    return False


# ── Ticket-type classification ──────────────────────────────────────────────
# Keyword → type, checked in order against the subject (first match wins).
# Edit freely as real ticket language turns out to differ from these guesses.
TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Cost / Billing", ["cost is not", "cost not processed", "cost data", "billing", "invoice", "cost processing"]),
    ("Budgets", ["budget"]),
    ("Onboarding", ["onboarding", "on-boarding", "on boarding", "provisioning new", "new account setup"]),
    ("Performance / Slowness", ["slow", "slowness", "performance", "lag", "timeout", "page is not loading", "page not loading", "not loading"]),
    ("Access / Login", ["login", "log in", "access denied", "permission denied", "sso", "password reset", "unable to access"]),
    ("Data Sync / Integration", ["sync", "integration", "connector", "not syncing", "data mismatch", "data missing"]),
    ("Reporting", ["report", "export", "dashboard not"]),
    ("Alerting / Notifications", ["alert", "notification"]),
    ("Bug / Error", ["error", "bug", "exception", "failed", "fails", "crash"]),
    ("Feature Request", ["feature request", "enhancement", "request for", "please add"]),
]


def classify_type(subject: str) -> str:
    s = (subject or "").lower()
    for label, keywords in TYPE_KEYWORDS:
        if any(k in s for k in keywords):
            return label
    return "Other"


_PRIORITY_MAP = {"Critical": "P1", "High": "P2", "Medium": "P3", "Normal": "P3", "Low": "P4"}
_PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}


def normalize_priority(raw: str) -> str:
    raw = raw or "Normal"
    return _PRIORITY_MAP.get(raw, raw if raw.upper().startswith("P") else "P3")


def quarter_label(d: date) -> str:
    q = (d.month - 1) // 3 + 1
    return f"Q{q} {d.year}"


def month_label(d: date) -> str:
    return d.strftime("%Y-%m")


def _parse_date(s: Any) -> date | None:
    if not s:
        return None
    if isinstance(s, date):
        return s
    s = str(s)
    for fmt in (None, "%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"):
        try:
            if fmt is None:
                return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def _norm_account(s: str) -> str:
    return (s or "").strip()


def normalize_json_ticket(raw: dict) -> dict | None:
    subject = raw.get("subject", "")
    email = raw.get("email") or raw.get("contactEmail") or ""
    cf = raw.get("cf") or {}
    custom_fields = raw.get("customFields") or {}

    account = ""
    if raw.get("account"):
        account = raw["account"].get("accountName") or raw["account"].get("name") or ""
    if not account:
        account = raw.get("accountName") or cf.get("cf_customer") or custom_fields.get("Customer") or ""
    account = _norm_account(account) or "Unknown"

    if is_noise(email, account, subject):
        return None

    created = _parse_date(raw.get("createdTime"))
    if not created:
        return None

    bundle = raw.get("category") or custom_fields.get("Category") or raw.get("subCategory") or custom_fields.get("Sub Category") or "Uncategorized"

    return {
        "ticket_number": raw.get("ticketNumber", ""),
        "subject": subject,
        "priority": normalize_priority(raw.get("priority")),
        "status": raw.get("status", ""),
        "is_closed": str(raw.get("status", "")).lower() in ("closed", "resolved"),
        "customer": account,
        "bundle": bundle,
        "type": classify_type(subject),
        "created_date": created.isoformat(),
        "quarter": quarter_label(created),
        "month": month_label(created),
    }


def normalize_csv_row(row: dict) -> dict | None:
    def g(*keys: str) -> str:
        for k in keys:
            if k in row and row[k]:
                return row[k]
        return ""

    subject = g("Subject")
    email = g("Email", "Contact Email")
    account = _norm_account(g("Account Name", "Account", "Customer")) or "Unknown"

    if is_noise(email, account, subject):
        return None

    created = _parse_date(g("Created Time", "Created Date"))
    if not created:
        return None

    bundle = g("Category") or g("Sub Category") or "Uncategorized"
    status = g("Status")

    return {
        "ticket_number": g("Ticket Number", "Ticket Id"),
        "subject": subject,
        "priority": normalize_priority(g("Priority")),
        "status": status,
        "is_closed": status.lower() in ("closed", "resolved"),
        "customer": account,
        "bundle": bundle,
        "type": classify_type(subject),
        "created_date": created.isoformat(),
        "quarter": quarter_label(created),
        "month": month_label(created),
    }


def load_tickets(path: str, start_date: date | None = None) -> list[dict]:
    """Load + normalize tickets from either a fetch_tickets.py JSON dump or a
    Zoho Desk CSV export. Returns the flat normalized records, noise already
    filtered out."""
    records: list[dict]
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            raw_list = json.load(f)
        records = [r for r in (normalize_json_ticket(t) for t in raw_list) if r]
    elif path.lower().endswith(".csv"):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            records = [r for r in (normalize_csv_row(row) for row in reader) if r]
    else:
        raise ValueError(f"Unsupported file type: {path}")

    if start_date:
        records = [r for r in records if date.fromisoformat(r["created_date"]) >= start_date]

    return records
