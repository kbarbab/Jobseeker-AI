"""Adzuna Jobs API. Free tier: ~1,000 calls/month. Requires ADZUNA_APP_ID + ADZUNA_APP_KEY
(register at https://developer.adzuna.com/). Docs: https://developer.adzuna.com/docs/search

Adzuna's search endpoint is per-country, so covering multiple target countries
(config.ADZUNA_COUNTRIES) means one API call per country — each counts against
the shared monthly quota.
"""

import logging

import requests

from job_search import config

log = logging.getLogger(__name__)

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


def _fetch_country(query: str, country: str) -> list[dict]:
    try:
        resp = requests.get(
            BASE_URL.format(country=country),
            params={
                "app_id": config.ADZUNA_APP_ID,
                "app_key": config.ADZUNA_APP_KEY,
                "what": query,
                "results_per_page": 50,
                "content-type": "application/json",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("adzuna: fetch failed for country %s", country)
        return []

    jobs = []
    for item in data.get("results", []):
        try:
            jobs.append({
                "id": f"{country}-{item['id']}",
                "source": "adzuna",
                "title": item.get("title", ""),
                "company": (item.get("company") or {}).get("display_name", ""),
                "location": (item.get("location") or {}).get("display_name", ""),
                "url": item.get("redirect_url", ""),
                "description": item.get("description", ""),
            })
        except Exception:
            log.exception("adzuna: skipped a malformed result (country %s)", country)
    return jobs


def fetch(query: str) -> list[dict]:
    if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
        log.info("adzuna: skipped, no API key configured")
        return []

    jobs = []
    for country in config.ADZUNA_COUNTRIES:
        jobs.extend(_fetch_country(query, country))
    return jobs
