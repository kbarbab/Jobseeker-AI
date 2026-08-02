"""Creates real Gmail drafts (with PDF attachments) via the Gmail API — separate
from job_search/notify.py, which only sends the digest email over SMTP with an
app password. App passwords can't create drafts; that needs proper OAuth.

One-time setup (see README): create a Google Cloud project, enable the Gmail
API, create an OAuth Desktop-app client, download it as gmail_oauth_client_secret.json
in the repo root. The first draft-creation call opens a browser for one-time
consent and caches a refresh token in gmail_oauth_token.json — both files are
gitignored, never commit them.

Scope is deliberately the narrowest that does the job: gmail.compose allows
creating/sending drafts, not reading the inbox.
"""

import base64
import logging
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
CLIENT_SECRET_PATH = os.path.join(_REPO_ROOT, "gmail_oauth_client_secret.json")
TOKEN_PATH = os.path.join(_REPO_ROOT, "gmail_oauth_token.json")


def _get_credentials() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not os.path.exists(CLIENT_SECRET_PATH):
            raise FileNotFoundError(
                f"{CLIENT_SECRET_PATH} not found — download your OAuth client "
                "secret from Google Cloud Console and save it there (see README)."
            )
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    return creds


def create_draft(to_email: str, subject: str, body_text: str, attachment_paths: list[str]) -> str | None:
    """Creates a Gmail draft with the given attachments. Returns the draft ID,
    or None on failure. Never sends — the user reviews and sends it themselves
    from their own Gmail Drafts folder."""
    try:
        creds = _get_credentials()
        service = build("gmail", "v1", credentials=creds)

        message = MIMEMultipart()
        message["to"] = to_email
        message["subject"] = subject
        message.attach(MIMEText(body_text))

        for path in attachment_paths:
            if not path or not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=os.path.basename(path))
            message.attach(part)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return draft.get("id")
    except Exception:
        log.exception("gmail_draft: failed to create draft for %s", to_email)
        return None
