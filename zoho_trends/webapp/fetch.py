"""
fetch.py
Zoho Desk fetch logic for the webapp. Credentials are passed in per-call from
the request body (see function_app.py) — nothing Zoho-related is read from
environment variables or written to disk here.
"""
from __future__ import annotations

from datetime import date

import requests

ZOHO_TOKEN_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_API_BASE = "https://desk.zoho.in/api/v1"

DEFAULT_ORG_ID = "60019389025"
DEFAULT_DEPT_ID = "100599000000010772"

MAX_PAGES = 200  # safety cap: 200 * 100 = 20,000 tickets max per request


class ZohoAuthError(Exception):
    pass


class ZohoApiError(Exception):
    pass


def get_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    try:
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
    except requests.RequestException as exc:
        raise ZohoAuthError(f"Could not reach Zoho accounts endpoint: {exc}") from exc

    if resp.status_code != 200:
        raise ZohoAuthError("Zoho rejected the client id / secret / refresh token combination.")
    body = resp.json()
    if "access_token" not in body:
        raise ZohoAuthError(f"Zoho token response had no access_token: {body.get('error', body)}")
    return body["access_token"]


def _headers(token: str, org_id: str) -> dict:
    return {"Authorization": f"Zoho-oauthtoken {token}", "orgId": org_id}


def fetch_range(token: str, org_id: str, dept_id: str, start: date, end: date) -> list[dict]:
    """Fetch every ticket (any status) created in [start, end], inclusive."""
    created_range = f"{start.isoformat()}T00:00:00.000Z,{end.isoformat()}T23:59:59.000Z"
    tickets, from_, page = [], 0, 0
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
        if resp.status_code == 401:
            raise ZohoAuthError("Zoho access token was rejected (expired or invalid org/department id).")
        if resp.status_code >= 400:
            raise ZohoApiError(f"Zoho API returned HTTP {resp.status_code} for departmentId={dept_id}.")
        data = resp.json().get("data", [])
        if not data:
            break
        tickets.extend(data)
        if len(data) < 100:
            break
        from_ += 100
        page += 1
        if page >= MAX_PAGES or from_ >= 100000:
            break
    return tickets


def fetch_all(client_id: str, client_secret: str, refresh_token: str, start: date, end: date,
              org_id: str = DEFAULT_ORG_ID, dept_id: str = DEFAULT_DEPT_ID) -> list[dict]:
    token = get_token(client_id, client_secret, refresh_token)
    return fetch_range(token, org_id, dept_id, start, end)
