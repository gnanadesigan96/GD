import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ZOHO_TOKEN_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_API_BASE  = "https://desk.zoho.in/api/v1"
ZOHO_ORG_ID    = os.environ["ZOHO_ORG_ID"]          # 60019389025


def _get_access_token() -> str:
    resp = requests.post(ZOHO_TOKEN_URL, params={
        "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
        "client_id":     os.environ["ZOHO_CLIENT_ID"],
        "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
        "grant_type":    "refresh_token",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Zoho-oauthtoken {token}",
        "orgId": ZOHO_ORG_ID,
    }


def fetch_tickets_by_status(status: str, token: str) -> list[dict]:
    """Fetch all tickets for the given status (handles pagination)."""
    tickets, from_ = [], 0
    while True:
        resp = requests.get(
            f"{ZOHO_API_BASE}/tickets",
            headers=_headers(token),
            params={
                "departmentId": "100599000000010772",
                "status":       status,
                "sortBy":       "createdTime",
                "limit":        50,
                "from":         from_,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            break
        tickets.extend(data)
        if len(data) < 50:
            break
        from_ += 50
    return tickets


def fetch_ticket_detail(ticket_id: str, token: str) -> dict:
    """Fetch full ticket detail including custom fields, contact, and assignee."""
    resp = requests.get(
        f"{ZOHO_API_BASE}/tickets/{ticket_id}",
        headers=_headers(token),
        params={"include": "contacts,assignee"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_active_tickets() -> list[dict]:
    """
    Return all active tickets across all four statuses, each enriched with
    full custom-field data fetched via individual ticket detail calls.
    """
    token = _get_access_token()
    statuses = ["Open", "In Progress", "On Hold", "Awaiting Resolution Confirmation"]
    all_tickets = []
    for s in statuses:
        all_tickets.extend(fetch_tickets_by_status(s, token))

    # Filter out Pentagon and SRE alert noise
    _PENTAGON_ACCOUNT = "100599000037212179"
    def _is_noise(t: dict) -> bool:
        acc_id = str((t.get("account") or {}).get("id") or t.get("accountId") or "")
        email  = (t.get("email") or t.get("contactEmail") or "").lower()
        subj   = (t.get("subject") or "").lower()
        if acc_id == _PENTAGON_ACCOUNT:               return True
        if "clouddesk@pentagon" in email:             return True
        if "notify-sre-ops@corestack.io" in email:   return True
        if "[inc-52" in subj and ("request resolved" in subj or "request received" in subj):
            return True
        return False
    all_tickets = [t for t in all_tickets if not _is_noise(t)]
    logging.info("After noise filter: %d tickets", len(all_tickets))

    # Keep only Incidents
    all_tickets = [t for t in all_tickets if (t.get("ticketType") or "").lower() in ("incident", "")]
    logging.info("After incident-only filter: %d tickets", len(all_tickets))

    # Enrich tickets with custom fields (cf) via parallel individual fetches
    def _enrich(ticket: dict) -> dict:
        tid = ticket.get("id") or ticket.get("ticketId") or ""
        if not tid:
            return ticket
        try:
            detail = fetch_ticket_detail(str(tid), token)
            # Merge cf and any extra fields from detail into the list ticket
            ticket["cf"] = detail.get("cf") or {}
            ticket["customFields"] = detail.get("customFields") or {}
            if detail.get("contacts"):
                ticket["contacts"] = detail["contacts"]
            if detail.get("contact"):
                ticket["contact"] = detail["contact"]
            if detail.get("assignee"):
                ticket["assignee"] = detail["assignee"]
            if detail.get("account"):
                ticket["account"] = detail["account"]
            if detail.get("resolution") and not ticket.get("resolution"):
                ticket["resolution"] = detail["resolution"]
        except Exception as exc:
            logging.warning("Could not fetch detail for ticket %s: %s", tid, exc)
        return ticket

    logging.info("Enriching %d tickets with custom fields…", len(all_tickets))
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_enrich, t): t for t in all_tickets}
        enriched = []
        for future in as_completed(futures):
            enriched.append(future.result())
    logging.info("Enrichment complete.")
    return enriched
