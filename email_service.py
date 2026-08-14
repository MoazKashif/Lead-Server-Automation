"""Central SMTP email service for the Lead Server.

Sends transactional emails directly from the FastAPI backend via Zoho SMTP,
replacing the previous n8n workflow (Backend -> n8n webhook -> n8n -> Email).
Uses only the Python standard library (smtplib + email) with no extra deps.
"""

import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional


class EmailError(Exception):
    """Base class for all email service errors."""


class EmailConfigError(EmailError):
    """Raised when SMTP is not configured."""


class EmailDeliveryError(EmailError):
    """Raised when an email cannot be delivered via SMTP."""


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _is_truthy(value: str) -> bool:
    return value.lower() in ("1", "true", "yes", "on")


def smtp_config() -> dict:
    """Return a normalized dict of SMTP settings from environment variables."""
    username = _env("SMTP_USERNAME")
    password = _env("SMTP_PASSWORD")
    return {
        "host": _env("SMTP_HOST"),
        "port": int(_env("SMTP_PORT", "587") or "587"),
        "username": username,
        "password": password,
        "from_email": _env("SMTP_FROM_EMAIL") or username,
        "from_name": _env("SMTP_FROM_NAME", "Fantom AI"),
        "use_tls": _is_truthy(_env("SMTP_USE_TLS", "true") or "true"),
        "timeout": int(_env("SMTP_TIMEOUT", "20") or "20"),
    }


def is_smtp_configured() -> bool:
    """True only when all settings required to send email are present."""
    cfg = smtp_config()
    return bool(cfg["host"] and cfg["username"] and cfg["password"] and cfg["from_email"])


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


def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> bool:
    """Send an email via SMTP.

    Supports HTML + plain-text fallback, UTF-8, TLS/SSL, timeout, optional
    Reply-To, and proper connection cleanup.

    Returns True on success. Raises EmailConfigError if SMTP is not
    configured and EmailDeliveryError if delivery fails.
    """
    cfg = smtp_config()
    if not is_smtp_configured():
        raise EmailConfigError(
            "SMTP is not configured. Set SMTP_HOST, SMTP_USERNAME, "
            "SMTP_PASSWORD, and SMTP_FROM_EMAIL."
        )

    from_header = formataddr((cfg["from_name"], cfg["from_email"]))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_header
    msg["To"] = to
    if reply_to:
        msg["Reply-To"] = reply_to
    msg["X-Mailer"] = "FantomAI Lead Server"

    if text_body is None:
        text_body = html_to_text(html_body)
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if cfg["use_tls"]:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=cfg["timeout"]) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(cfg["username"], cfg["password"])
                server.sendmail(cfg["from_email"], [to], msg.as_string())
        else:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=cfg["timeout"]) as server:
                server.login(cfg["username"], cfg["password"])
                server.sendmail(cfg["from_email"], [to], msg.as_string())
    except smtplib.SMTPAuthenticationError as e:
        raise EmailDeliveryError("SMTP authentication failed.") from e
    except Exception as e:
        raise EmailDeliveryError(f"SMTP delivery failed: {e}") from e
    return True