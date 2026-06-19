"""
gen_report_live.py
Run this locally to generate today's CS Daily Incident Report with live Zoho data
including ADO numbers, then upload to SharePoint.

Usage:
    pip install requests openpyxl
    python3 gen_report_live.py

Credentials:
    Create a file called  credentials.py  in the same folder with:
        SHAREPOINT_TENANT_ID     = "your-tenant-id"
        SHAREPOINT_CLIENT_SECRET = "your-client-secret"
    That file is git-ignored and never committed.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "azure-function"))

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone, timedelta

import requests

from report_generator import parse_ticket, generate_html, generate_excel
from sharepoint_client import upload_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ── Zoho credentials (safe to keep here — Zoho tokens, not passwords) ─────────
ZOHO_CLIENT_ID     = os.environ.get("ZOHO_CLIENT_ID",     "1000.LXE6HGZAW4FWRED50ZUZ42CHUFHVEO")
ZOHO_CLIENT_SECRET = os.environ.get("ZOHO_CLIENT_SECRET", "7d84eb43d93d42648ad05636b2b7310652361722e9")
ZOHO_REFRESH_TOKEN = os.environ.get("ZOHO_REFRESH_TOKEN", "1000.ca586bbc38413c0661c0e67e78378449.72ac1952b7eb013374cc87e8544475a4")

# ── SharePoint credentials — loaded from credentials.py (never committed) ─────
SHAREPOINT_TENANT_ID     = os.environ.get("SHAREPOINT_TENANT_ID",     "")
SHAREPOINT_CLIENT_ID     = os.environ.get("SHAREPOINT_CLIENT_ID",     "abb2a8fa-4603-4aff-80b2-bf614beb173b")
SHAREPOINT_CLIENT_SECRET = os.environ.get("SHAREPOINT_CLIENT_SECRET", "")
SHAREPOINT_SITE_URL      = os.environ.get("SHAREPOINT_SITE_URL",      "cloudenablersinc.sharepoint.com/sites/SupportTeam")
SHAREPOINT_HTML_FOLDER   = os.environ.get("SHAREPOINT_HTML_FOLDER",   "General/Daily-Incident-Report/Template")
SHAREPOINT_EXCEL_FOLDER  = os.environ.get("SHAREPOINT_EXCEL_FOLDER",  "General/Daily-Incident-Report/Template")

# ── Local credentials override (create credentials.py — see docstring above) ──
try:
    from credentials_zoho import (     # type: ignore
        SHAREPOINT_TENANT_ID     as _T,
        SHAREPOINT_CLIENT_SECRET as _S,
    )
    if _T: SHAREPOINT_TENANT_ID     = _T
    if _S: SHAREPOINT_CLIENT_SECRET = _S
except ImportError:
    pass

# Push resolved values into env so sharepoint_client.py picks them up
os.environ["SHAREPOINT_TENANT_ID"]     = SHAREPOINT_TENANT_ID
os.environ["SHAREPOINT_CLIENT_ID"]     = SHAREPOINT_CLIENT_ID
os.environ["SHAREPOINT_CLIENT_SECRET"] = SHAREPOINT_CLIENT_SECRET
os.environ["SHAREPOINT_SITE_URL"]      = SHAREPOINT_SITE_URL
os.environ["SHAREPOINT_HTML_FOLDER"]   = SHAREPOINT_HTML_FOLDER
os.environ["SHAREPOINT_EXCEL_FOLDER"]  = SHAREPOINT_EXCEL_FOLDER
ZOHO_ORG_ID        = "60019389025"
ZOHO_DEPT_ID       = "100599000000010772"
PENTAGON_ACCOUNT   = "100599000037212179"

ZOHO_TOKEN_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_API_BASE  = "https://desk.zoho.in/api/v1"
IST = timedelta(hours=5, minutes=30)


def get_token() -> str:
    resp = requests.post(ZOHO_TOKEN_URL, params={
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id":     ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type":    "refresh_token",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def headers(token: str) -> dict:
    return {"Authorization": f"Zoho-oauthtoken {token}", "orgId": ZOHO_ORG_ID}


def fetch_by_status(status: str, token: str) -> list[dict]:
    tickets, from_ = [], 0
    while True:
        resp = requests.get(f"{ZOHO_API_BASE}/tickets", headers=headers(token), params={
            "departmentId": ZOHO_DEPT_ID,
            "status":       status,
            "sortBy":       "createdTime",
            "limit":        50,
            "from":         from_,
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            break
        tickets.extend(data)
        if len(data) < 50:
            break
        from_ += 50
    return tickets


def fetch_detail(ticket_id: str, token: str) -> dict:
    resp = requests.get(
        f"{ZOHO_API_BASE}/tickets/{ticket_id}",
        headers=headers(token),
        params={"include": "contacts,assignee"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def is_pentagon(t: dict) -> bool:
    acc = (t.get("account") or {})
    acc_id = acc.get("id") or acc.get("accountId") or t.get("accountId") or ""
    if str(acc_id) == PENTAGON_ACCOUNT:
        return True
    subj = (t.get("subject") or "").lower()
    email = (t.get("email") or t.get("contactEmail") or "").lower()
    if "clouddesk@pentagon" in email:
        return True
    if "[inc-52" in subj and ("request resolved" in subj or "request received" in subj):
        return True
    return False


def is_alert(t: dict) -> bool:
    email = (t.get("email") or t.get("contactEmail") or "").lower()
    return "notify-sre-ops@corestack.io" in email


def main():
    today = (datetime.now(timezone.utc) + IST).date()
    logging.info("Generating report for %s", today)

    token = get_token()
    logging.info("Token obtained.")

    statuses = ["Open", "In Progress", "On Hold", "Awaiting Resolution Confirmation"]
    raw = []
    for s in statuses:
        batch = fetch_by_status(s, token)
        logging.info("  %s: %d tickets", s, len(batch))
        raw.extend(batch)

    # Filter noise
    raw = [t for t in raw if not is_pentagon(t) and not is_alert(t)]
    logging.info("After filters (Pentagon + Alerts): %d tickets", len(raw))

    # Keep only Incidents (exclude Service Requests and other types)
    raw = [t for t in raw if (t.get("ticketType") or "").lower() in ("incident", "")]
    logging.info("After incident-only filter: %d tickets", len(raw))

    # Enrich with custom fields (ADO) via parallel individual fetches
    def enrich(t: dict) -> dict:
        tid = t.get("id") or t.get("ticketId") or ""
        if not tid:
            return t
        try:
            detail = fetch_detail(str(tid), token)
            t["cf"] = detail.get("cf") or {}
            t["customFields"] = detail.get("customFields") or {}
            if detail.get("contacts"):
                t["contacts"] = detail["contacts"]
            if detail.get("contact"):
                t["contact"] = detail["contact"]
            if detail.get("assignee"):
                t["assignee"] = detail["assignee"]
            if detail.get("account"):
                t["account"] = detail["account"]
            if detail.get("resolution") and not t.get("resolution"):
                t["resolution"] = detail["resolution"]
        except Exception as e:
            logging.warning("Detail fetch failed for %s: %s", tid, e)
        return t

    logging.info("Fetching individual ticket details for ADO numbers…")
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(enrich, t): t for t in raw}
        enriched = [f.result() for f in as_completed(futures)]
    logging.info("Enrichment done.")

    tickets = [parse_ticket(t, today) for t in enriched]

    # Count tickets with ADO
    ado_count = sum(1 for t in tickets if t.get("ado"))
    logging.info("Tickets with ADO numbers: %d / %d", ado_count, len(tickets))

    # Show which tickets have ADO
    for t in tickets:
        if t.get("ado"):
            logging.info("  #%s  ADO=%s", t["num"], t["ado"])

    date_tag = today.strftime("%Y%m%d")
    html_path  = f"CS_Daily_Incident_Report_{date_tag}.html"
    excel_path = f"CS_Daily_Incident_Report_{date_tag}.xlsx"

    # Generate Excel first
    with open(excel_path, "wb") as f:
        f.write(generate_excel(tickets, today))
    logging.info("Excel written: %s", excel_path)

    # Upload Excel to get the SharePoint URL, then embed it in the HTML
    sp_html_folder  = os.environ["SHAREPOINT_HTML_FOLDER"]
    sp_excel_folder = os.environ["SHAREPOINT_EXCEL_FOLDER"]
    excel_sp_url = ""
    try:
        logging.info("Uploading Excel to SharePoint…")
        excel_sp_url = upload_file(excel_path, sp_excel_folder, excel_path)
        logging.info("Excel uploaded: %s", excel_sp_url)
    except Exception as e:
        logging.error("SharePoint Excel upload failed: %s", e)

    # Generate HTML with the SharePoint Excel URL embedded
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(generate_html(tickets, today, excel_url=excel_sp_url))
    logging.info("HTML written: %s", html_path)

    try:
        logging.info("Uploading HTML to SharePoint…")
        html_url = upload_file(html_path, sp_html_folder, html_path)
        logging.info("HTML uploaded: %s", html_url)
    except Exception as e:
        logging.error("SharePoint HTML upload failed: %s", e)
        logging.info("Files saved locally — upload manually if needed.")

    logging.info("Done. %d tickets in report.", len(tickets))


if __name__ == "__main__":
    main()
