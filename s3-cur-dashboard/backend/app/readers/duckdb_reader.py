"""Aggregate a single month's CUR part files with DuckDB.

Both CUR file formats are handled the same way: point DuckDB's httpfs
extension at the list of part-file S3 keys from the manifest and let it read
them directly over the network using the assumed-role's temporary
credentials.

- Parquet parts are columnar and splittable, so DuckDB pushes projection and
  predicate filters down and only pulls the bytes the aggregation needs.
- Gzip-CSV parts are not splittable *within* a file, but a CUR export is
  always split into many part files, so DuckDB still parallelizes across
  files -- each part decompresses on its own thread.

No data is written to disk and nothing is cached between requests: the
DuckDB connection and the temporary credentials are discarded as soon as the
request finishes, matching the "wiped on refresh" requirement.
"""

import duckdb
from fastapi import HTTPException

from ..cur_columns import ResolvedColumn


def _build_source(file_format: str, paths: list[str]) -> str:
    array_literal = "[" + ", ".join(f"'{p}'" for p in paths) + "]"
    if file_format == "parquet":
        return f"read_parquet({array_literal}, union_by_name=true)"
    # compression='auto' (not a hardcoded 'gzip'): CUR CSV exports aren't
    # always gzip-compressed -- main.py's format detection only checks for
    # ".parquet", so anything else lands here regardless of whether it's
    # actually gzip, uncompressed, or something else DuckDB can sniff from
    # the file itself. Hardcoding 'gzip' broke with "Input is not a GZIP
    # stream" against a real, uncompressed CUR export.
    return f"read_csv({array_literal}, header=true, compression='auto', all_varchar=true, union_by_name=true)"


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

    # duckdb.Error is caught (and its message logged ourselves, via print --
    # captured by CloudWatch same as any stdout write) rather than left to
    # propagate: a Lambda invocation that saw one has, in practice, cut off
    # the exception's own message before it reached CloudWatch, leaving only
    # a bare 500 with no way to tell what actually failed.
    try:
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
    finally:
        con.close()

    return {
        "total_cost": float(total_cost),
        "currency": currency,
        "cost_by_service": [{"service": str(s) if s is not None else "unknown", "cost": float(c or 0)} for s, c in by_service],
        "cost_by_day": [{"date": str(d), "cost": float(c or 0)} for d, c in by_day if d is not None],
        "cost_by_account": [{"account_id": str(a) if a is not None else "unknown", "cost": float(c or 0)} for a, c in by_account],
    }
