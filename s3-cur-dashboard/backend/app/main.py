import os
import time

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .aws_client import assume_role, resolve_bucket_region, s3_client_for
from .cur_columns import resolve_columns
from .manifest import find_month_manifest_key, load_manifest, parse_s3_uri
from .readers.duckdb_reader import aggregate
from .schemas import CurLoadRequest, CurLoadResponse

app = FastAPI(title="S3 CUR Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: str | None = Header(default=None)):
    """No-op unless CUR_DASHBOARD_API_KEY is set.

    A Lambda Function URL with AuthType=NONE is invocable by anyone who has
    it -- without this, that means anyone could get this backend to attempt
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


@app.post("/api/cur/load", response_model=CurLoadResponse, dependencies=[Depends(require_api_key)])
def load_cur(req: CurLoadRequest):
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
