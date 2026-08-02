"""OPTIONAL, off-by-default supplementary source. Reads public, logged-out
LinkedIn/Indeed job-search-results pages instead of using an API, because neither
site offers a consumer jobs-search API. This is a real ToS violation on both
sites, accepted knowingly at small, scoped risk — not eliminated.

Rules this module follows (see the project plan for the full rationale):
  - Never logs in. No session cookies, no credentials, no "Easy Apply" automation.
  - Called at most once per scheduled run. No retries on failure or blocking.
  - Checks robots.txt for the search path before requesting it; if disallowed,
    that source is skipped entirely for the run.
  - Ordinary, honest User-Agent. No proxy rotation, IP rotation, or CAPTCHA
    solving. If blocked (403, CAPTCHA page), stop and drop the source.
  - Only extracts title/company/location/url/snippet text, discards raw HTML.

Enable via ENABLE_LINKEDIN_INDEED=true. Off by default.
"""

import logging
import urllib.parse
import urllib.robotparser

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) job-search-agent personal script"

LINKEDIN_SEARCH_URL = "https://www.linkedin.com/jobs/search"
INDEED_SEARCH_URL = "https://www.indeed.com/jobs"


def _robots_allow(base_url: str, path: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, path)
    except Exception:
        log.exception("linkedin_indeed: robots.txt check failed, treating as disallowed")
        return False


def _fetch_linkedin(query: str) -> list[dict]:
    path = "/jobs/search"
    if not _robots_allow(LINKEDIN_SEARCH_URL, path):
        log.info("linkedin: robots.txt disallows this path, skipping source")
        return []

    try:
        resp = requests.get(
            LINKEDIN_SEARCH_URL,
            params={"keywords": query},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        if resp.status_code != 200:
            log.info("linkedin: non-200 response (%s), dropping source for this run", resp.status_code)
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        log.exception("linkedin: fetch failed, dropping source for this run")
        return []

    jobs = []
    for card in soup.select("div.base-card"):
        try:
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            location_el = card.select_one("span.job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")
            if not (title_el and link_el):
                continue
            jobs.append({
                "id": link_el["href"].split("?")[0],
                "source": "linkedin",
                "title": title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True) if company_el else "",
                "location": location_el.get_text(strip=True) if location_el else "",
                "url": link_el["href"].split("?")[0],
                "description": title_el.get_text(strip=True),
            })
        except Exception:
            log.exception("linkedin: skipped a malformed card")
    return jobs


def _fetch_indeed(query: str) -> list[dict]:
    path = "/jobs"
    if not _robots_allow(INDEED_SEARCH_URL, path):
        log.info("indeed: robots.txt disallows this path, skipping source")
        return []

    try:
        resp = requests.get(
            INDEED_SEARCH_URL,
            params={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        if resp.status_code != 200:
            log.info("indeed: non-200 response (%s), dropping source for this run", resp.status_code)
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        log.exception("indeed: fetch failed, dropping source for this run")
        return []

    jobs = []
    for card in soup.select("div.job_seen_beacon"):
        try:
            title_el = card.select_one("h2.jobTitle span")
            company_el = card.select_one("span[data-testid='company-name']")
            location_el = card.select_one("div[data-testid='text-location']")
            link_el = card.select_one("h2.jobTitle a")
            snippet_el = card.select_one("div.job-snippet")
            if not (title_el and link_el):
                continue
            href = link_el.get("href", "")
            url = href if href.startswith("http") else f"https://www.indeed.com{href}"
            jobs.append({
                "id": url,
                "source": "indeed",
                "title": title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True) if company_el else "",
                "location": location_el.get_text(strip=True) if location_el else "",
                "url": url,
                "description": snippet_el.get_text(strip=True) if snippet_el else title_el.get_text(strip=True),
            })
        except Exception:
            log.exception("indeed: skipped a malformed card")
    return jobs


def fetch(query: str) -> list[dict]:
    """Combined LinkedIn + Indeed cautious check. Each site is independent —
    one being blocked/changed doesn't affect the other."""
    return _fetch_linkedin(query) + _fetch_indeed(query)
