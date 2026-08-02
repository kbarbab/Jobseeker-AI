"""Remotive API. Free, no key required, remote-only listings. Remotive's own
guidance asks for at most ~4 requests/day — this is called once per scheduled run,
so stay well within that as long as the job isn't re-run manually many times a day.
Docs: https://remotive.com/api-documentation
"""

import logging

import requests

log = logging.getLogger(__name__)

URL = "https://remotive.com/api/remote-jobs"


def fetch(query: str) -> list[dict]:
    try:
        resp = requests.get(URL, params={"search": query}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("remotive: fetch failed")
        return []

    jobs = []
    for item in data.get("jobs", []):
        try:
            jobs.append({
                "id": str(item["id"]),
                "source": "remotive",
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("candidate_required_location", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            })
        except Exception:
            log.exception("remotive: skipped a malformed result")
    return jobs
