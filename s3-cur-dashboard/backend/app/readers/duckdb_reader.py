"""Aggregate a single month's CUR part files with DuckDB.

Parquet and (gzip- or un-)compressed CSV parts are handled the same way:
point DuckDB's httpfs extension at the list of part-file S3 keys from the
manifest and let it read them directly over the network using the
assumed-role's temporary credentials, without ever landing on local disk.

- Parquet parts are columnar and splittable, so DuckDB pushes projection and
  predicate filters down and only pulls the bytes the aggregation needs.
- Gzip/plain CSV parts aren't splittable *within* a file, but a CUR export is
  always split into many part files, so DuckDB still parallelizes across
  files -- each part decompresses (if needed) on its own thread.

Legacy CUR's ZIP compression option is different in kind, not just degree:
each part is a real ZIP archive (one CSV member inside), and DuckDB's
read_csv can sniff gzip or plain CSV from a stream but can't read *inside* a
ZIP archive the way an unzip tool would. For that format only, each part is
downloaded via boto3 and extracted to /tmp before DuckDB ever sees it, then
removed once the aggregation finishes (success or failure) -- /tmp is a
warm Lambda container's local disk, reused across requests, so leaving
extracted CUR data sitting there would violate the "wiped on refresh"
requirement for any *other* request that happens to land on the same
warm container.

Nothing else is written to disk and nothing else is cached between
requests: the DuckDB connection and the temporary credentials are discarded
as soon as the request finishes either way.
"""

import io
import os
import shutil
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor

import boto3
import duckdb
from botocore.exceptions import ClientError as BotoClientError
from fastapi import HTTPException

from ..cur_columns import ResolvedColumn


def _build_source(file_format: str, paths: list[str]) -> str:
    array_literal = "[" + ", ".join(f"'{p}'" for p in paths) + "]"
    if file_format == "parquet":
        return f"read_parquet({array_literal}, union_by_name=true)"
    if file_format == "csv_zip":
        # Already downloaded and extracted to plain local CSV files by
        # _download_and_extract_zip_parts -- no compression left to detect.
        return f"read_csv({array_literal}, header=true, compression='none', all_varchar=true, union_by_name=true)"
    # compression='auto' (not a hardcoded 'gzip'): CUR CSV exports aren't
    # always gzip-compressed -- main.py's format detection only checks for
    # ".parquet"/".zip", so anything else lands here regardless of whether
    # it's actually gzip, uncompressed, or something else DuckDB can sniff
    # from the file itself. Hardcoding 'gzip' broke with "Input is not a
    # GZIP stream" against a real, uncompressed CUR export.
    return f"read_csv({array_literal}, header=true, compression='auto', all_varchar=true, union_by_name=true)"


def _download_and_extract_zip_parts(creds: dict, region: str, bucket: str, part_keys: list[str], tmp_dir: str) -> list[str]:
    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=creds["aws_access_key_id"],
        aws_secret_access_key=creds["aws_secret_access_key"],
        aws_session_token=creds["aws_session_token"],
    )

    def fetch_and_extract(index_key: tuple[int, str]) -> str:
        index, key = index_key
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            member = csv_names[0] if csv_names else zf.namelist()[0]
            local_path = f"{tmp_dir}/part-{index}.csv"
            with zf.open(member) as src, open(local_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            return local_path

    # Downloads are network-latency-bound (S3 GET + a small in-memory
    # unzip), so they parallelize well despite the GIL -- boto3's socket
    # I/O releases it. Bounded at 8 concurrent to avoid hammering S3 with a
    # very large part-file count.
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(fetch_and_extract, enumerate(part_keys)))


def _col_ref(file_format: str, column: ResolvedColumn) -> str:
    if file_format == "parquet":
        return column.athena_name()
    return f'"{column.csv_header()}"'


def aggregate(
    creds: dict,
    region: str,
    bucket: str,
    part_keys: list[str],
    file_format: str,
    columns: dict[str, ResolvedColumn],
) -> dict:
    # Lambda's filesystem is read-only outside /tmp, and there's no HOME env
    # var set by default -- DuckDB's INSTALL needs *some* home/extension
    # directory to cache extensions in, and fails with "Can't find the home
    # directory at ''" if left to its own defaults. home_directory can't be
    # passed via connect(config=...) on this pinned duckdb version (1.1.1
    # rejects it there with "Could not set option ... as a global option");
    # it has to be a regular SET statement after connecting instead.
    con = duckdb.connect()
    con.execute("SET home_directory='/tmp'")
    con.execute("SET extension_directory='/tmp/duckdb_extensions'")

    zip_tmp_dir = f"/tmp/cur-{uuid.uuid4().hex}" if file_format == "csv_zip" else None

    # Everything that can fail -- the download/extract step for ZIP parts,
    # and the DuckDB queries themselves -- is inside this one try/finally so
    # a failure in either place still cleans up zip_tmp_dir and closes the
    # connection. Errors are caught and logged ourselves (a plain print,
    # captured by CloudWatch same as any stdout write) rather than left to
    # propagate: a Lambda invocation that hit one has, in practice, cut off
    # the exception's own message before it reached CloudWatch, leaving
    # only a bare 500 with no way to tell what actually failed.
    try:
        if zip_tmp_dir is not None:
            # No httpfs/S3 credentials needed here -- the part files are
            # downloaded via boto3 and read from local disk instead.
            os.makedirs(zip_tmp_dir, exist_ok=True)
            paths = _download_and_extract_zip_parts(creds, region, bucket, part_keys, zip_tmp_dir)
        else:
            con.execute("INSTALL httpfs")
            con.execute("LOAD httpfs")
            con.execute(f"SET s3_region='{region}'")
            con.execute("SET s3_access_key_id=?", [creds["aws_access_key_id"]])
            con.execute("SET s3_secret_access_key=?", [creds["aws_secret_access_key"]])
            con.execute("SET s3_session_token=?", [creds["aws_session_token"]])
            paths = [f"s3://{bucket}/{key}" for key in part_keys]

        source = _build_source(file_format, paths)
        print(f"aggregate: file_format={file_format!r} part_count={len(paths)} first_paths={paths[:3]!r}")

        cost = f"TRY_CAST({_col_ref(file_format, columns['cost'])} AS DOUBLE)"
        service = _col_ref(file_format, columns["service"])
        day = f"TRY_CAST({_col_ref(file_format, columns['usage_start_date'])} AS TIMESTAMP)::DATE"
        account = _col_ref(file_format, columns["account_id"])

        total_cost = con.execute(f"SELECT SUM({cost}) FROM {source}").fetchone()[0] or 0.0

        by_service = con.execute(
            f"SELECT {service} AS service, SUM({cost}) AS cost FROM {source} "
            f"GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()

        by_day = con.execute(
            f"SELECT {day} AS day, SUM({cost}) AS cost FROM {source} "
            f"GROUP BY 1 ORDER BY 1"
        ).fetchall()

        by_account = con.execute(
            f"SELECT {account} AS account, SUM({cost}) AS cost FROM {source} "
            f"GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()

        currency = None
        if "currency" in columns:
            currency_ref = _col_ref(file_format, columns["currency"])
            row = con.execute(f"SELECT {currency_ref} FROM {source} LIMIT 1").fetchone()
            currency = row[0] if row else None
    except duckdb.Error as exc:
        print(f"DuckDB query failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"DuckDB query failed: {exc}") from exc
    except (BotoClientError, zipfile.BadZipFile, OSError) as exc:
        print(f"Downloading/extracting ZIP part files failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"Unable to read ZIP-compressed report files: {exc}") from exc
    finally:
        con.close()
        # Extracted CUR CSVs must not outlive this request -- /tmp persists
        # across warm-container reuse, and leaving them there would let one
        # customer's data leak into a different request that happens to
        # land on the same warm Lambda container.
        if zip_tmp_dir is not None:
            shutil.rmtree(zip_tmp_dir, ignore_errors=True)

    return {
        "total_cost": float(total_cost),
        "currency": currency,
        "cost_by_service": [{"service": str(s) if s is not None else "unknown", "cost": float(c or 0)} for s, c in by_service],
        "cost_by_day": [{"date": str(d), "cost": float(c or 0)} for d, c in by_day if d is not None],
        "cost_by_account": [{"account_id": str(a) if a is not None else "unknown", "cost": float(c or 0)} for a, c in by_account],
    }
