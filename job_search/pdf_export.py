import datetime
import logging
import os
import re

from fpdf import FPDF

from job_search import config

log = logging.getLogger(__name__)

# fpdf2's core fonts (Helvetica/Arial) are Latin-1 only. Rather than bundling a
# TTF font file in the repo just to support smart quotes/em-dashes, transliterate
# the handful of Unicode punctuation marks Claude's output actually produces.
_UNICODE_TO_ASCII = {
    "—": "--", "–": "-",       # em dash, en dash
    "‘": "'", "’": "'",         # smart single quotes
    "“": '"', "”": '"',         # smart double quotes
    "…": "...",                       # ellipsis
    " ": " ",                         # non-breaking space
}


def _sanitize(text: str) -> str:
    for unicode_char, ascii_equiv in _UNICODE_TO_ASCII.items():
        text = text.replace(unicode_char, ascii_equiv)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _safe_filename(job: dict, suffix: str) -> str:
    raw = f"{job.get('source', '')}_{job.get('id', '')}_{suffix}"
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)
    return f"{safe}.pdf"


def cover_letter_pdf_path(job: dict) -> str:
    return os.path.join(config.DRAFTS_DIR, _safe_filename(job, "cover_letter"))


def resume_pdf_path(job: dict) -> str:
    return os.path.join(config.DRAFTS_DIR, _safe_filename(job, "resume"))


def generate_cover_letter_pdf(job: dict, tailored: dict, base_resume: dict) -> str | None:
    """Renders the tailored cover letter as a simple, print-ready PDF. Returns
    the file path, or None if there's no cover letter to render."""
    cover_letter = tailored.get("cover_letter") if tailored else None
    if not cover_letter:
        return None

    os.makedirs(config.DRAFTS_DIR, exist_ok=True)
    path = cover_letter_pdf_path(job)

    name = base_resume.get("name", "")
    email = base_resume.get("email", "")
    phone = base_resume.get("phone", "")
    location = base_resume.get("location", "")

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, _sanitize(name), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    contact_line = " | ".join(x for x in [email, phone, location] if x)
    pdf.cell(0, 6, _sanitize(contact_line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, datetime.date.today().strftime("%B %d, %Y"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    re_line = f"Re: {job.get('title', '')} at {job.get('company', '')}"
    pdf.multi_cell(0, 6, _sanitize(re_line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, _sanitize(cover_letter), new_x="LMARGIN", new_y="NEXT")

    pdf.output(path)
    return path


def generate_resume_pdf(job: dict, tailored: dict, base_resume: dict) -> str | None:
    """Renders a full resume PDF: header, the tailored summary + emphasized
    skills for this posting, then the complete factual work history from
    base_resume.json unchanged (tailoring only reorders/emphasizes — it never
    invents or omits experience, so the full history always appears here)."""
    if not tailored:
        return None

    os.makedirs(config.DRAFTS_DIR, exist_ok=True)
    path = resume_pdf_path(job)

    name = base_resume.get("name", "")
    email = base_resume.get("email", "")
    phone = base_resume.get("phone", "")
    location = base_resume.get("location", "")
    links = base_resume.get("links", {})

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 9, _sanitize(name), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    contact_line = " | ".join(x for x in [email, phone, location, *links.values()] if x)
    pdf.multi_cell(0, 5, _sanitize(contact_line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    summary = tailored.get("tailored_resume_summary") or base_resume.get("summary", "")
    pdf.multi_cell(0, 5, _sanitize(summary), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    skills = tailored.get("emphasized_skills") or base_resume.get("skills", [])
    if skills:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Skills", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _sanitize(", ".join(skills)), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    experience = base_resume.get("experience", [])
    if experience:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Experience", new_x="LMARGIN", new_y="NEXT")
        for entry in experience:
            pdf.set_font("Helvetica", "B", 10)
            title_line = f"{entry.get('title', '')} — {entry.get('company', '')}"
            pdf.multi_cell(0, 5, _sanitize(title_line), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "I", 9)
            meta_line = f"{entry.get('location', '')} | {entry.get('start_date', '')} - {entry.get('end_date', '')}"
            pdf.multi_cell(0, 5, _sanitize(meta_line), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for bullet in entry.get("bullets", []):
                pdf.multi_cell(0, 5, _sanitize(f"- {bullet}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

    education = base_resume.get("education", [])
    if education:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Education", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for entry in education:
            line = f"{entry.get('institution', '')} - {entry.get('degree', '')} ({entry.get('start_date', '')}-{entry.get('end_date', '')})"
            pdf.multi_cell(0, 5, _sanitize(line), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    certifications = base_resume.get("certifications", [])
    if certifications:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Certifications", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for cert in certifications:
            pdf.multi_cell(0, 5, _sanitize(f"- {cert}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    projects = base_resume.get("projects", [])
    if projects:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Projects", new_x="LMARGIN", new_y="NEXT")
        for entry in projects:
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 5, _sanitize(entry.get("name", "")), new_x="LMARGIN", new_y="NEXT")
            technologies = entry.get("technologies", [])
            if technologies:
                pdf.set_font("Helvetica", "I", 9)
                pdf.multi_cell(0, 5, _sanitize(", ".join(technologies)), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for bullet in entry.get("bullets", []):
                pdf.multi_cell(0, 5, _sanitize(f"- {bullet}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

    pdf.output(path)
    return path
