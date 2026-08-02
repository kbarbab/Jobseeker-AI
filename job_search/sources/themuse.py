"""The Muse public jobs API. Free without a key (500 req/hr) or with a free key
(3,600 req/hr). No free-text query param — fetch the Software Engineering category
and let the shared keyword filter (job_search/filters.py) narrow it to .NET roles.
Docs: https://www.themuse.com/developers/api/v2
"""

import logging

import requests

from job_search import config

log = logging.getLogger(__name__)

URL = "https://www.themuse.com/api/public/jobs"


def fetch(query: str) -> list[dict]:
    try:
        params = {"category": "Software Engineering", "page": 0}
        if config.THEMUSE_API_KEY:
            params["api_key"] = config.THEMUSE_API_KEY
        resp = requests.get(URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("themuse: fetch failed")
        return []

    jobs = []
    for item in data.get("results", []):
        try:
            locations = ", ".join(
                loc.get("name", "") for loc in item.get("locations", [])
            )
            jobs.append({
                "id": str(item["id"]),
                "source": "themuse",
                "title": item.get("name", ""),
                "company": (item.get("company") or {}).get("name", ""),
                "location": locations,
                "url": (item.get("refs") or {}).get("landing_page", ""),
                "description": item.get("contents", ""),
            })
        except Exception:
            log.exception("themuse: skipped a malformed result")
    return jobs
