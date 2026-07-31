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


def quarter_of(d: date) -> tuple[int, int]:
    return d.year, (d.month - 1) // 3 + 1


def quarter_label(d: date) -> str:
    y, q = quarter_of(d)
    return f"Q{q} {y}"


def quarter_start_date(y: int, q: int) -> date:
    return date(y, (q - 1) * 3 + 1, 1)


def shift_quarter(y: int, q: int, n: int) -> tuple[int, int]:
    idx = y * 4 + (q - 1) + n
    return idx // 4, idx % 4 + 1


def rolling_window(today: date, quarters_back: int = 2) -> tuple[date, date]:
    """Start of (current quarter - quarters_back) through today — e.g. current +
    last 2 quarters when quarters_back=2."""
    y, q = quarter_of(today)
    sy, sq = shift_quarter(y, q, -quarters_back)
    return quarter_start_date(sy, sq), today


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


def _blank(v: Any) -> bool:
    """True for None, "", and Zoho's own "NA"/"N/A" placeholder strings."""
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s.upper() in ("NA", "N/A")


# Internal/placeholder account names — relabeled (not dropped) so they're easy
# to spot and exclude via the dashboard's own customer filter if you want to.
_INTERNAL_ACCOUNT_NAMES = {"internal", "corestack", "corestack internal", "corestack_cs", "unknown", "n/a", "na", ""}


def _clean_account(name: str) -> str:
    name = _norm_account(name)
    return "Corestack (internal)" if name.lower() in _INTERNAL_ACCOUNT_NAMES else (name or "Unknown")


def normalize_json_ticket(raw: dict) -> dict | None:
    subject = raw.get("subject", "")
    email = raw.get("email") or raw.get("contactEmail") or ""
    cf = raw.get("cf") or {}
    custom_fields = raw.get("customFields") or {}

    # Account: getTicket/detail responses put it top-level; searchTickets/getTickets
    # (list endpoints) nest it under contact.account. Check both shapes.
    account = ""
    acct_obj = raw.get("account") or (raw.get("contact") or {}).get("account") or {}
    if acct_obj:
        account = acct_obj.get("accountName") or acct_obj.get("name") or ""
    if _blank(account):
        account = raw.get("accountName") or ""
    if _blank(account):
        account = cf.get("cf_customer") or custom_fields.get("Customer") or ""
    account = _clean_account(account)

    if is_noise(email, account, subject):
        return None

    created = _parse_date(raw.get("createdTime"))
    if not created:
        return None

    # Bundle: CoreStack's own "Reporting Bundle" custom field (cf_bundle) —
    # NOT the generic Zoho Category/Sub-Category fields, which are unused here.
    bundle = cf.get("cf_bundle") or custom_fields.get("Reporting Bundle")
    if _blank(bundle):
        bundle = raw.get("category") or raw.get("subCategory")
    bundle = bundle if not _blank(bundle) else "Uncategorized"

    # Ticket type: CoreStack's own "Reporting Feature" custom field (cf_feature)
    # is a curated taxonomy (Cost processing, Onboarding, Budget, Access, ...).
    # Fall back to subject-keyword classification only when it's not set.
    feature = cf.get("cf_feature") or custom_fields.get("Reporting Feature")
    ttype = feature if not _blank(feature) else classify_type(subject)

    return {
        "ticket_number": raw.get("ticketNumber", ""),
        "subject": subject,
        "priority": normalize_priority(raw.get("priority")),
        "status": raw.get("status", ""),
        "is_closed": str(raw.get("status", "")).lower() in ("closed", "resolved"),
        "customer": account,
        "bundle": bundle,
        "type": ttype,
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
    account = _clean_account(g("Account Name", "Account", "Customer"))

    if is_noise(email, account, subject):
        return None

    created = _parse_date(g("Created Time", "Created Date"))
    if not created:
        return None

    bundle = g("Reporting Bundle", "Bundle", "Category") or g("Sub Category") or "Uncategorized"
    feature = g("Reporting Feature", "Feature")
    ttype = feature if not _blank(feature) else classify_type(subject)
    status = g("Status")

    return {
        "ticket_number": g("Ticket Number", "Ticket Id"),
        "subject": subject,
        "priority": normalize_priority(g("Priority")),
        "status": status,
        "is_closed": status.lower() in ("closed", "resolved"),
        "customer": account,
        "bundle": bundle,
        "type": ttype,
        "created_date": created.isoformat(),
        "quarter": quarter_label(created),
        "month": month_label(created),
    }


def normalize_ticket_list(raw_list: list[dict], start_date: date | None = None) -> list[dict]:
    """Same as load_tickets's JSON branch, but for an in-memory list (used by
    the webapp, which fetches tickets directly via the API rather than from a
    file on disk)."""
    records = [r for r in (normalize_json_ticket(t) for t in raw_list) if r]
    if start_date:
        records = [r for r in records if date.fromisoformat(r["created_date"]) >= start_date]
    return records


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
