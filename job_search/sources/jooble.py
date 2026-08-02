"""Jooble API. Free API key via a short signup form at https://jooble.org/api/about.
Docs: https://jooble.org/api/about
"""

import logging

import requests

from job_search import config

log = logging.getLogger(__name__)


def fetch(query: str) -> list[dict]:
    if not config.JOOBLE_API_KEY:
        log.info("jooble: skipped, no API key configured")
        return []

    try:
        resp = requests.post(
            f"https://jooble.org/api/{config.JOOBLE_API_KEY}",
            json={"keywords": query},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("jooble: fetch failed")
        return []

    jobs = []
    for i, item in enumerate(data.get("jobs", [])):
        try:
            link = item.get("link", "")
            jobs.append({
                "id": link or f"jooble-{i}",
                "source": "jooble",
                "title": item.get("title", ""),
                "company": item.get("company", ""),
                "location": item.get("location", ""),
                "url": link,
                "description": item.get("snippet", ""),
            })
        except Exception:
            log.exception("jooble: skipped a malformed result")
    return jobs
