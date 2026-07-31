# Zoho Ticket Trend Dashboard

Quarter-over-quarter trend analysis of Zoho Desk support tickets, broken down
by priority, customer, bundle, and ticket type — with a drill-down view so
you can pick one customer or bundle and see its own quarter-by-quarter mix
(e.g. "Customer X raised 2 tickets in Q1 about cost-processing and
onboarding, then 6 in Q2 about budgets/onboarding/slowness").

Tickets from `notify-sre-ops@corestack.io`, any `@gmail.com` sender, any
Gartner-related account/email, and internal/Corestack-placeholder accounts
("internal", "Corestack", "CoreStack_CS") are dropped automatically
(`normalize.is_noise`, `normalize.INTERNAL_ACCOUNT_LABEL`).

## `webapp/` — the self-service dashboard (start here)

An Azure Function (same deployment pattern as `azure-function/`) that serves
a page where **you paste your own Zoho credentials in the browser** — no
Zoho secret is stored server-side anywhere. It fetches the current quarter +
previous 2 quarters (configurable) and renders the same dashboard described
below.

```bash
cd zoho_trends/webapp
pip install -r requirements.txt
cp local.settings.json.template local.settings.json   # no Zoho values needed here
func start
# open http://localhost:7071/api/dashboard
```

### Deploying it to get a real URL

`webapp/deploy.sh` provisions a resource group + storage account + Linux
Python Function App and publishes this folder to it in one go. Run it from
your own machine or Azure Cloud Shell (needs the Azure CLI logged in —
`az login` — and Azure Functions Core Tools v4):

```bash
cd zoho_trends/webapp
# edit the RESOURCE_GROUP / LOCATION / FUNCTION_APP_NAME variables at the top first
./deploy.sh
```

This can't be run from this Claude Code sandbox — it needs network access to
`management.azure.com`, which this environment's egress policy also blocks
(same class of restriction as the `zoho.in` block below). Once deployed,
the dashboard is at `https://<your-function-app-name>.azurewebsites.net/api/dashboard`.

The route uses anonymous auth (`AuthLevel.ANONYMOUS` in `function_app.py`) —
anyone with the URL can load the page and POST to `/api/tickets` with
*their own* Zoho credentials (nothing of yours is exposed by that), but it
does mean the endpoint itself isn't gated. Put it behind your org's SSO,
Front Door, or an IP restriction if it shouldn't be publicly reachable.

On the page itself: enter Client ID, Client Secret, Refresh Token (Org ID /
Department ID are pre-filled with CoreStack Support's defaults), pick the
window (current + last N quarters, default 2), click **Load dashboard**.

**Credential handling:** sent once per request to the function's own `/api/tickets`
endpoint, used in-memory to call Zoho, then discarded — never logged, never
written to disk, never persisted across a page reload. Deploy behind HTTPS
(Azure Functions gives you this by default) since credentials travel in the
POST body.

## Confirmed real Zoho field mappings

Verified against live CoreStack Support department data (not guessed):

| Concept | Field | Notes |
|---|---|---|
| Bundle | `cf.cf_bundle` / `customFields["Reporting Bundle"]` | **Not** Category/Sub-Category — those are unused (always empty) on this department. Values seen: CloudOps, FinOps, Core, SecOps, Analytics. |
| Ticket type | `cf.cf_feature` / `customFields["Reporting Feature"]` | CoreStack's own curated taxonomy (Cost processing, Onboarding, Budget, Access, Executive dashboard, ...). Falls back to subject-keyword classification (`normalize.TYPE_KEYWORDS`) only when this is blank/"NA". |
| Customer | `contact.account.accountName` (list/search endpoints nest it here) → `account.accountName` (single-ticket endpoint) → `cf.cf_customer` | Internal placeholder names ("internal", "Corestack", "CoreStack_CS") are excluded entirely (`normalize.INTERNAL_ACCOUNT_LABEL`), same as notify-sre/Gmail/Gartner. |

## Data-quality finding that shaped the filter

A live sample pull (300 tickets across Q1–Q3 2026) found **58% were
notify-sre noise** — the filter is doing real work. A further ~17% were
other `@corestack.io` senders tagged account "Corestack"/"CoreStack_CS"
(customer = "internal") — not notify-sre, not Gmail, not Gartner by name,
but clearly not a real customer either, so those are now excluded too.

## Files

| File | Purpose |
|---|---|
| `webapp/` | The Azure Function above — self-contained, own copy of `normalize.py`, credentials supplied per-request. |
| `fetch_tickets.py` | CLI fetch: current quarter + previous 2 quarters (rolling window) from Zoho Desk, every status. Requires network access to `desk.zoho.in` / `accounts.zoho.in` and `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET` / `ZOHO_REFRESH_TOKEN` env vars. |
| `normalize.py` | Noise filter, bundle/type/customer field mapping, quarter-window math. Loads either `fetch_tickets.py`'s JSON output or a Zoho Desk CSV export. |
| `build_dashboard.py` | Renders the same dashboard as a static HTML file from normalized tickets (no server needed). |
| `dashboard_template.py` | That static dashboard's HTML/CSS/JS. |
| `sample_data.py` | Generates synthetic demo data. **Not real ticket data.** |

## Running the static (no-server) version

```bash
export ZOHO_CLIENT_ID=...
export ZOHO_CLIENT_SECRET=...
export ZOHO_REFRESH_TOKEN=...
python3 fetch_tickets.py                 # defaults to current quarter + last 2
python3 build_dashboard.py --in data/tickets_raw.json --out trend_dashboard.html
```
Or from a Zoho Desk CSV export: `python3 build_dashboard.py --in tickets_export.csv`.

## Preview with synthetic data

```bash
python3 sample_data.py
python3 build_dashboard.py --in data/sample_tickets_raw.json --out sample_dashboard.html
```

## Known issue in this repo (not part of this feature)

`gen_report_live.py` has a live Zoho client secret and refresh token
hardcoded as fallback default values (`os.environ.get("ZOHO_CLIENT_SECRET",
"...")`), committed to git history. Worth rotating those credentials in
Zoho and stripping the fallbacks regardless of this dashboard work.
