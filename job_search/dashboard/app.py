"""Minimalistic local dashboard for reviewing job matches.

Run with: python -m job_search.dashboard.app
Then open http://127.0.0.1:5000 in your browser.

The "Email" button only appears for jobs where a contact email was detected in
the posting itself (most postings don't have one — they expect an application
via the job board's own form, shown as a plain "Apply here" link instead). It
creates a real Gmail draft (resume + cover letter PDFs attached) via the Gmail
API — see job_search/gmail_draft.py — and never sends anything itself.
"""

import os

from flask import Flask, redirect, render_template, send_file, url_for

from job_search import dashboard_data, gmail_draft

app = Flask(__name__)


@app.route("/")
def index():
    records = dashboard_data.load_all()
    jobs = sorted(records.items(), key=lambda kv: kv[1].get("first_seen", ""), reverse=True)
    return render_template("index.html", jobs=jobs)


@app.route("/draft/<path:job_key>", methods=["POST"])
def create_draft(job_key):
    records = dashboard_data.load_all()
    record = records.get(job_key)
    if not record or not record.get("contact_email"):
        return redirect(url_for("index"))

    job = record["job"]
    tailored = record.get("tailored") or {}
    subject = f"Application for {job.get('title', '')} at {job.get('company', '')}"
    body_text = tailored.get("cover_letter", "Please see attached resume and cover letter.")
    attachments = [p for p in (record.get("resume_pdf_path"), record.get("cover_letter_pdf_path")) if p]

    draft_id = gmail_draft.create_draft(record["contact_email"], subject, body_text, attachments)
    if draft_id:
        dashboard_data.mark_email_draft_created(job_key)

    return redirect(url_for("index"))


@app.route("/file/<path:job_key>/<kind>")
def download_file(job_key, kind):
    records = dashboard_data.load_all()
    record = records.get(job_key)
    if not record:
        return "Not found", 404
    path = record.get(f"{kind}_path")
    if not path or not os.path.exists(path):
        return "Not found", 404
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
