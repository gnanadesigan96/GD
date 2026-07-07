"""
run_report.py
Standalone entry point for the Docker container.
Generates the report and uploads to SharePoint.
"""
import logging
import os
import sys
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

from perf_report import generate_report
from sharepoint_upload import upload_bytes


def main():
    now = datetime.utcnow()
    ist = now + timedelta(hours=5, minutes=30)
    logging.info("Report run starting — %s", ist.strftime("%d %b %Y %I:%M %p IST"))

    html_bytes, csv_bytes, html_filename, csv_filename = generate_report(now)

    report_folder = os.environ.get(
        "SHAREPOINT_REPORT_FOLDER", "General/Cost-Performance-Report")
    csv_folder = os.environ.get(
        "SHAREPOINT_CSV_FOLDER", "General/Cost-Performance-Report/Dump")

    logging.info("Uploading HTML → SharePoint/%s/%s", report_folder, html_filename)
    html_url = upload_bytes(html_bytes, report_folder, html_filename)
    logging.info("HTML uploaded: %s", html_url)

    logging.info("Uploading CSV → SharePoint/%s/%s", csv_folder, csv_filename)
    csv_url = upload_bytes(csv_bytes, csv_folder, csv_filename)
    logging.info("CSV uploaded: %s", csv_url)

    logging.info("Complete. HTML=%s CSV=%s", html_url, csv_url)


if __name__ == "__main__":
    main()
