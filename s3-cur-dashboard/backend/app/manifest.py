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
    if not s3_uri.startswith("s3://"):
        raise HTTPException(status_code=400, detail="s3_uri must start with s3://")
    without_scheme = s3_uri[len("s3://"):]
    parts = without_scheme.split("/", 1)
    if len(parts) != 2 or not parts[1]:
        raise HTTPException(status_code=400, detail="s3_uri must include a bucket and report prefix")
    return S3Location(bucket=parts[0], key=parts[1].rstrip("/"))


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
    paginator = s3_client.get_paginator("list_objects_v2")
    matches = []  # (key, last_modified)
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=f"{report_prefix}/"):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not (key.endswith("-Manifest.json") or key.endswith("Manifest.json")):
                    continue
                folder = key[len(report_prefix):].strip("/")
                if _folder_matches_month(folder, month):
                    matches.append((key, obj["LastModified"]))
    except ClientError as exc:
        raise HTTPException(status_code=502, detail=f"Unable to list report files: {exc}") from exc

    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"No CUR manifest found for billing period {month} under s3://{bucket}/{report_prefix}",
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
