# Jobseeker AI

An experiment built using [Claude](https://claude.com) (Anthropic's AI) to
explore how far an agentic pipeline can go for personal job hunting — built
and iterated on entirely through conversation with Claude Code, including
finding and fixing several real bugs along the way (see commit history / the
"Known limitations" section below for specifics).

Finds .NET developer **or** Agentic AI/LLM engineering roles in Australia/Europe
that offer visa sponsorship or relocation, tailors your resume + drafts a cover
letter per posting with Claude, and emails you the results (with a ready-to-send
cover letter PDF per job) to review and apply manually. **It never submits
applications itself.**

> ⚠️ **This repo is public.** `job_search/base_resume.json` ships as a
> placeholder template — see step 1 below for how to fill in your real details
> locally without ever committing them.

## How it works

```
GitHub Actions (runs twice daily — see Scheduling below)
  -> fetch: Adzuna (AU + Europe), Arbeitnow, Remotive, RemoteOK, The Muse, Jooble,
            Greenhouse/Lever/Ashby (direct company career-page boards you configure)
            (+ optional: LinkedIn/Indeed public search pages, off by default)
            Adzuna/Remotive/Jooble are queried once per JOB_QUERY and once per
            AI_JOB_QUERY (their APIs restrict results server-side); the rest
            ignore the query and fetch everything, relying on the filter below
  -> filter: (.NET/C# keywords OR Agentic AI/LLM keywords) AND visa/relocation
             keywords AND AU/Europe location
  -> dedupe: skip jobs already in job_search/seen_jobs.json
  -> tailor: Claude rewrites your resume summary + drafts a cover letter per job,
             flagging a warning if the posting wants meaningfully more years of
             experience than you have, or looks like a false visa/relocation match
  -> save: full tailored draft (job_search/drafts/*.md), a print-ready resume
            PDF, and a cover letter PDF per job; job_search/dashboard_data.json
            records everything the dashboard needs (below), including a
            contact email auto-detected in the posting text, if one exists
  -> email: the job's real "Apply here" link + cover letter PDF attached,
            batched at up to 10 jobs per email (extra jobs spill into further
            emails rather than one unbounded message)
  -> persist: seen_jobs.json + drafts/ + dashboard_data.json committed back to
              the repo. Only jobs whose email actually sent are marked seen —
              if one batch's send fails, that batch retries next run instead
              of being dropped
```

Applying is manual: open the "Apply here" link, use the attached resume/cover
letter PDFs, and submit through the site yourself — or use the local dashboard
below, which can also draft an email directly for postings that list a contact
address instead of (or alongside) an application form.

## Dashboard

A minimal local review UI — run `python -m job_search.dashboard.app` and open
http://127.0.0.1:5000. For each tracked job it shows the tailored summary,
skills, any warning, an "Apply here" link, resume/cover-letter PDF downloads,
and — only when the posting's own text contains a contact email address — an
"Email" button. That button creates a real Gmail **draft** (both PDFs
attached) via the Gmail API; it never sends anything. You open the draft in
Gmail, review it, and send it yourself.

Most postings won't show an Email button — they expect an application through
the job board's own form instead, which is what "Apply here" is for. The
button only appears when a real address was found in the description text.

### One-time Gmail API setup (only needed for the Email button)
The digest email itself keeps using the Gmail app password from step 3 above —
this is a separate, additional credential needed only for *creating drafts*,
since app passwords can't do that (only real OAuth can):

1. Go to https://console.cloud.google.com/ and create a project (or reuse one).
2. Enable the **Gmail API** for that project (APIs & Services → Library).
3. Configure the OAuth consent screen: User type **External**, publishing
   status **Testing** (this avoids Google's app-verification review — fine for
   a personal single-user tool), and add your own Gmail address as a test user.
4. Create credentials → OAuth client ID → Application type **Desktop app**.
   Download the JSON.
5. Save it as `gmail_oauth_client_secret.json` in the repo root (already
   gitignored — never commit it).
6. Run the dashboard and click "Email" on any job with the button — the first
   time, it opens a browser for one-time consent, then caches a refresh token
   in `gmail_oauth_token.json` (also gitignored) so you won't need to log in
   again.

## Setup

### 1. Fill in your real resume
Edit `job_search/base_resume.json` with your actual experience, skills, and
contact info. This is the only source of truth the tailoring step is allowed to
draw from — it will not invent experience beyond what's here. The optional
`"projects"` array is what the tailoring step draws from for Agentic AI/LLM
engineering postings (vs. `"experience"` for .NET postings) — consider adding
an entry for a project like this one if you build/extend it yourself, since
that's genuine, relevant hands-on experience.

**Since this repo is public**, tell git to stop tracking your local edits to
this one file, so `git add -A` / a normal commit never picks up your real
details:
```
git update-index --skip-worktree job_search/base_resume.json
```
(To resume tracking it later — e.g. to update the placeholder template itself
— run `git update-index --no-skip-worktree job_search/base_resume.json` first.)

### 2. Get API keys (all free)
- **Adzuna**: register at https://developer.adzuna.com/ → `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`.
  Searches Australia + Europe by default (`ADZUNA_COUNTRIES=au,gb,de,nl,at,fr,it,pl`) —
  override in `.env` if you want different countries.
- **Jooble**: get a key at https://jooble.org/api/about → `JOOBLE_API_KEY`
- **The Muse** (optional, works without a key at a lower rate limit): https://www.themuse.com/developers/api/v2 → `THEMUSE_API_KEY`
- **Arbeitnow, Remotive, RemoteOK**: no key needed
- **Claude**: no API key needed — see step 2b. This project deliberately avoids
  console.anthropic.com pay-as-you-go billing and uses your existing Claude
  Pro/Max subscription instead.

### 2a. Direct-company job boards (no key needed)
Instead of only aggregators, the agent also fetches specific companies' own
career pages directly — genuinely public JSON APIs their ATS vendor publishes
for embedding listings (not scraping), so there's no ToS gray area like the
LinkedIn/Indeed module below.

**A default pool of ~76 companies is built in** (`job_search/config.py`,
sourced from [santifer/career-ops](https://github.com/santifer/career-ops)'s
company list), so this works out of the box with no setup. That list was
originally curated for AI/ML roles, so most of these aren't .NET shops — that's
harmless, since the .NET keyword filter downstream excludes irrelevant
postings automatically, and a handful of stale/renamed slugs (~15 of 76 as of
this writing) are logged and skipped per-company rather than breaking the run.

To use your own list instead of the default, set these as a comma-separated
list of board tokens (found in the company's careers page URL):

| ATS | URL pattern | Env var |
|---|---|---|
| Greenhouse | `boards.greenhouse.io/<token>` | `GREENHOUSE_COMPANIES` |
| Lever | `jobs.lever.co/<token>` | `LEVER_COMPANIES` |
| Ashby | `jobs.ashbyhq.com/<token>` | `ASHBY_COMPANIES` |

For best signal, swap in .NET-heavy fintech/enterprise companies with EU/AU
offices that you're actually targeting.

### 2b. Claude Code subscription token (for tailoring)
The resume/cover-letter step calls the `claude` CLI in headless mode
(`claude -p`), which uses your Claude subscription's included usage instead of
metered API billing — as long as `ANTHROPIC_API_KEY` is not set anywhere in the
environment it runs in (it takes priority over the subscription if present).

1. Install Claude Code locally if you haven't: `npm install -g @anthropic-ai/claude-code`
2. Make sure you're logged in with your Pro/Max account (`claude` then `/login`
   if needed).
3. Generate a long-lived token for CI: `claude setup-token` — this mints a
   one-year OAuth token tied to your subscription.
4. Save it as `CLAUDE_CODE_OAUTH_TOKEN` (repo secret in step 5 below; not
   needed in your local `.env` if you're already logged into `claude`
   interactively on this machine).

### 3. Gmail app password (for sending the digest)
1. Enable 2-Step Verification on your Google account if not already on.
2. Go to https://myaccount.google.com/apppasswords and generate an app password.
3. Use your Gmail address as `GMAIL_ADDRESS` and the generated password as
   `GMAIL_APP_PASSWORD`. Set `NOTIFY_TO` to whichever address should receive the
   digest (can be the same address).

### 4. Local test run
```
cp .env.example .env   # fill in real values
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code   # if not already installed
python -m dotenv run -- python -m job_search.main
```
Confirm a real email arrives and `job_search/seen_jobs.json` gets new entries.
Run it again — it should report 0 new jobs (dedupe working).

### 5. Push to GitHub and configure secrets
Push this project to your GitHub repo. If it's public (like the original), make
sure you've done the `git update-index --skip-worktree` step above first, and
double-check `git status`/`git diff --cached` before committing to confirm
your real resume details aren't in the diff. In the repo's Settings → Secrets
and variables → Actions, add each of these as a repository secret: `CLAUDE_CODE_OAUTH_TOKEN` (from step
2b), `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `JOOBLE_API_KEY`, `THEMUSE_API_KEY`,
`GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `NOTIFY_TO`. Do **not** add an
`ANTHROPIC_API_KEY` secret — its presence would override the subscription
token and switch tailoring to metered billing. Optionally add
`ENABLE_LINKEDIN_INDEED`, `JOB_QUERY`, `AI_JOB_QUERY`, `ADZUNA_COUNTRIES`,
`GREENHOUSE_COMPANIES`, `LEVER_COMPANIES`, and `ASHBY_COMPANIES` as repository
**variables** (not secrets — they're not sensitive) if you want to override
the defaults.

Run the workflow manually once via the Actions tab (`workflow_dispatch`) before
trusting the scheduled runs.

## Scheduling

The workflow runs **twice a day**, timed to each region's business-day start
rather than "market open + market close":

- **`0 6 * * *` (06:00 UTC)** — ~7–8am Central European time (varies with
  daylight saving), catching fresh postings as European recruiters start
  their day.
- **`0 22 * * *` (22:00 UTC)** — ~8–9am Australian Eastern time, same idea for
  Australia.

**Why twice, not four times a day (open + close, per region):** job postings
don't meaningfully change within a few hours — a role posted at 9am is still
there at 5pm — so a market-close run mostly re-fetches the same listings the
next morning's run would catch anyway, for little added benefit. It also has a
real cost: Adzuna's free tier is ~1,000 calls/month, and each run already costs
8 calls (one per country in `ADZUNA_COUNTRIES`). Twice a day is ~480 calls/month;
four times a day would be ~960/month, leaving almost no headroom for manual
testing or added countries. If you still want a close-of-day run, add a third
`cron` line to `.github/workflows/job-search.yml` — just watch the Adzuna quota
if you do.

## The LinkedIn/Indeed module (optional, off by default)

`job_search/sources/linkedin_indeed.py` reads public, logged-out search-results
pages from LinkedIn and Indeed, since neither offers a consumer jobs-search API.
This is a real violation of both sites' Terms of Service — there's no technical
fix that makes it compliant, only smaller/less detectable. The module is scoped
deliberately:
- never logs in, never automates "Apply"
- runs at most once/day, no retries
- checks `robots.txt` before requesting and skips the source if disallowed
- uses an honest User-Agent, no proxy rotation or CAPTCHA solving — if blocked,
  it drops the source for that run rather than escalating

Its HTML selectors are based on each site's typical current markup and **are
the most brittle part of this project** — expect to need to update them if
either site changes its page structure. Enable at your own judgment via
`ENABLE_LINKEDIN_INDEED=true`.

## Known limitations
- Email detection (`job_search/email_detect.py`) is a plain regex over the
  posting's description text with a small denylist for obvious noise (image
  filenames, tracking domains, `noreply@`-style addresses). Most postings
  don't include a direct contact email at all — that's expected, not a bug;
  the Email button simply won't appear for those, and "Apply here" is the
  normal path.
- Greenhouse/Lever/Ashby only cover the specific companies you list — there's
  no general "search all companies" mode on these ATS platforms, so coverage is
  exactly as broad as the list you configure. Not every company uses one of
  these three (Workday and custom in-house ATS are common and aren't covered),
  and a guessed board token (e.g. assuming a company's slug matches their name)
  frequently doesn't exist — verify it against the company's actual careers
  page URL before adding it.
- No API here exposes a reliable structured "offers visa sponsorship" filter
  except Arbeitnow — everywhere else this is keyword matching, which is noisy
  in both directions. The Claude tailoring step does a second-pass sanity check
  and will flag a `warning` in the digest if a "match" looks like a false
  positive on closer reading, or if the posting wants meaningfully more
  experience than your resume shows.
- The region filter (`config.TARGET_REGION_KEYWORDS`) is the same kind of
  coarse keyword match as the visa/relocation filter — it checks the job's
  location/description text against an Australia + Europe keyword list, not a
  structured country field. It's most reliable for Adzuna (searched per-country
  via `ADZUNA_COUNTRIES`); for the other sources it's a text match and can miss
  or misfire at the edges.
- Most real job postings simply don't state visa/relocation terms in the ad
  copy even when the employer might actually consider it — expect this filter
  to surface real matches only occasionally, not every day.
- All listed API free tiers are each provider's current published policy, not a
  durable guarantee — each source fails independently so one going away doesn't
  break the others.
- Gmail SMTP connections have occasionally hit transient timeouts in testing on
  some networks; `notify.py` retries a failed send 3 times before giving up.
  Each batch of up to 10 jobs is its own email — only successfully-sent batches
  get marked seen, so a failed batch retries next run instead of being dropped.
- The cover letter PDFs (`job_search/pdf_export.py`) use `fpdf2`'s built-in
  Latin-1 core font, not a bundled Unicode font — smart quotes, em/en dashes,
  and similar punctuation are transliterated to plain ASCII before rendering so
  they don't break the PDF. Plain English text renders fine; anything genuinely
  non-Latin (e.g. non-English characters) would need a bundled TTF font instead.
