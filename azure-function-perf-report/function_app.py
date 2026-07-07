"""
function_app.py
Azure Function — Timer Trigger for CoreStack Platform Performance Report.

Schedule: daily at 06:30 PM IST (13:00 UTC).
Requires: VNet integration to reach MongoDB hosts on private IPs.
Outputs:  HTML report + CSV raw data → SharePoint.
"""
import logging
import os
from datetime import datetime, timezone, timedelta

import azure.functions as func

from perf_report import generate_report
from sharepoint_upload import upload_bytes

IST = timedelta(hours=5, minutes=30)

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 0 13 * * *",   # 13:00 UTC = 18:30 IST
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def perf_report_trigger(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logging.warning("Timer is past due — running anyway.")

    now = datetime.utcnow()
    ist_now = now + IST
    logging.info("CoreStack Performance Report starting — %s",
                 ist_now.strftime("%d %b %Y %I:%M %p IST"))

    html_bytes, csv_bytes, html_filename, csv_filename = generate_report(now)

    report_folder = os.environ.get(
        "SHAREPOINT_REPORT_FOLDER", "General/Cost-Performance-Report")
    csv_folder = os.environ.get(
        "SHAREPOINT_CSV_FOLDER", "General/Cost-Performance-Report/Dump")

    logging.info("Uploading HTML report to SharePoint (%s)...", report_folder)
    html_url = upload_bytes(html_bytes, report_folder, html_filename)
    logging.info("HTML uploaded: %s", html_url)

    logging.info("Uploading CSV dump to SharePoint (%s)...", csv_folder)
    csv_url = upload_bytes(csv_bytes, csv_folder, csv_filename)
    logging.info("CSV uploaded: %s", csv_url)

    logging.info("Performance Report complete. HTML=%s CSV=%s", html_url, csv_url)
