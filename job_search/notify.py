import logging
import smtplib
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from job_search import config

log = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SEND_RETRIES = 3
SEND_RETRY_DELAY_SECONDS = 5

# Cap on how many jobs go in a single email — keeps individual emails short and
# avoids very large attachment counts. Overflow is sent as additional emails.
MAX_JOBS_PER_EMAIL = 10


def _send(subject: str, html_body: str, attachments: list[tuple[str, bytes]] | None = None) -> None:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.NOTIFY_TO

    body = MIMEMultipart("alternative")
    body.attach(MIMEText(html_body, "html"))
    msg.attach(body)

    for filename, data in attachments or []:
        part = MIMEApplication(data, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    # Gmail SMTP connections have been observed to intermittently time out
    # (transient network/routing blips, not a config problem — a bare retry
    # typically succeeds). This matters most for the unattended daily cron run,
    # where there's no one around to notice a failed send and retry manually.
    last_exc = None
    for attempt in range(1, SEND_RETRIES + 1):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
                server.send_message(msg)
            return
        except Exception as exc:
            last_exc = exc
            log.warning("notify: send attempt %d/%d failed: %s", attempt, SEND_RETRIES, exc)
            if attempt < SEND_RETRIES:
                time.sleep(SEND_RETRY_DELAY_SECONDS)
    raise last_exc


def _render_batch(entries: list[dict], part: int, total_parts: int) -> tuple[str, str, list[tuple[str, bytes]]]:
    sections = []
    attachments = []

    for entry in entries:
        job = entry["job"]
        tailored = entry["tailored"]
        draft_path = entry.get("draft_path")
        pdf_path = entry.get("pdf_path")

        warning_html = ""
        if tailored and tailored.get("warning"):
            warning_html = f"<p><b>⚠ Warning:</b> {tailored['warning']}</p>"

        if tailored is None:
            body_html = "<p><i>Tailoring failed for this job — review the posting manually.</i></p>"
        else:
            skills = ", ".join(tailored.get("emphasized_skills", []))
            draft_html = f"<p><b>Full draft saved to:</b> <code>{draft_path}</code></p>" if draft_path else ""
            pdf_note = ""
            if pdf_path:
                try:
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    attachment_name = f"cover_letter_{job.get('company', 'job')}.pdf".replace(" ", "_")
                    attachments.append((attachment_name, pdf_bytes))
                    pdf_note = f"<p><b>Cover letter PDF attached:</b> {attachment_name}</p>"
                except OSError:
                    log.exception("notify: could not read PDF at %s", pdf_path)

            body_html = f"""
                {warning_html}
                {draft_html}
                {pdf_note}
                <p><b>Tailored summary:</b> {tailored.get('tailored_resume_summary', '')}</p>
                <p><b>Emphasize skills:</b> {skills}</p>
            """

        sections.append(f"""
            <h3>{job.get('title', '')} — {job.get('company', '')}</h3>
            <p>{job.get('location', '')} · source: {job.get('source', '')}</p>
            <p><b>Apply here:</b> <a href="{job.get('url', '')}">{job.get('url', '')}</a></p>
            {body_html}
            <hr/>
        """)

    part_label = f" ({part}/{total_parts})" if total_parts > 1 else ""
    subject = f"Job search digest{part_label}: {len(entries)} new .NET relocation role(s)"
    html_body = "<html><body>" + "".join(sections) + "</body></html>"
    return subject, html_body, attachments


def send_digest(entries: list[dict]) -> list[dict]:
    """entries: list of {job, tailored, draft_path, pdf_path} dicts. Sent in
    batches of MAX_JOBS_PER_EMAIL jobs per email — extra jobs beyond that spill
    into additional emails rather than one unbounded message.

    Returns the subset of entries whose email actually sent. The caller must
    only mark those jobs as "seen" — a transient SMTP failure on a later batch
    shouldn't cause an earlier, successfully-sent batch to be silently dropped,
    nor should a failed batch be marked seen (dedup means it's never retried)."""
    if not entries:
        log.info("notify: no new matching jobs, skipping email")
        return []

    batches = [entries[i:i + MAX_JOBS_PER_EMAIL] for i in range(0, len(entries), MAX_JOBS_PER_EMAIL)]
    total_parts = len(batches)
    sent_entries = []

    for part, batch in enumerate(batches, start=1):
        subject, html_body, attachments = _render_batch(batch, part, total_parts)
        try:
            _send(subject, html_body, attachments)
            sent_entries.extend(batch)
        except Exception:
            log.exception("notify: failed to send digest email part %d/%d", part, total_parts)

    return sent_entries


def send_failure_alert(error: str) -> None:
    try:
        _send("Job search agent: run failed", f"<pre>{error}</pre>")
    except Exception:
        log.exception("notify: failed to send failure alert (this is the last resort, giving up)")
