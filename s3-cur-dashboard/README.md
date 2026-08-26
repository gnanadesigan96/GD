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
   `<report>/BILLING_PERIOD=<YYYY-MM>/` for CUR 2.0/Data Exports). `s3_uri`
   only has to name the bucket (`my-cur-bucket`) or a bucket + `s3://`
   scheme (`s3://my-cur-bucket`) — the report's own prefix inside the
   bucket is optional. When it's given, the backend lists just that prefix;
   when it's omitted, the backend scans the whole bucket for a manifest
   matching the requested month instead (slower, since it's listing
   everything in the bucket, but means the customer never has to hand us
   their exact report path). Either way, it picks the folder matching the
   requested month and reads that folder's manifest — never anything
   outside the selected month. AWS regenerates a billing period's report
   repeatedly as costs settle, and each regeneration is a full cumulative
   report for the month (not a delta), so when a customer's report history
   setting leaves multiple versioned manifests for the same month, the
   backend picks the one with the newest S3 `LastModified` — the latest
   regeneration already has every day's cost for the month so far, so older
   versions are never read.
3. **Read the part files**: the manifest lists every part file for that
   month, in whichever format the customer's export uses:
   - **Parquet** — columnar and splittable, read directly via DuckDB's
     `httpfs` extension with projection/predicate pushdown.
   - **Gzip or uncompressed CSV** — a single gzip member isn't splittable,
     but a CUR export is always many part files, so DuckDB still
     parallelizes across files even though each one decompresses (if
     compressed at all — `compression='auto'` sniffs per file rather than
     assuming) on a single thread.
   - **ZIP-compressed CSV** (legacy CUR's other compression option) — a
     real ZIP archive per part, which DuckDB can't read directly the way it
     can sniff gzip or plain CSV from a stream. Each part is downloaded via
     boto3 (in parallel) and its single CSV member extracted to a
     per-request `/tmp` directory before DuckDB reads it locally; the
     extracted files are deleted once the request finishes, success or
     failure, so nothing from one request's data survives into another
     request on a reused warm Lambda container.

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
5. **Run it as a background job, not one blocking request**: a real CUR
   export can take anywhere from seconds to several minutes to download and
   aggregate — comfortably past API Gateway's hard, non-configurable
   30-second integration timeout. `POST /api/cur/load` only creates a job
   record and fires an async (fire-and-forget) self-invocation of the same
   Lambda to do the actual work; the frontend polls
   `GET /api/cur/job/{job_id}` every couple of seconds until it's done. Job
   status and the final result live in a DynamoDB table with a short
   auto-expiring TTL (30 minutes) — only that small aggregated result is
   ever stored there, and only briefly, so this stays close to the "nothing
   persists" spirit even though it's a real (if short-lived) departure from
   "nothing is ever written down".

## Running locally

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values, or set these as real env vars/secrets
uvicorn app.main:app --reload
```

The backend calls `sts:AssumeRole` *as* some IAM identity, which must be a
principal named in the customer's role trust policy. That caller identity's
access key / secret key are resolved in priority order (`app/aws_client.py`):

1. **Azure Key Vault** (`app/secrets.py`) — replace the placeholder
   `KEY_VAULT_URL` / secret names there (or set `AZURE_KEY_VAULT_URL` /
   `AZURE_KV_ACCESS_KEY_SECRET_NAME` / `AZURE_KV_SECRET_KEY_SECRET_NAME`)
   once the vault is provisioned. Auth uses `DefaultAzureCredential`, so it
   picks up Managed Identity on Azure or an `az login` session locally with
   no extra config.
2. `CUR_DASHBOARD_CALLER_ACCESS_KEY_ID` / `CUR_DASHBOARD_CALLER_SECRET_ACCESS_KEY`
   env vars (see `.env.example`), used only if no vault is configured.
3. boto3's default credential chain (instance/task role, etc.) if neither
   of the above is set — prefer that over static keys wherever it's
   available.

The key material never has to live in code or a committed file either way.
This identity only needs `sts:AssumeRole` permission on the role(s)
customers provide; it does not
need direct S3 access itself.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://localhost:8000` in dev (see
`vite.config.ts`).

## Deployment (AWS Lambda + S3)

The dashboard is the human interface: a person opens the frontend page in a
browser, fills in role ARN / external ID / S3 URI / month, and clicks "Load
report" — that form submission is the only input this system takes. There
is no separate config file or CLI to drive it.

- **Backend** runs as a container-image Lambda function behind an API
  Gateway HTTP API (Lambda proxy integration, quick-create mode).
  `app/lambda_handler.py` wraps the same FastAPI app used locally via
  [Mangum](https://github.com/jordaneremieff/mangum) for normal HTTP
  requests, so there's no route/logic fork between `uvicorn` and Lambda —
  but it also routes a second, internal event shape (`{"cur_job": ...}`)
  straight to the job-running code, bypassing Mangum entirely. That's how
  the async self-invocation described above reaches the same Lambda
  without going through API Gateway a second time.
- **Frontend + API share one CloudFront distribution**: a static build
  synced to a private S3 bucket serves the frontend at `/`, and a `/api/*`
  behavior forwards to the API Gateway endpoint. The S3 origin uses Origin
  Access Control, so the bucket needs no public (`Principal: "*"`)
  resource policy; the API Gateway origin is a plain public custom origin
  (API Gateway's default endpoint is already public). This still means the
  frontend calls its API same-origin, so no CORS is needed, and there's
  only one domain to remember. Access control on the API is the app-level
  `CUR_DASHBOARD_API_KEY` (below), not IAM signing.

  (Why API Gateway and not a Lambda Function URL: a `NONE`-auth Function
  URL needs a public (`Principal: "*"`) resource policy, which this
  account's setup rejected outright — confirmed twice, both behind
  CloudFront + Origin Access Control (a controlled test proved a genuinely
  SigV4-signed request straight to the Function URL succeeded, but
  CloudFront's OAC-signed request to that same URL did not) and called
  directly with no CloudFront involved at all. API Gateway's Lambda proxy
  integration is a much older, more battle-tested path that sidesteps both
  failures — its own 30-second timeout is what the async job pattern above
  works around instead.)

```bash
# 1. Deploy the backend (builds + pushes a container image, creates the
#    Lambda function and an API Gateway HTTP API in front of it)
AWS_REGION=us-east-1 ./deploy/deploy_backend.sh

# 2. Deploy the frontend -- this also wires the API Gateway endpoint into
#    the same CloudFront distribution as the /api/* origin
LAMBDA_FUNCTION_NAME=cur-dashboard-backend BUCKET=my-cur-dashboard-frontend \
  ./deploy/deploy_frontend.sh
```

The backend's job is to call `sts:AssumeRole` on whatever role ARN it's
given, so it's still worth an extra layer even behind CloudFront: set
`CUR_DASHBOARD_API_KEY` on the Lambda and pass the same value as `API_KEY`
to `deploy_frontend.sh`; the frontend sends it as `x-api-key` and the
backend rejects requests without a match (see `require_api_key` in
`app/main.py`). Left unset, both sides skip it — convenient for local dev.

`deploy/deploy_frontend.sh` prints the CloudFront domain
(`https://<id>.cloudfront.net`) at the end — that's the URL to open. It
uses `PriceClass_100` (US/Canada/Europe edge locations only, the cheapest
tier) since cost is the priority here; CloudFront's 1TB/month + 10M
requests/month free tier is permanent, so this stays $0 at low traffic. Re-
running the script after a content-only change (no new distribution)
invalidates the CloudFront cache so the new build is served immediately
instead of waiting for the old one to expire.

### Custom domain

A custom domain instead of `*.cloudfront.net` needs a certificate in ACM's
`us-east-1` region (required by CloudFront regardless of the distribution's
own edge locations), plus a DNS record pointing the domain at the
distribution.

If you already have a certificate/key (rather than one ACM should issue and
DNS-validate itself), import it first:

```bash
CERT_FILE=/path/to/certificate.pem \
CHAIN_FILE=/path/to/intermediate-chain.pem \
KEY_FILE=/path/to/private.key \
./deploy/import_certificate.sh
# -> prints ACM_CERT_ARN
```

The chain file should contain intermediate certificate(s) only, not the
self-signed root — if your CA gave you a bundle with the root included,
strip it (`awk` on `-----BEGIN CERTIFICATE-----` boundaries, keeping only
the first block, works for a two-cert bundle). The script verifies the key
matches the certificate before importing and never prints the key itself.
An imported certificate does not auto-renew — re-import before it expires.

Then deploy (or redeploy) the frontend with the domain and that ARN:

```bash
DOMAIN_NAME=cur.example.com ACM_CERT_ARN=<arn-from-above> \
LAMBDA_FUNCTION_NAME=cur-dashboard-backend BUCKET=my-cur-dashboard-frontend \
./deploy/deploy_frontend.sh
```

This works whether the distribution already exists (it gets updated in
place) or is being created fresh. The script prints the CNAME (or
ALIAS/ANAME, if the domain is a bare apex) record to add on your DNS
provider, pointing at the CloudFront domain.

`deploy_backend.sh` also applies an ECR lifecycle policy on every run:
untagged images (left behind whenever a later push moves the `latest` tag
off them) expire after 1 day, and the repo never keeps more than 5 images
total — otherwise every redeploy would add another image to ECR's storage
bill forever.

## API

`POST /api/cur/load` starts the load as a background job:

```json
{
  "role_arn": "arn:aws:iam::123456789012:role/CurReaderRole",
  "external_id": "customer-supplied-external-id",
  "s3_uri": "my-cur-bucket",
  "month": "2026-06"
}
```

Returns `202` with `{"job_id": "..."}` immediately — this endpoint does no
S3/STS work itself, so it stays fast regardless of how big the export
turns out to be.

`GET /api/cur/job/{job_id}` polls for the result:

```json
{"status": "pending"}
```
```json
{"status": "done", "result": { "total_cost": ..., "cost_by_service": [...], "...": "..." }}
```
```json
{"status": "error", "error": "..."}
```

`result` (once `status` is `"done"`) has total cost, cost by service, cost
by day, and cost by linked account for that billing period, plus
`file_format`, `part_file_count`, and `load_time_ms` so the read strategy
and its cost are visible. A `job_id` not found (expired, or never existed)
returns `404`.

It also carries everything the per-account drill-down UI needs, computed
in the same pass as everything else above (one extra `GROUP BY`, not a
second read of the export):

- `available_cost_metrics` — whichever cost columns this specific export
  actually has (e.g. `["unblended_cost", "blended_cost"]`; `net_*` variants
  only show up once an account has Reserved Instances or Savings Plans).
- `drilldown` — one row per `(account_id, product_category,
  resource_category, charge_type)` combination that occurs in the bill,
  each carrying every metric in `available_cost_metrics`. Still grouped,
  not raw line items — bounded by how many distinct combinations exist,
  not by row count. `product_category` is the same value as
  `cost_by_service`'s `service`; `resource_category` resolves to
  `product/productFamily` and `charge_type` to `lineItem/LineItemType`
  when present, falling back to `"unknown"` for exports that lack them.

`cost_by_day` entries also carry a `costs` map (cost per metric for that
day) alongside the existing `date`/`cost` fields — no product/resource/
charge-type dimension, just the metric breakdown. There used to be a
separate `day_drilldown` array with the full category breakdown per day,
mirroring the account one; it was removed because day-count × every other
dimension's combinations made it by far the largest of the backend's
grouping-set buckets, and cutting it measurably reduces peak memory on a
large export. Clicking a day in the UI now shows a small per-metric table
(`DayCostBreakdown`) instead of the full `DrilldownPanel`.

The frontend fetches this all once and drills through it entirely
client-side — clicking an account in "Cost by linked account" needs no
further request. It renders through the shared `DrilldownPanel` component
(metric → dimension → search, with click-to-expand rows to reconcile
totals across dimensions).

It also carries `part_files` — one `{key, size_bytes}` entry per part file
in the manifest, resolved with one (occasionally a handful of) paginated
`list_objects_v2` calls grouped by the part files' common S3 prefix rather
than a `HeadObject` per file. Clicking the "Part files scanned" KPI in the
UI opens a table of these. Selecting up to 10 accounts in "Cost by linked
account" and choosing a cost metric lets the frontend build a CSV report
from `drilldown` (account, product category, resource category, charge
type, cost) entirely client-side and trigger a browser download — no
extra request either, since the data's already loaded.

## Notes / follow-ups

- The customer's role trust policy must allow the backend's AWS identity to
  assume it, scoped with the external ID.
- `region` is auto-detected via `s3:GetBucketLocation` if not supplied;
  passing it explicitly skips that extra call.
- Only the classic CUR manifest shape (`columns` + `reportKeys`) and the
  CUR 2.0 `dataFiles` key are handled; if AWS changes the manifest schema
  again, `manifest.py`/`main.py` are the places to extend.
- A very large export can still outgrow Lambda's memory and its ephemeral
  storage (already maxed at 10GB — see `deploy_backend.sh`), surfacing as a
  DuckDB "Out of Memory" / `max_temp_directory_size` error, which is what
  happened against a real large customer export. Three things address
  this: Lambda's memory is set to its own max (10240MB); DuckDB's
  `memory_limit` is pinned to ~80% of that (via the
  `AWS_LAMBDA_FUNCTION_MEMORY_SIZE` env var Lambda provides) so it spills
  to disk as late as possible; and — the main fix —
  `duckdb_reader.aggregate()` no longer materializes a full row-level copy
  of the export into a temp table at all. Every breakdown (total,
  by-service, by-day, by-account, the account drill-down) comes out of a
  single `GROUP BY GROUPING SETS (...)` query that runs as one
  `HASH_GROUP_BY` over one scan of the source (confirmed via `EXPLAIN`),
  tagging each output row's grouping set via `GROUPING_ID(...)` rather than
  a temp table + separate re-queries of it -- and the day-level category
  drill-down (by far the largest of the grouping-set buckets) was dropped
  entirely in favor of a lighter per-metric-only breakdown, further cutting
  peak memory. Verified against a 3,000-row randomized synthetic export
  cross-checked row-for-row against an independent pure-Python reference
  implementation.
