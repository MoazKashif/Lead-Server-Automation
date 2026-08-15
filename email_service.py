"""Central email service for the Lead Server.

Sends transactional emails directly from the FastAPI backend via the
Resend HTTP API (HTTPS), replacing the previous Resend SMTP delivery which
timed out on Render (outbound SMTP connections blocked / slow). Uses only
the Python standard library (urllib.request + json) with no extra
dependencies, so no network ports other than 443 are required.

Resend API configuration:
  RESEND_API_KEY=<your Resend API key>  (starts with re_)
  RESEND_FROM_EMAIL=team@fantomai.site  (must be on a verified domain)
  RESEND_FROM_NAME=Fantom AI
"""

import json
import os
import re
import urllib.error
import urllib.request
from email.utils import formataddr
from typing import Optional

RESEND_API_URL = "https://api.resend.com/emails"


class EmailError(Exception):
    """Base class for all email service errors."""


class EmailConfigError(EmailError):
    """Raised when Resend is not configured."""


class EmailDeliveryError(EmailError):
    """Raised when an email cannot be delivered via the Resend API."""


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def email_config() -> dict:
    """Return a normalized dict of Resend API settings from environment variables."""
    return {
        "api_key": _env("RESEND_API_KEY"),
        "from_email": _env("RESEND_FROM_EMAIL"),
        "from_name": _env("RESEND_FROM_NAME", "Fantom AI"),
        "timeout": int(_env("RESEND_TIMEOUT", "20") or "20"),
    }


def is_email_configured() -> bool:
    """True only when all settings required to send email are present."""
    cfg = email_config()
    return bool(cfg["api_key"] and cfg["from_email"])


def html_to_text(html: str) -> str:
    """Crude HTML -> plain-text conversion for the text/plain fallback."""
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"</(?:div|h1|h2|h3|h4|li)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _post_resend(api_key: str, payload: dict, timeout: int) -> None:
    """POST the payload to the Resend Emails API and raise on non-2xx."""
    request = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "FantomAI-LeadServer/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()


def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> bool:
    """Send an email via the Resend HTTP API.

    Supports HTML + plain-text fallback, UTF-8, optional Reply-To, and a
    connection timeout. Returns True on a successful Resend API response.
    Raises EmailConfigError if Resend is not configured and
    EmailDeliveryError if the API call or network delivery fails.
    """
    cfg = email_config()
    if not is_email_configured():
        raise EmailConfigError(
            "Resend is not configured. Set RESEND_API_KEY and RESEND_FROM_EMAIL."
        )

    if text_body is None:
        text_body = html_to_text(html_body)

    payload = {
        "from": formataddr((cfg["from_name"], cfg["from_email"])),
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    try:
        _post_resend(cfg["api_key"], payload, timeout=cfg["timeout"])
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("message", "")
        except Exception:
            pass
        raise EmailDeliveryError(
            f"Resend API returned HTTP {e.code}: {detail or e.reason}"
        ) from e
    except Exception as e:
        raise EmailDeliveryError(f"Resend delivery failed: {e}") from e
    return True
