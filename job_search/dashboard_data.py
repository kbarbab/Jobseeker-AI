import json
import os
from datetime import datetime, timezone

INDEX_PATH = os.path.join(os.path.dirname(__file__), "dashboard_data.json")


def _job_key(job: dict) -> str:
    return f"{job.get('source', '')}:{job.get('id', '')}"


def load_all() -> dict:
    if not os.path.exists(INDEX_PATH):
        return {}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_all(records: dict) -> None:
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, sort_keys=True)


def record_job(
    job: dict,
    tailored: dict | None,
    draft_path: str | None,
    resume_pdf_path: str | None,
    cover_letter_pdf_path: str | None,
    contact_email: str | None,
) -> None:
    """Persists everything the dashboard needs to show and act on a job, in
    one place — separate from job_search/seen_jobs.json (which only tracks
    dedup, not full content) and job_search/drafts/*.md (human-readable, but
    not structured for a UI to render)."""
    records = load_all()
    key = _job_key(job)
    records[key] = {
        "job": job,
        "tailored": tailored,
        "draft_path": draft_path,
        "resume_pdf_path": resume_pdf_path,
        "cover_letter_pdf_path": cover_letter_pdf_path,
        "contact_email": contact_email,
        "first_seen": datetime.now(timezone.utc).isoformat(),
        "email_draft_created_at": None,
    }
    save_all(records)


def mark_email_draft_created(job_key: str) -> None:
    records = load_all()
    if job_key in records:
        records[job_key]["email_draft_created_at"] = datetime.now(timezone.utc).isoformat()
        save_all(records)
