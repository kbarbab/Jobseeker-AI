"""Ashby Job Board API — public, no key required, meant for embedding a
company's own listings on their careers page.
Docs: https://developers.ashbyhq.com/reference/jobpostingapi-jobboard

Per-company, like Greenhouse/Lever — fetches each configured company's full board.
"""

import logging

import requests

from job_search import config

log = logging.getLogger(__name__)

URL = "https://api.ashbyhq.com/posting-api/job-board/{company}"


def _fetch_company(company: str) -> list[dict]:
    try:
        resp = requests.get(URL.format(company=company), timeout=20)
        if resp.status_code == 404:
            log.warning("ashby: unknown company board '%s', skipping", company)
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("ashby: fetch failed for company %s", company)
        return []

    jobs = []
    for item in data.get("jobs", []):
        try:
            jobs.append({
                "id": f"{company}-{item['id']}",
                "source": "ashby",
                "title": item.get("title", ""),
                "company": company,
                "location": item.get("location", ""),
                "url": item.get("jobUrl", ""),
                "description": item.get("descriptionPlain") or item.get("descriptionHtml", ""),
            })
        except Exception:
            log.exception("ashby: skipped a malformed result (company %s)", company)
    return jobs


def fetch(query: str) -> list[dict]:
    jobs = []
    for company in config.ASHBY_COMPANIES:
        jobs.extend(_fetch_company(company))
    return jobs
