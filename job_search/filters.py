from job_search import config


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in keywords)


def is_dotnet_role(job: dict) -> bool:
    # Title-only, not title+description: AI/ML companies in particular repeat
    # generic "we build AI agents" boilerplate across every posting regardless
    # of function (sales, marketing, finance), so scanning the full description
    # for role-category keywords produces exactly the kind of false positive
    # already fixed once for region matching (see is_target_region below) — a
    # job whose actual function is unrelated matching on incidental company
    # copy. The title is a much stronger signal of what the role actually is.
    return _contains_any(job.get("title", ""), config.DOTNET_KEYWORDS)


def is_agentic_ai_role(job: dict) -> bool:
    return _contains_any(job.get("title", ""), config.AGENTIC_AI_KEYWORDS)


def offers_visa_or_relocation(job: dict) -> bool:
    # Arbeitnow gives us a real structured signal — trust it directly when present.
    if job.get("source") == "arbeitnow" and "visa_sponsorship" in job:
        if job["visa_sponsorship"]:
            return True
        # Fall through to keyword check too — some Arbeitnow listings mention
        # relocation support without the visa_sponsorship flag being set.

    text = f"{job.get('title', '')} {job.get('description', '')}"
    if not _contains_any(text, config.VISA_RELOCATION_KEYWORDS):
        return False
    # Plain substring matching can't tell "we offer visa sponsorship" apart from
    # "not eligible for visa sponsorship" — both contain "visa sponsorship". Catch
    # the common negated phrasings explicitly rather than treating a match as
    # automatically positive.
    if _contains_any(text, config.VISA_NEGATION_PHRASES):
        return False
    return True


def is_target_region(job: dict) -> bool:
    # Prefer the structured location field — company "About us" boilerplate in
    # the description routinely lists every office the company has worldwide
    # (e.g. "hubs in Berlin, Denver, London, New York..."), which would make an
    # otherwise US-only posting match on "Berlin"/"London" if the whole
    # description were scanned. Only fall back to the description when there's
    # no location field to go on at all.
    location = job.get("location", "")
    if location:
        return _contains_any(location, config.TARGET_REGION_KEYWORDS)
    return _contains_any(job.get("description", ""), config.TARGET_REGION_KEYWORDS)


def matches(job: dict) -> bool:
    role_matches = is_dotnet_role(job) or is_agentic_ai_role(job)
    return role_matches and offers_visa_or_relocation(job) and is_target_region(job)


def filter_jobs(jobs: list[dict]) -> list[dict]:
    return [job for job in jobs if matches(job)]
