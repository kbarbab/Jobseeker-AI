"""
Each source module exposes a single function: fetch(query: str) -> list[dict].

Every dict is normalized to:
    {
        "id": str,           # stable identifier, unique within this source
        "source": str,       # short source name, e.g. "adzuna"
        "title": str,
        "company": str,
        "location": str,
        "url": str,
        "description": str,  # full text used for keyword filtering + tailoring
    }

Sources must not raise on recoverable failures (network errors, bad responses) —
catch and return [] so one source's outage never breaks the whole run. Let the
orchestrator (main.py) log which sources returned nothing.
"""

from job_search.sources import (
    adzuna, arbeitnow, remotive, remoteok, themuse, jooble,
    greenhouse, lever, ashby,
)

# Registry of always-on, legitimate API sources.
API_SOURCES = {
    "adzuna": adzuna.fetch,
    "arbeitnow": arbeitnow.fetch,
    "remotive": remotive.fetch,
    "remoteok": remoteok.fetch,
    "themuse": themuse.fetch,
    "jooble": jooble.fetch,
    # Direct-company ATS boards — no-op until GREENHOUSE_COMPANIES /
    # LEVER_COMPANIES / ASHBY_COMPANIES lists companies to fetch (see config.py).
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
}
