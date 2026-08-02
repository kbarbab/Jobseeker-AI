"""Greenhouse Job Board API — public, no key required, meant for embedding a
company's own listings on their careers page. Docs: https://developers.greenhouse.io/job-board.html

Per-company: fetches every configured company's full board and lets the shared
keyword filter (job_search/filters.py) narrow it down — there's no free-text
search parameter, this isn't a general job search API.
"""

import logging

import requests

from job_search import config

log = logging.getLogger(__name__)

URL = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"


def _fetch_company(company: str) -> list[dict]:
    try:
        resp = requests.get(URL.format(company=company), params={"content": "true"}, timeout=20)
        if resp.status_code == 404:
            log.warning("greenhouse: unknown company board '%s', skipping", company)
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("greenhouse: fetch failed for company %s", company)
        return []

    jobs = []
    for item in data.get("jobs", []):
        try:
            jobs.append({
                "id": f"{company}-{item['id']}",
                "source": "greenhouse",
                "title": item.get("title", ""),
                "company": item.get("company_name", company),
                "location": (item.get("location") or {}).get("name", ""),
                "url": item.get("absolute_url", ""),
                "description": item.get("content", ""),
            })
        except Exception:
            log.exception("greenhouse: skipped a malformed result (company %s)", company)
    return jobs


def fetch(query: str) -> list[dict]:
    jobs = []
    for company in config.GREENHOUSE_COMPANIES:
        jobs.extend(_fetch_company(company))
    return jobs
