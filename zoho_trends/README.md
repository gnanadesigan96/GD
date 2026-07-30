# Zoho Ticket Trend Dashboard

Quarter-over-quarter trend analysis of Zoho Desk support tickets (Jan 1 –
today), broken down by priority, customer, bundle (Category/Sub-Category),
and ticket type — with a drill-down view so you can pick one customer or
bundle and see its own quarter-by-quarter mix, the way it's described in the
brief (e.g. "Customer X raised 2 tickets in Q1 about cost-processing and
onboarding, then 6 in Q2 about budgets/onboarding/slowness").

Tickets from `notify-sre-ops@corestack.io`, any `@gmail.com` sender, and any
Gartner-related account/email are dropped automatically (`normalize.is_noise`).

## Files

| File | Purpose |
|---|---|
| `fetch_tickets.py` | Pulls **all** tickets (every status, not just the "active" ones the daily incident report uses) from Zoho Desk, Jan 1 → today. Requires network access to `desk.zoho.in` / `accounts.zoho.in` and `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET` / `ZOHO_REFRESH_TOKEN` env vars. |
| `normalize.py` | Noise filter, ticket-type keyword classifier, priority/quarter normalization. Loads either `fetch_tickets.py`'s JSON output or a Zoho Desk CSV export. |
| `build_dashboard.py` | Renders the self-contained HTML dashboard from normalized tickets. |
| `dashboard_template.py` | The dashboard's HTML/CSS/JS (no external dependencies — opens standalone in any browser). |
| `sample_data.py` | Generates synthetic demo data (`data/sample_tickets_raw.json`) so the dashboard can be previewed before real data is wired in. **Not real ticket data.** |

## Running it for real

This sandboxed session's network policy blocks `desk.zoho.in`, so the fetch
step has to run somewhere with Zoho access — the same constraint
`gen_report_live.py` already works under. Pick one:

**A. Run locally** (same pattern as `gen_report_live.py`):
```bash
export ZOHO_CLIENT_ID=...
export ZOHO_CLIENT_SECRET=...
export ZOHO_REFRESH_TOKEN=...
python3 fetch_tickets.py --start-date 2026-01-01
python3 build_dashboard.py --in data/tickets_raw.json --out trend_dashboard.html
```
Open `trend_dashboard.html` in a browser, or send it back for a live Artifact preview.

**B. Export from the Zoho Desk UI** — export tickets (Jan 1–today, all
statuses) as CSV with at least: Ticket Number, Subject, Priority, Status,
Account Name, Category, Created Time, Email. Then:
```bash
python3 build_dashboard.py --in tickets_export.csv --out trend_dashboard.html
```

**C. Grant this environment network access to `zoho.in`** in the Claude Code
environment settings, then re-run from a fresh session.

## Preview with synthetic data

```bash
python3 sample_data.py
python3 build_dashboard.py --in data/sample_tickets_raw.json --out sample_dashboard.html
```

## Tuning to your real taxonomy

- **Bundle** currently reads Zoho's `category` / `subCategory` field. If your
  bundles (FinOps/CloudOps/SecOps/etc.) live in a different custom field,
  point `normalize.normalize_json_ticket`'s `bundle = ...` line at it.
- **Ticket type** is keyword-matched against the subject line
  (`normalize.TYPE_KEYWORDS`). Once you see the dashboard against real data,
  tighten/expand those keyword lists to match actual ticket language.

## Known issue in this repo (not part of this feature)

`gen_report_live.py` has a live Zoho client secret and refresh token
hardcoded as fallback default values (`os.environ.get("ZOHO_CLIENT_SECRET",
"...")`), committed to git history. Worth rotating those credentials in
Zoho and stripping the fallbacks regardless of this dashboard work.
