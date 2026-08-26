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
    cost_metrics: dict[str, ResolvedColumn],
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
    # DuckDB spills intermediate results to disk once a query's working set
    # is large enough (aggregating a real customer's full month easily is),
    # and its default spill location is a relative ".tmp" directory under
    # the current working directory -- /var/task in Lambda, which is
    # read-only outside /tmp, same class of problem as home_directory
    # above but only surfaces once the data is big enough to spill at all.
    con.execute("SET temp_directory='/tmp/duckdb_temp'")
    # DuckDB auto-detects available memory from the container it's running
    # in, but Lambda already tells us exactly how much it configured this
    # invocation with -- using that directly (rather than trusting
    # auto-detection inside a cgroup-limited container) keeps DuckDB from
    # spilling to /tmp sooner than it needs to. Ephemeral storage is capped
    # at Lambda's hard 10GB maximum (see deploy_backend.sh), so once a
    # sufficiently large export starts spilling, there's no more disk to
    # give it -- the only lever left is keeping more of the working set in
    # RAM in the first place. Reserve ~20% of configured memory for the
    # Python process, boto3, and the Lambda runtime itself.
    lambda_memory_mb = os.environ.get("AWS_LAMBDA_FUNCTION_MEMORY_SIZE")
    if lambda_memory_mb:
        con.execute(f"SET memory_limit='{int(int(lambda_memory_mb) * 0.8)}MB'")

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

        service = _col_ref(file_format, columns["service"])
        day = f"TRY_CAST({_col_ref(file_format, columns['usage_start_date'])} AS TIMESTAMP)::DATE"
        account = _col_ref(file_format, columns["account_id"])
        currency_expr = _col_ref(file_format, columns["currency"]) if "currency" in columns else "NULL"
        # Optional drill-down dimensions: not every export has these
        # columns (productFamily/LineItemType), so anything missing just
        # falls back to a literal 'unknown' instead of failing the load.
        resource_category_expr = _col_ref(file_format, columns["resource_category"]) if "resource_category" in columns else "'unknown'"
        charge_type_expr = _col_ref(file_format, columns["charge_type"]) if "charge_type" in columns else "'unknown'"
        metric_base_cols = ", ".join(
            f"TRY_CAST({_col_ref(file_format, col)} AS DOUBLE) AS metric_{name}"
            for name, col in cost_metrics.items()
        )

        # "cost" (used for total/by-service/by-day/by-account) and one of
        # the drill-down's cost_metrics columns are, in the overwhelming
        # common case, the exact same source column (both prefer
        # lineItem/UnblendedCost first) -- reuse that metric_<name> value
        # for "cost" instead of computing/summing it a second time. Only
        # fall back to a separate cost_raw column in the rare case where it
        # doesn't (e.g. an export with a cost/UnblendedCost column but no
        # lineItem/Blended|UnblendedCost at all).
        cost_metric_alias = next((name for name, col in cost_metrics.items() if col == columns["cost"]), None)
        cost_base_col = "" if cost_metric_alias else f", TRY_CAST({_col_ref(file_format, columns['cost'])} AS DOUBLE) AS cost_raw"
        cost_agg_source = f"metric_{cost_metric_alias}" if cost_metric_alias else "cost_raw"

        # Every breakdown the dashboard needs -- the grand total, by
        # service/day/account, and the account/day drill-downs -- comes out
        # of a single pass over the source with one multi-grouping-set hash
        # aggregate (verified via EXPLAIN to be one HASH_GROUP_BY over one
        # SEQ_SCAN, no intermediate materialization), instead of copying the
        # full export into a temp table first and re-querying that copy six
        # times. This is what actually fixed a large export's "Out of
        # Memory... max_temp_directory_size" error -- there's no longer a
        # full row-level copy of the month sitting in memory/spilled to
        # /tmp at all, on top of reading the export exactly once either way.
        #
        # GROUPING_ID(service, day, account_id, resource_category,
        # charge_type) tags each output row with which grouping set
        # produced it (one bit per column, MSB-first in argument order: 1 =
        # rolled up/not grouped, 0 = grouped) -- routing rows below by this
        # tag rather than by NULL-checking the columns themselves, since a
        # column's real value can legitimately be NULL too (e.g. service).
        GID_TOTAL = 0b11111          # ()
        GID_BY_SERVICE = 0b01111     # (service)
        GID_BY_DAY = 0b10111         # (day)
        GID_BY_ACCOUNT = 0b11011     # (account_id)
        GID_DRILLDOWN = 0b01000      # (account_id, service, resource_category, charge_type)
        GID_DAY_DRILLDOWN = 0b00100  # (day, service, resource_category, charge_type)

        metric_names = list(cost_metrics.keys())
        metric_sum_cols = ", ".join(f"SUM(metric_{name}) AS metric_{name}" for name in metric_names)
        # Always include all 6 sets, even when cost_metrics is empty (rare
        # -- effectively every real CUR export has at least UnblendedCost):
        # DuckDB requires every column passed to GROUPING_ID to appear in
        # at least one grouping set, so resource_category/charge_type can't
        # be conditionally dropped here without also dropping them from
        # GROUPING_ID's argument list (and every GID constant with them).
        # Cheaper to compute two extra always-tiny grouping-set buckets in
        # that rare case than to carry two parallel bit-weight schemes.
        # Whether cost_metrics is empty is instead handled where drilldown/
        # day_drilldown rows get appended below, matching the old
        # behavior's "if cost_metrics:" gate exactly.
        grouping_sets = [
            "()",
            "(service)",
            "(day)",
            "(account_id)",
            "(account_id, service, resource_category, charge_type)",
            "(day, service, resource_category, charge_type)",
        ]

        base_select = (
            f"SELECT {service} AS service, {day} AS day, {account} AS account_id, "
            f"{currency_expr} AS currency, "
            f"COALESCE({resource_category_expr}, 'unknown') AS resource_category, "
            f"COALESCE({charge_type_expr}, 'unknown') AS charge_type"
            + (f", {metric_base_cols}" if metric_base_cols else "")
            + cost_base_col
            + f" FROM {source}"
        )

        rows = con.execute(
            f"SELECT service, day, account_id, resource_category, charge_type, "
            f"GROUPING_ID(service, day, account_id, resource_category, charge_type) AS gid, "
            f"MAX(currency) AS currency, SUM({cost_agg_source}) AS cost"
            + (f", {metric_sum_cols}" if metric_sum_cols else "")
            + f" FROM ({base_select}) AS base"
            + f" GROUP BY GROUPING SETS ({', '.join(grouping_sets)})"
        ).fetchall()

        total_cost = 0.0
        currency = None
        by_service: list[tuple] = []
        by_day: list[tuple] = []
        by_account: list[tuple] = []
        # The account drill-down: one row per (account, product category,
        # resource category, charge type) actually present, with every
        # detected cost metric alongside it -- e.g. "AmazonEC2 / Compute
        # Instance / Usage: {unblended_cost: 12.3, net_unblended_cost:
        # 11.8}". Grouped, not raw line items, so this stays small (bounded
        # by how many distinct combinations occur, not by row count) and
        # the frontend can pivot through it entirely client-side without
        # another request.
        drilldown = []
        # Same idea, grouped by calendar day instead of account. Account
        # isn't part of the group here -- that keeps this bounded by
        # day-count x distinct combinations rather than multiplying in
        # account cardinality too, and the "cost by day" view this powers
        # isn't per-account anyway.
        day_drilldown = []

        for row in rows:
            svc, day_val, acct, res_cat, chg_type, gid, curr, cost_val, *metric_values = row
            cost_val = float(cost_val or 0)
            if gid == GID_TOTAL:
                total_cost = cost_val
                currency = curr
            elif gid == GID_BY_SERVICE:
                by_service.append((svc, cost_val))
            elif gid == GID_BY_DAY:
                by_day.append((day_val, cost_val))
            elif gid == GID_BY_ACCOUNT:
                by_account.append((acct, cost_val))
            elif cost_metrics and gid == GID_DRILLDOWN:
                drilldown.append({
                    "account_id": str(acct) if acct is not None else "unknown",
                    "product_category": str(svc) if svc is not None else "unknown",
                    "resource_category": str(res_cat) if res_cat is not None else "unknown",
                    "charge_type": str(chg_type) if chg_type is not None else "unknown",
                    "costs": {name: float(v or 0) for name, v in zip(metric_names, metric_values)},
                })
            elif cost_metrics and gid == GID_DAY_DRILLDOWN and day_val is not None:
                day_drilldown.append({
                    "date": str(day_val),
                    "product_category": str(svc) if svc is not None else "unknown",
                    "resource_category": str(res_cat) if res_cat is not None else "unknown",
                    "charge_type": str(chg_type) if chg_type is not None else "unknown",
                    "costs": {name: float(v or 0) for name, v in zip(metric_names, metric_values)},
                })

        by_service.sort(key=lambda x: -x[1])
        by_account.sort(key=lambda x: -x[1])
        by_day = [(d, c) for d, c in by_day if d is not None]
        by_day.sort(key=lambda x: x[0])
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
        "available_cost_metrics": list(cost_metrics.keys()),
        "drilldown": drilldown,
        "day_drilldown": day_drilldown,
    }
