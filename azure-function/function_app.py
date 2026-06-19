"""
function_app.py
Azure Function — Timer Trigger: runs daily at 6:00 PM IST (12:30 UTC).
"""
import logging
import os
import tempfile
from datetime import date, datetime, timezone, timedelta

import azure.functions as func

from zoho_client import fetch_all_active_tickets
from report_generator import parse_ticket, generate_html, generate_excel
from sharepoint_client import upload_file

IST = timedelta(hours=5, minutes=30)

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 30 12 * * *",   # 12:30 UTC = 18:00 IST
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def daily_incident_report(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logging.warning("Timer is past due — running anyway.")

    now_ist = datetime.now(timezone.utc) + IST
    today   = now_ist.date()
    logging.info("Daily Incident Report starting for %s", today.isoformat())

    # 1. Fetch live tickets from Zoho Desk
    logging.info("Fetching tickets from Zoho Desk…")
    raw_tickets = fetch_all_active_tickets()
    logging.info("Fetched %d raw tickets", len(raw_tickets))

    # 2. Normalise
    tickets = [parse_ticket(r, today) for r in raw_tickets]
    logging.info("Parsed %d tickets", len(tickets))

    # 3. Generate reports
    html_bytes  = generate_html(tickets, today).encode("utf-8")
    excel_bytes = generate_excel(tickets, today)

    date_tag = today.strftime("%Y-%m-%d")
    html_filename  = f"CS_Daily_Incident_Report_{date_tag}.html"
    excel_filename = f"CS_Daily_Incident_Report_{date_tag}.xlsx"

    # 4. Upload to SharePoint
    sp_html_folder  = os.environ.get("SHAREPOINT_HTML_FOLDER",  "General/Daily-Incident-Report/Template")
    sp_excel_folder = os.environ.get("SHAREPOINT_EXCEL_FOLDER", "General/Daily-Incident-Report/Excel")

    with tempfile.TemporaryDirectory() as tmp:
        html_path  = os.path.join(tmp, html_filename)
        excel_path = os.path.join(tmp, excel_filename)

        with open(html_path,  "wb") as fh:
            fh.write(html_bytes)
        with open(excel_path, "wb") as fh:
            fh.write(excel_bytes)

        logging.info("Uploading HTML to SharePoint…")
        html_url  = upload_file(html_path,  sp_html_folder,  html_filename)
        logging.info("HTML uploaded: %s", html_url)

        logging.info("Uploading Excel to SharePoint…")
        excel_url = upload_file(excel_path, sp_excel_folder, excel_filename)
        logging.info("Excel uploaded: %s", excel_url)

    logging.info("Daily Incident Report complete. HTML=%s  Excel=%s", html_url, excel_url)
