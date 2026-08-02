"""Arbeitnow Job Board API. Free, no API key required. EU-weighted listings.
Docs: https://www.arbeitnow.com/api/job-board-api
Has a genuine visa_sponsorship boolean field on each listing (rare among these
sources) — we filter on it client-side rather than trusting a query param, since
that's the more reliably documented behavior.
"""

import logging

import requests

log = logging.getLogger(__name__)

URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch(query: str) -> list[dict]:
    try:
        resp = requests.get(URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("arbeitnow: fetch failed")
        return []

    jobs = []
    for item in data.get("data", []):
        try:
            jobs.append({
                "id": str(item.get("slug", item.get("url", ""))),
                "source": "arbeitnow",
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("location", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "visa_sponsorship": bool(item.get("visa_sponsorship", False)),
            })
        except Exception:
            log.exception("arbeitnow: skipped a malformed result")
    return jobs
