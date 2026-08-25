# S3 CUR Dashboard

Loads one month of an AWS Cost & Usage Report (CUR) straight from a
customer's S3 bucket via a cross-account role, and renders it as a
dashboard. There is no database and no server-side cache: every load is a
fresh read, and the data lives only in the browser tab's memory — refresh
the page and it's gone.

## How it works

1. **Auth**: the backend calls `sts:AssumeRole` with the role ARN + external
   ID supplied in the request. The resulting temporary credentials are used
   for that one request only and are never persisted.
2. **Locate the month**: CUR exports are partitioned into one folder per
   billing period (`<report>/<YYYYMMDD>-<YYYYMMDD>/` for legacy CUR, or
   `<report>/BILLING_PERIOD=<YYYY-MM>/` for CUR 2.0/Data Exports). The
   backend lists the report prefix once and picks the folder matching the
   requested month, then reads that folder's manifest — never anything
   outside the selected month.
3. **Read the part files**: the manifest lists every part file for that
   month, in whichever format the customer's export uses:
   - **Parquet** — columnar and splittable, read directly via DuckDB's
     `httpfs` extension with projection/predicate pushdown.
   - **Gzip CSV** — a single gzip member isn't splittable, but a CUR export
     is always many part files, so DuckDB still parallelizes across files
     even though each one decompresses on a single thread.

   Column names differ between the two formats (Parquet uses Athena-style
   `line_item_unblended_cost`, CSV uses the raw manifest header
   `lineItem/UnblendedCost`), so the columns the dashboard needs are
   resolved from the manifest's own column list at request time rather than
   hardcoded — this also means it tolerates schema variations (blended vs.
   unblended cost, CUR 2.0 renames, etc.).
4. **Aggregate**: total cost, cost by service, daily trend, and cost by
   linked account are computed with SQL `GROUP BY` in DuckDB, so only the
   aggregated result — not the raw line items — crosses into the API
   response.

## Running locally

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The AWS identity running the backend (or its default credential chain) only
needs `sts:AssumeRole` permission on the role(s) customers provide — it does
not need direct S3 access itself.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://localhost:8000` in dev (see
`vite.config.ts`).

## API

`POST /api/cur/load`

```json
{
  "role_arn": "arn:aws:iam::123456789012:role/CurReaderRole",
  "external_id": "customer-supplied-external-id",
  "s3_uri": "s3://my-cur-bucket/cur-reports/my-report",
  "month": "2026-06"
}
```

Returns total cost, cost by service, cost by day, and cost by linked
account for that billing period, plus `file_format`, `part_file_count`, and
`load_time_ms` so the read strategy and its cost are visible.

## Notes / follow-ups

- The customer's role trust policy must allow the backend's AWS identity to
  assume it, scoped with the external ID.
- `region` is auto-detected via `s3:GetBucketLocation` if not supplied;
  passing it explicitly skips that extra call.
- Only the classic CUR manifest shape (`columns` + `reportKeys`) and the
  CUR 2.0 `dataFiles` key are handled; if AWS changes the manifest schema
  again, `manifest.py`/`main.py` are the places to extend.
