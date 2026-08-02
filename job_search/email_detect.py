import re

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Coarse denylist for obvious non-hiring-contact matches — image asset references,
# tracking pixels, and generic mailbox-provider noise that occasionally shows up
# embedded in raw HTML job descriptions. Not exhaustive, same spirit as the rest
# of this project's keyword filters: a heuristic, not a guarantee.
_IGNORED_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
_IGNORED_DOMAINS = ("sentry.io", "schema.org", "wixpress.com", "example.com", "w3.org")
_IGNORED_LOCAL_PARTS = ("noreply", "no-reply", "notifications", "donotreply")


def find_contact_email(text: str) -> str | None:
    """Returns the first plausible hiring-contact email address found in the
    text, or None. Best-effort — job descriptions rarely include a direct
    email at all, since most postings expect an application via the job
    board's own form instead."""
    if not text:
        return None

    for match in EMAIL_PATTERN.finditer(text):
        candidate = match.group(0)
        lowered = candidate.lower()
        if lowered.endswith(_IGNORED_SUFFIXES):
            continue
        if any(domain in lowered for domain in _IGNORED_DOMAINS):
            continue
        local_part = lowered.split("@", 1)[0]
        if local_part in _IGNORED_LOCAL_PARTS:
            continue
        return candidate
    return None
