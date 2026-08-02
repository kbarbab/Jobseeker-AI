"""RemoteOK JSON API. Free, no key, but unofficial/unpublished rate limits —
treat as best-effort and call at most once per scheduled run. Remote-only listings.
"""

import logging

import requests

log = logging.getLogger(__name__)

URL = "https://remoteok.com/api"


def fetch(query: str) -> list[dict]:
    try:
        resp = requests.get(
            URL,
            headers={"User-Agent": "job-search-agent/1.0 (personal use)"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("remoteok: fetch failed")
        return []

    jobs = []
    # First element is a legal/metadata notice, not a job listing.
    for item in data[1:] if isinstance(data, list) else []:
        try:
            jobs.append({
                "id": str(item.get("id", item.get("slug", ""))),
                "source": "remoteok",
                "title": item.get("position", ""),
                "company": item.get("company", ""),
                "location": item.get("location", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            })
        except Exception:
            log.exception("remoteok: skipped a malformed result")
    return jobs
