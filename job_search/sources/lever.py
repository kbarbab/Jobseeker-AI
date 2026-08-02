"""Lever Postings API — public, no key required, meant for embedding a
company's own listings on their careers page. Docs: https://github.com/lever/postings-api

Per-company, like Greenhouse — fetches each configured company's full board.
"""

import logging

import requests

from job_search import config

log = logging.getLogger(__name__)

URL = "https://api.lever.co/v0/postings/{company}"


def _fetch_company(company: str) -> list[dict]:
    try:
        resp = requests.get(URL.format(company=company), params={"mode": "json"}, timeout=20)
        if resp.status_code == 404:
            log.warning("lever: unknown company board '%s', skipping", company)
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("lever: fetch failed for company %s", company)
        return []

    jobs = []
    for item in data if isinstance(data, list) else []:
        try:
            categories = item.get("categories") or {}
            description = f"{item.get('descriptionPlain', '')} {item.get('additionalPlain', '')}"
            jobs.append({
                "id": f"{company}-{item['id']}",
                "source": "lever",
                "title": item.get("text", ""),
                "company": company,
                "location": categories.get("location", ""),
                "url": item.get("hostedUrl", ""),
                "description": description,
            })
        except Exception:
            log.exception("lever: skipped a malformed result (company %s)", company)
    return jobs


def fetch(query: str) -> list[dict]:
    jobs = []
    for company in config.LEVER_COMPANIES:
        jobs.extend(_fetch_company(company))
    return jobs
