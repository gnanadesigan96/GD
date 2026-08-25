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

- **Backend** runs as a container-image Lambda function behind a Lambda
  Function URL (an HTTPS endpoint, no API Gateway needed — no extra cost
  beyond Lambda itself). `app/lambda_handler.py` wraps the same FastAPI app
  used locally via [Mangum](https://github.com/jordaneremieff/mangum), so
  there's no route/logic fork between `uvicorn` and Lambda.
- **Frontend** is a static build synced to a private S3 bucket, served over
  HTTPS through a CloudFront distribution (using Origin Access Control, so
  only CloudFront — not the public internet — can read the bucket
  directly), and pointed at the deployed Function URL via
  `VITE_API_BASE_URL` at build time.

```bash
# 1. Deploy the backend (builds + pushes a container image, creates the
#    Lambda function and its Function URL)
AWS_REGION=us-east-1 ./deploy/deploy_backend.sh
# -> prints the Function URL

# 2. Deploy the frontend, pointed at that URL
API_BASE_URL=<function-url-from-step-1> BUCKET=my-cur-dashboard-frontend \
  ./deploy/deploy_frontend.sh
```

A Lambda Function URL with `AuthType=NONE` is invocable by anyone who has
the URL, and this backend's job is to call `sts:AssumeRole` on whatever role
ARN it's given — so before sharing the URL with real users, set
`CUR_DASHBOARD_API_KEY` on the Lambda (see the output of
`deploy_backend.sh`) and pass the same value as `API_KEY` to
`deploy_frontend.sh`; the frontend sends it as `x-api-key` and the backend
rejects requests without a match (see `require_api_key` in `app/main.py`).
Left unset, both sides skip it — convenient for local dev, not for a public
URL.

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
API_BASE_URL=<function-url> BUCKET=my-cur-dashboard-frontend \
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
