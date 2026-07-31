"""
function_app.py
Azure Function — HTTP-triggered Zoho ticket trend dashboard.

GET  /api/dashboard  -> the dashboard page (credentials form + charts)
POST /api/tickets    -> {client_id, client_secret, refresh_token, org_id?,
                         dept_id?, quarters_back?} -> {tickets: [...], meta: {...}}

No Zoho credentials are read from environment variables or stored anywhere
server-side — every request supplies its own, used once to call Zoho, then
discarded. Nothing from the request body is logged.
"""
import json
import logging
from datetime import date, datetime, timezone

import azure.functions as func

from dashboard_page import render as render_dashboard_page
from fetch import DEFAULT_DEPT_ID, DEFAULT_ORG_ID, ZohoApiError, ZohoAuthError, fetch_all
from normalize import normalize_ticket_list, rolling_window

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="dashboard", methods=["GET"])
def dashboard(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(render_dashboard_page(), mimetype="text/html")


@app.route(route="tickets", methods=["POST"])
def tickets(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _json_error("Request body must be JSON.", 400)

    client_id = (body.get("client_id") or "").strip()
    client_secret = (body.get("client_secret") or "").strip()
    refresh_token = (body.get("refresh_token") or "").strip()
    org_id = (body.get("org_id") or "").strip() or DEFAULT_ORG_ID
    dept_id = (body.get("dept_id") or "").strip() or DEFAULT_DEPT_ID
    try:
        quarters_back = max(0, min(6, int(body.get("quarters_back", 2))))
    except (TypeError, ValueError):
        quarters_back = 2

    if not client_id or not client_secret or not refresh_token:
        return _json_error("client_id, client_secret, and refresh_token are all required.", 400)

    start, end = rolling_window(date.today(), quarters_back=quarters_back)
    logging.info("Fetching tickets org=%s dept=%s window=%s..%s (quarters_back=%d)",
                 org_id, dept_id, start, end, quarters_back)

    try:
        raw_tickets = fetch_all(client_id, client_secret, refresh_token, start, end, org_id=org_id, dept_id=dept_id)
    except ZohoAuthError as exc:
        logging.warning("Zoho auth failure for org=%s dept=%s: %s", org_id, dept_id, exc)
        return _json_error(str(exc), 401)
    except ZohoApiError as exc:
        logging.warning("Zoho API failure for org=%s dept=%s: %s", org_id, dept_id, exc)
        return _json_error(str(exc), 502)
    except Exception as exc:
        logging.exception("Unexpected error fetching tickets")
        return _json_error(f"Unexpected error: {exc}", 500)

    records = normalize_ticket_list(raw_tickets, start_date=start)
    logging.info("Fetched %d raw tickets, %d after noise filter", len(raw_tickets), len(records))

    meta = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "raw_count": len(raw_tickets),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    return func.HttpResponse(json.dumps({"tickets": records, "meta": meta}), mimetype="application/json")


def _json_error(message: str, status: int) -> func.HttpResponse:
    return func.HttpResponse(json.dumps({"error": message}), status_code=status, mimetype="application/json")
