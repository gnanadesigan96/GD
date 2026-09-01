# Resume Auto-Apply Assistant

A personal web app that:

1. Takes your resume (PDF/DOCX/TXT) and profile (target roles, years of
   experience, target locations).
2. Pulls open roles matching those roles/locations from job board APIs.
3. Uses Claude to rewrite your resume and draft a cover letter tailored to
   each specific posting, without inventing experience you don't have.
4. Tracks each job's status (new → tailored → applied → interview → …) on a
   dashboard.

**It does not submit applications for you.** Job boards like LinkedIn and
Indeed prohibit automated submissions in their terms of service, and
bot-submitted applications risk your account being banned. Instead, for
each match you get a tailored resume + cover letter ready to download, and a
link to the original posting — you review and click "Apply" yourself.

## Job sources

Configured out of the box for your target markets (Chennai/India, Dubai/UAE,
Europe):

- **Adzuna** — covers India and several European countries (UK, Germany,
  France, Netherlands, Spain, Italy, Poland). Free key at
  https://developer.adzuna.com/
- **Jooble** — much broader country coverage, including UAE/Dubai. Free key
  at https://jooble.org/api/about

Both are optional independently; the app works (in "fetch" mode) with either
one configured, and skips whichever isn't.

## Setup

```bash
cd resume-auto-apply
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: add ANTHROPIC_API_KEY, and ADZUNA_APP_ID/ADZUNA_APP_KEY and/or JOOBLE_API_KEY
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/settings, upload your resume, and set:

- Target roles: `Product Specialist, Business Analyst, Customer Success Manager`
- Target locations: `Chennai, India, Dubai, UAE, Europe`
- Years of experience: `8`

Go back to the dashboard and click **Fetch new jobs**, then open any match to
generate a tailored resume + cover letter.

## Notes

- All data (uploaded resume, generated documents, the SQLite database) is
  stored under `data/`, which is gitignored — nothing here is meant to be
  committed.
- This runs unauthenticated. It's meant for local/private use; don't expose
  it on the open internet without adding authentication, since it holds your
  resume and contact details.
- Adzuna has no single "Europe" endpoint; when a target location is just
  "Europe" the app fans out across the UK, Germany, France, Netherlands,
  Spain, Italy, and Poland. Add specific countries to your target locations
  for more control.
