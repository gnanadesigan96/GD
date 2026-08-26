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
"""

import json
import os
import time

import boto3

JOB_TTL_SECONDS = 1800  # 30 minutes

_TABLE_NAME = os.environ.get("CUR_DASHBOARD_JOBS_TABLE", "")
_local_jobs: dict[str, dict] = {}


def _table():
    return boto3.resource("dynamodb").Table(_TABLE_NAME)


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
    _table().update_item(
        Key={"job_id": job_id},
        UpdateExpression="SET #s = :s, #r = :r, #t = :t",
        ExpressionAttributeNames={"#s": "status", "#r": "result", "#t": "ttl"},
        ExpressionAttributeValues={
            ":s": "done",
            ":r": json.dumps(result),
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
    return resp.get("Item")
