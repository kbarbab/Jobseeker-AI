import logging
import os
import sys
import traceback

from job_search import config, dashboard_data, dedupe, drafts, email_detect, filters, notify, pdf_export, tailor
from job_search.sources import API_SOURCES, linkedin_indeed

# Job titles/descriptions routinely contain non-ASCII characters (accents, umlauts,
# emoji). Windows consoles default to a legacy codepage (e.g. cp1252) that raises
# UnicodeEncodeError on those — reconfigure so logging never crashes a run over this.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")

# Sources whose fetch() actually restricts results server-side by the query
# string (Adzuna's `what`, Remotive's `search`, Jooble's `keywords`). Everyone
# else (Greenhouse/Lever/Ashby company boards, RemoteOK, The Muse) ignores the
# query entirely and fetches everything, so calling them twice would just
# double the load for identical results — only these three get queried once
# per search term (config.JOB_QUERY and config.AI_JOB_QUERY).
QUERY_FILTERED_SOURCES = {"adzuna", "remotive", "jooble"}


def _dedupe_within_run(jobs: list[dict]) -> list[dict]:
    """Querying a source twice (once per search term) can return the same job
    from both calls — collapse those before filtering, or a job could pass
    dedupe.filter_unseen as two separate "new" entries and get tailored/emailed
    twice in one run."""
    seen_keys = set()
    unique = []
    for job in jobs:
        key = (job.get("source"), job.get("id"))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(job)
    return unique


def fetch_all_jobs() -> list[dict]:
    all_jobs = []
    for name, fetch_fn in API_SOURCES.items():
        try:
            if name in QUERY_FILTERED_SOURCES:
                jobs = fetch_fn(config.JOB_QUERY) + fetch_fn(config.AI_JOB_QUERY)
            else:
                jobs = fetch_fn(config.JOB_QUERY)
        except Exception:
            log.exception("source %s raised unexpectedly, treating as empty", name)
            jobs = []
        log.info("source %s: %d results", name, len(jobs))
        all_jobs.extend(jobs)

    if config.ENABLE_LINKEDIN_INDEED:
        try:
            jobs = linkedin_indeed.fetch(config.JOB_QUERY) + linkedin_indeed.fetch(config.AI_JOB_QUERY)
        except Exception:
            log.exception("linkedin_indeed raised unexpectedly, treating as empty")
            jobs = []
        log.info("source linkedin_indeed: %d results", len(jobs))
        all_jobs.extend(jobs)
    else:
        log.info("source linkedin_indeed: disabled (ENABLE_LINKEDIN_INDEED=false)")

    return _dedupe_within_run(all_jobs)


def check_config() -> list[str]:
    """Returns human-readable descriptions of missing *required* configuration.
    Without this check, a run with no secrets configured at all still exits
    0 ("success" in GitHub Actions) after silently skipping every credentialed
    step — misleading, since nothing useful actually happened. This doesn't
    catch wrong-but-present values (e.g. an invalid app password still only
    surfaces as a runtime SMTP error), only the "never configured" case."""
    problems = []
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
        problems.append(
            "GMAIL_ADDRESS / GMAIL_APP_PASSWORD are not set — the digest email "
            "can never be sent without these (see README step 3)."
        )
    running_in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    if running_in_ci and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") and not os.environ.get("ANTHROPIC_API_KEY"):
        problems.append(
            "Running in GitHub Actions with neither CLAUDE_CODE_OAUTH_TOKEN nor "
            "ANTHROPIC_API_KEY set — tailoring will fail for every job (see "
            "README step 2b: `claude setup-token`)."
        )
    return problems


def run() -> None:
    problems = check_config()
    if problems:
        for problem in problems:
            log.error("CONFIG PROBLEM: %s", problem)
        raise RuntimeError("Missing required configuration: " + " | ".join(problems))

    all_jobs = fetch_all_jobs()
    log.info("total fetched: %d", len(all_jobs))

    matched = filters.filter_jobs(all_jobs)
    log.info("matched .NET + visa/relocation filter: %d", len(matched))

    seen = dedupe.load_seen()
    new_jobs = dedupe.filter_unseen(matched, seen)
    log.info("new (unseen) jobs: %d", len(new_jobs))

    if not new_jobs:
        log.info("nothing new, exiting")
        return

    base_resume = tailor.load_base_resume()
    entries = []
    for job in new_jobs:
        tailored = tailor.tailor_for_job(job, base_resume)
        draft_path = drafts.save_draft(job, tailored)
        resume_pdf_path = pdf_export.generate_resume_pdf(job, tailored, base_resume) if tailored else None
        cover_letter_pdf_path = pdf_export.generate_cover_letter_pdf(job, tailored, base_resume) if tailored else None
        contact_email = email_detect.find_contact_email(job.get("description", ""))
        entries.append({
            "job": job,
            "tailored": tailored,
            "draft_path": draft_path,
            "pdf_path": cover_letter_pdf_path,  # notify.py attaches this to the digest email
            "resume_pdf_path": resume_pdf_path,
            "cover_letter_pdf_path": cover_letter_pdf_path,
            "contact_email": contact_email,
        })

    sent_entries = notify.send_digest(entries)
    if not sent_entries:
        log.warning("no digest email sent — not marking any jobs seen, will retry next run")
        return

    sent_jobs = [e["job"] for e in sent_entries]
    dedupe.mark_seen(sent_jobs, seen)
    dedupe.save_seen(seen)

    for entry in sent_entries:
        dashboard_data.record_job(
            entry["job"], entry["tailored"], entry["draft_path"],
            entry["resume_pdf_path"], entry["cover_letter_pdf_path"], entry["contact_email"],
        )

    log.info("done: %d/%d new jobs recorded (rest will retry next run)", len(sent_jobs), len(new_jobs))


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        log.exception("run failed")
        notify.send_failure_alert(f"{exc}\n\n{traceback.format_exc()}")
        sys.exit(1)
