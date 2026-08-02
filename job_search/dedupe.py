import json
import os
from datetime import datetime, timezone

from job_search import config


def _job_key(job: dict) -> str:
    return f"{job.get('source', '')}:{job.get('id', '')}"


def load_seen() -> dict:
    if not os.path.exists(config.SEEN_JOBS_PATH):
        return {}
    with open(config.SEEN_JOBS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_seen(seen: dict) -> None:
    with open(config.SEEN_JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, sort_keys=True)


def filter_unseen(jobs: list[dict], seen: dict) -> list[dict]:
    return [job for job in jobs if _job_key(job) not in seen]


def mark_seen(jobs: list[dict], seen: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for job in jobs:
        seen[_job_key(job)] = {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "url": job.get("url", ""),
            "first_seen": now,
        }
