import os
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


def fetch_tickets_by_status(status: str) -> list[dict]:
    """Fetch all tickets for the given status (handles pagination)."""
    token = _get_access_token()
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


def fetch_all_active_tickets() -> list[dict]:
    """Return all active tickets across all four statuses."""
    statuses = ["Open", "In Progress", "On Hold", "Awaiting Resolution Confirmation"]
    all_tickets = []
    for s in statuses:
        all_tickets.extend(fetch_tickets_by_status(s))
    return all_tickets
