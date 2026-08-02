import json
import logging
import subprocess

from job_search import config
from job_search.prompt_templates import TAILOR_SYSTEM_PROMPT, TAILOR_USER_TEMPLATE

log = logging.getLogger(__name__)


def load_base_resume() -> dict:
    with open(config.BASE_RESUME_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def tailor_for_job(job: dict, base_resume: dict) -> dict | None:
    """Returns a dict with tailored_resume_summary/emphasized_skills/cover_letter,
    or None if tailoring failed (job is skipped for this run, not retried).

    Calls the Claude Code CLI in headless print mode (`claude -p`) instead of the
    metered Anthropic API, so this runs against the user's Claude subscription
    (Pro/Max) via CLAUDE_CODE_OAUTH_TOKEN rather than pay-per-token billing.
    ANTHROPIC_API_KEY must NOT be set in this process's environment — if present,
    Claude Code prefers it over the subscription token even in headless mode.
    """
    user_prompt = TAILOR_USER_TEMPLATE.format(
        base_resume_json=json.dumps(base_resume, indent=2),
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        url=job.get("url", ""),
        description=job.get("description", ""),
    )
    full_prompt = f"{TAILOR_SYSTEM_PROMPT}\n\n{user_prompt}"

    cmd = ["claude", "-p", full_prompt]
    if config.TAILOR_MODEL:
        cmd += ["--model", config.TAILOR_MODEL]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
            check=True,
        )
        text = result.stdout.strip()
        # The model sometimes wraps the JSON in a code fence and/or adds leading
        # or trailing prose despite instructions to output only JSON — extract
        # the outermost object rather than assuming the whole string is clean.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"no JSON object found in tailoring output: {text[:200]!r}")
        return json.loads(text[start:end + 1])
    except Exception:
        log.exception("tailor: failed for job %s at %s", job.get("title"), job.get("url"))
        return None
