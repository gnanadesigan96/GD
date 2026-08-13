#!/bin/bash
# Watchdog for generate_perf_report.py.
#
# The 6 PM IST cron run occasionally fails outright (VPN/network blips that
# outlast the script's own 3x retry). This runs later (e.g. 7 PM IST) and
# re-executes the report only if today's IST-dated output file is missing —
# if it's already there, it does nothing.
#
# Usage: ./check_and_rerun_report.sh
# Intended to run from cron on the same box as generate_perf_report.py.

set -u

REPORT_DIR="/opt/performance"
SCRIPT="${REPORT_DIR}/generate_perf_report.py"
DATE_STAMP="$(TZ="Asia/Kolkata" date +%Y-%m-%d)"
HTML_FILE="${REPORT_DIR}/corestack-performance-report_${DATE_STAMP}.html"

if [ -f "$HTML_FILE" ]; then
    echo "$(date): ${HTML_FILE} exists, skipping re-run."
    exit 0
fi

echo "$(date): ${HTML_FILE} missing, re-running generate_perf_report.py."
cd "$REPORT_DIR" || exit 1
/usr/bin/python3 "$SCRIPT" --no-vpn --fix-ms-routes
