"""Ephemeral job status/result store, used to run a slow CUR load as an
async Lambda invocation instead of blocking the HTTP request that started
it.

API Gateway's integration timeout is hard-capped at 30 seconds with no way
to raise it, and a real CUR export can take far longer than that to
download and aggregate. POST /api/cur/load only creates a job record and
fires an async (fire-and-forget) self-invocation of this same Lambda
function to do the actual work -- see main.py's _dispatch_job and
lambda_handler.py's routing between HTTP events and this internal "cur_job"
shape. The frontend then polls GET /api/cur/job/{job_id} until it's done.

Every item has a short TTL so DynamoDB auto-deletes it shortly after --
only job status and the same small aggregated result the API already
returns (never raw CUR line items) are ever stored, and only briefly, so
this stays close to the "nothing is persisted" spirit even though it's a
real (if short-lived) departure from "nothing is ever written down".

Without CUR_DASHBOARD_JOBS_TABLE set (local/uvicorn dev, where there's no
deployed DynamoDB table and no separate Lambda invocation to fire either --
see main.py's _dispatch_job), this falls back to a plain in-process dict.
That's fine there: main.py runs the job inline in that case, so nothing
ever needs to survive across processes or requests.

The result is gzip-compressed before it's written to DynamoDB (stored as a
Binary attribute, not String -- no base64 overhead). The per-account
drill-down added to the result is grouped, not raw line items, but a bill
with many linked accounts can still produce a few thousand small rows, and
DynamoDB caps a single item at 400KB; the result JSON is repetitive enough
(the same handful of category/charge-type strings recur across every
account) that gzip alone cuts it by roughly 6-8x in practice, which is the
difference between comfortably fitting and not for a real multi-account
bill. get_job transparently decompresses it back to a plain JSON string,
so callers never need to know which path a given job came from.

A bill with enough linked accounts can still exceed DynamoDB's 400KB cap
even gzip-compressed, though -- when CUR_DASHBOARD_JOBS_BUCKET is set,
mark_done falls back to spilling the compressed blob to S3 (auto-expired by
the bucket's own lifecycle rule, same "nothing is kept around" spirit as
the jobs table's own short TTL) and stores just the object key in DynamoDB
instead. get_job follows that pointer transparently, so this is invisible
to every other caller.
"""

import gzip
import json
import os
import time

import boto3
from botocore.exceptions import ClientError

JOB_TTL_SECONDS = 1800  # 30 minutes

_TABLE_NAME = os.environ.get("CUR_DASHBOARD_JOBS_TABLE", "")
_RESULTS_BUCKET = os.environ.get("CUR_DASHBOARD_JOBS_BUCKET", "")
_local_jobs: dict[str, dict] = {}


def _table():
    return boto3.resource("dynamodb").Table(_TABLE_NAME)


def _s3():
    return boto3.client("s3")


def create_job(job_id: str) -> None:
    item = {"job_id": job_id, "status": "pending", "ttl": int(time.time()) + JOB_TTL_SECONDS}
    if not _TABLE_NAME:
        _local_jobs[job_id] = item
        return
    _table().put_item(Item=item)


def mark_done(job_id: str, result: dict) -> None:
    if not _TABLE_NAME:
        _local_jobs[job_id] = {**_local_jobs.get(job_id, {}), "status": "done", "result": json.dumps(result)}
        return
    compressed = gzip.compress(json.dumps(result).encode("utf-8"))
    try:
        _table().update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s, #r = :r, #t = :t",
            ExpressionAttributeNames={"#s": "status", "#r": "result", "#t": "ttl"},
            ExpressionAttributeValues={
                ":s": "done",
                ":r": compressed,
                ":t": int(time.time()) + JOB_TTL_SECONDS,
            },
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ValidationException" or not _RESULTS_BUCKET:
            raise
        key = f"{job_id}.gz"
        _s3().put_object(Bucket=_RESULTS_BUCKET, Key=key, Body=compressed)
        _table().update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s, #k = :k, #t = :t",
            ExpressionAttributeNames={"#s": "status", "#k": "result_s3_key", "#t": "ttl"},
            ExpressionAttributeValues={
                ":s": "done",
                ":k": key,
                ":t": int(time.time()) + JOB_TTL_SECONDS,
            },
        )


def mark_error(job_id: str, detail: str) -> None:
    if not _TABLE_NAME:
        _local_jobs[job_id] = {**_local_jobs.get(job_id, {}), "status": "error", "error": detail}
        return
    _table().update_item(
        Key={"job_id": job_id},
        UpdateExpression="SET #s = :s, #e = :e, #t = :t",
        ExpressionAttributeNames={"#s": "status", "#e": "error", "#t": "ttl"},
        ExpressionAttributeValues={
            ":s": "error",
            ":e": detail,
            ":t": int(time.time()) + JOB_TTL_SECONDS,
        },
    )


def get_job(job_id: str) -> dict | None:
    if not _TABLE_NAME:
        return _local_jobs.get(job_id)
    resp = _table().get_item(Key={"job_id": job_id})
    item = resp.get("Item")
    if item is None:
        return item
    if "result" in item:
        # boto3's DynamoDB resource returns Binary attributes wrapped in
        # its own Binary type -- bytes(...) unwraps it either way.
        item["result"] = gzip.decompress(bytes(item["result"])).decode("utf-8")
    elif "result_s3_key" in item:
        obj = _s3().get_object(Bucket=_RESULTS_BUCKET, Key=item.pop("result_s3_key"))
        item["result"] = gzip.decompress(obj["Body"].read()).decode("utf-8")
    return item
