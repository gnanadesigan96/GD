import json
import os
import time
import uuid

import boto3
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import jobs
from .aws_client import assume_role, resolve_bucket_region, s3_client_for
from .cur_columns import resolve_columns
from .manifest import find_month_manifest_key, load_manifest, parse_s3_uri
from .readers.duckdb_reader import aggregate
from .schemas import CurJobStartedResponse, CurJobStatusResponse, CurLoadRequest, CurLoadResponse

app = FastAPI(title="S3 CUR Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: str | None = Header(default=None)):
    """No-op unless CUR_DASHBOARD_API_KEY is set.

    Without this, anyone who reaches this API could get it to attempt
    sts:AssumeRole against arbitrary role ARNs. Set CUR_DASHBOARD_API_KEY in
    the deployment and the matching value in the frontend's build to close
    that off with a shared secret. Left unset for local development.
    """
    expected = os.environ.get("CUR_DASHBOARD_API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


@app.get("/api/health")
def health():
    return {"status": "ok"}


def run_cur_job(req: CurLoadRequest) -> CurLoadResponse:
    """The actual (potentially slow) work: assume the role, locate the
    month's manifest, and aggregate its part files. Can take anywhere from
    seconds to several minutes depending on the export's size -- this is
    only ever called from the async job path (see _execute_job), never
    directly from an HTTP request, so it isn't bound by any request
    timeout.
    """
    started = time.perf_counter()

    location = parse_s3_uri(req.s3_uri)
    creds = assume_role(req.role_arn, req.external_id, req.session_name)
    s3_client = s3_client_for(creds, region=req.region)
    region = req.region or resolve_bucket_region(s3_client, location.bucket)

    manifest_key = find_month_manifest_key(s3_client, location.bucket, location.key, req.month)
    manifest = load_manifest(s3_client, location.bucket, manifest_key)

    part_keys = manifest.get("reportKeys") or manifest.get("dataFiles") or []
    if not part_keys:
        raise HTTPException(status_code=502, detail="Manifest for this billing period lists no report files")

    first_key = part_keys[0]
    if first_key.endswith(".parquet"):
        file_format = "parquet"
    elif first_key.endswith(".zip"):
        # Legacy CUR's ZIP compression option: each part is a real ZIP
        # archive (one CSV member inside), not a gzip stream -- DuckDB's
        # httpfs/read_csv can't read inside a ZIP archive directly the way
        # it can sniff gzip/plain CSV, so this format needs the part files
        # downloaded and extracted first (see readers/duckdb_reader.py).
        file_format = "csv_zip"
    else:
        file_format = "csv_gz"
    columns = resolve_columns(manifest["columns"])

    result = aggregate(creds, region, location.bucket, part_keys, file_format, columns)

    return CurLoadResponse(
        billing_period=req.month,
        currency=result["currency"],
        total_cost=result["total_cost"],
        cost_by_service=result["cost_by_service"],
        cost_by_day=result["cost_by_day"],
        cost_by_account=result["cost_by_account"],
        file_format=file_format,
        part_file_count=len(part_keys),
        load_time_ms=(time.perf_counter() - started) * 1000,
    )


def _execute_job(job_id: str, req: CurLoadRequest) -> None:
    """Runs run_cur_job and records the outcome. Called either inline (no
    Lambda to self-invoke -- local/uvicorn dev) or from lambda_handler.py
    when this Lambda invokes itself asynchronously.
    """
    try:
        result = run_cur_job(req)
        jobs.mark_done(job_id, result.model_dump())
    except HTTPException as exc:
        jobs.mark_error(job_id, str(exc.detail))
    except Exception as exc:  # noqa: BLE001 -- must not leave a job stuck "pending" for any failure
        jobs.mark_error(job_id, str(exc))


def _dispatch_job(job_id: str, req: CurLoadRequest) -> None:
    function_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    if not function_name:
        # Local dev (uvicorn) -- there's no separate Lambda invocation to
        # fire, so just run the job in this same process/request instead.
        _execute_job(job_id, req)
        return
    boto3.client("lambda").invoke(
        FunctionName=function_name,
        InvocationType="Event",  # fire-and-forget -- don't wait for it to finish
        Payload=json.dumps({"cur_job": {"job_id": job_id, "request": req.model_dump()}}).encode(),
    )


@app.post("/api/cur/load", response_model=CurJobStartedResponse, status_code=202, dependencies=[Depends(require_api_key)])
def load_cur(req: CurLoadRequest):
    """Starts the load as a background job and returns immediately.

    A real CUR export can take minutes to download and aggregate --
    comfortably past API Gateway's hard, non-configurable 30-second
    integration timeout. This endpoint itself does no S3/STS work, so it
    stays fast; the actual work happens in _execute_job, dispatched via
    _dispatch_job to run outside any request's timeout. Poll
    GET /api/cur/job/{job_id} for the result.
    """
    job_id = uuid.uuid4().hex
    jobs.create_job(job_id)
    _dispatch_job(job_id, req)
    return CurJobStartedResponse(job_id=job_id)


@app.get("/api/cur/job/{job_id}", response_model=CurJobStatusResponse, dependencies=[Depends(require_api_key)])
def get_cur_job(job_id: str):
    item = jobs.get_job(job_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Job not found (it may have expired)")

    status = item["status"]
    if status == "done":
        return CurJobStatusResponse(status="done", result=CurLoadResponse(**json.loads(item["result"])))
    if status == "error":
        return CurJobStatusResponse(status="error", error=item.get("error"))
    return CurJobStatusResponse(status="pending")
