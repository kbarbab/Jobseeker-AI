import os
import re

from job_search import config


def _safe_filename(job: dict) -> str:
    raw = f"{job.get('source', '')}_{job.get('id', '')}"
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)
    return f"{safe}.md"


def draft_path(job: dict) -> str:
    return os.path.join(config.DRAFTS_DIR, _safe_filename(job))


def save_draft(job: dict, tailored: dict) -> str | None:
    """Writes the full tailored resume summary + cover letter to a Markdown file
    so it's available later (e.g. when actually applying), not just summarized
    in the digest email. Returns the file path, or None if there's nothing to save."""
    if not tailored:
        return None

    os.makedirs(config.DRAFTS_DIR, exist_ok=True)
    path = draft_path(job)

    warning_section = f"\n**Warning:** {tailored['warning']}\n" if tailored.get("warning") else ""
    skills = ", ".join(tailored.get("emphasized_skills", []))

    content = f"""# {job.get('title', '')} — {job.get('company', '')}

- **Location:** {job.get('location', '')}
- **Source:** {job.get('source', '')}
- **Apply here:** {job.get('url', '')}
{warning_section}
## Tailored resume summary

{tailored.get('tailored_resume_summary', '')}

**Emphasize skills:** {skills}

## Cover letter

{tailored.get('cover_letter', '')}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
