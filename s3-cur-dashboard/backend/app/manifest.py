"""Locate and parse a single month's CUR manifest.

Standard AWS CUR layout partitions report data by billing period:

  legacy CUR:  <prefix>/<reportName>/<YYYYMMDD>-<YYYYMMDD>/<reportName>-Manifest.json
  CUR 2.0:     <prefix>/<reportName>/BILLING_PERIOD=<YYYY-MM>/<reportName>-Manifest.json

Rather than hardcode either convention, we list the objects under the report
prefix once and match the billing-period folder against the requested month,
so both layouts (and any date-range formatting AWS chooses) work.

A billing period isn't generated once -- AWS regenerates the report for the
current (and sometimes a recent past) month repeatedly as usage/cost data
settles, and each regeneration is a full cumulative report for that month,
not an incremental delta. Depending on the customer's "overwrite existing
report" setting, old regenerations may remain in S3 as their own
assembly-versioned copies alongside the newest one. We only ever want the
most recent regeneration -- it already contains every day's cost for the
month so far -- so among manifests matching the requested month we pick the
one with the latest S3 LastModified timestamp, rather than processing (or
even reading) every historical version.
"""

import json
import re
from dataclasses import dataclass

from botocore.exceptions import ClientError
from fastapi import HTTPException

_DATE_RANGE_RE = re.compile(r"(\d{8})-(\d{8})")
_BILLING_PERIOD_RE = re.compile(r"BILLING_PERIOD=(\d{4}-\d{2})")


@dataclass
class S3Location:
    bucket: str
    key: str


def parse_s3_uri(s3_uri: str) -> S3Location:
    """Accepts a bare bucket name, "bucket/prefix", or either of those with
    an "s3://" scheme. The prefix is optional -- when it's omitted (just a
    bucket), find_month_manifest_key scans the whole bucket to locate the
    requested month's report instead of requiring the caller to already
    know its exact path.
    """
    without_scheme = s3_uri[len("s3://"):] if s3_uri.startswith("s3://") else s3_uri
    if not without_scheme:
        raise HTTPException(status_code=400, detail="s3_uri must not be empty")
    bucket, _, prefix = without_scheme.partition("/")
    if not bucket:
        raise HTTPException(status_code=400, detail="s3_uri must include a bucket name")
    return S3Location(bucket=bucket, key=prefix.rstrip("/"))


def _folder_matches_month(folder: str, month: str) -> bool:
    range_match = _DATE_RANGE_RE.search(folder)
    if range_match:
        start = range_match.group(1)  # YYYYMMDD
        return f"{start[:4]}-{start[4:6]}" == month

    period_match = _BILLING_PERIOD_RE.search(folder)
    if period_match:
        return period_match.group(1) == month

    return False


def find_month_manifest_key(s3_client, bucket: str, report_prefix: str, month: str) -> str:
    """report_prefix narrows the S3 listing when known, but isn't required:
    the billing-period match is checked against the whole key (not just the
    segment immediately after report_prefix), so passing "" scans the
    entire bucket and auto-discovers the report's location -- useful when
    the customer only gave us a bucket name. That full scan lists every
    object in the bucket, so it's slower and costs more list-requests than
    passing the report prefix when it's known.
    """
    paginator = s3_client.get_paginator("list_objects_v2")
    matches = []  # (key, last_modified)
    list_prefix = f"{report_prefix}/" if report_prefix else ""
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=list_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not (key.endswith("-Manifest.json") or key.endswith("Manifest.json")):
                    continue
                if _folder_matches_month(key, month):
                    matches.append((key, obj["LastModified"]))
    except ClientError as exc:
        raise HTTPException(status_code=502, detail=f"Unable to list report files: {exc}") from exc

    if not matches:
        location = f"s3://{bucket}/{report_prefix}" if report_prefix else f"s3://{bucket}"
        raise HTTPException(
            status_code=404,
            detail=f"No CUR manifest found for billing period {month} under {location}",
        )

    # Most recently regenerated report wins -- it already covers every day
    # of the month up to the last refresh, so older versioned copies (if the
    # customer keeps report history) are never read.
    latest_key, _ = max(matches, key=lambda pair: pair[1])
    return latest_key


def load_manifest(s3_client, bucket: str, manifest_key: str) -> dict:
    try:
        body = s3_client.get_object(Bucket=bucket, Key=manifest_key)["Body"].read()
    except ClientError as exc:
        raise HTTPException(status_code=502, detail=f"Unable to read manifest: {exc}") from exc
    return json.loads(body)
