"""
Email service backed by Resend via direct HTTP API.

Uses httpx (already in requirements.txt), no extra dependency needed.
"""

from __future__ import annotations

import logging
import os

import httpx

from app.core.config import settings
from app.emails.templates import password_reset_email_html, verification_email_html

logger = logging.getLogger(__name__)


def _resend_api_key() -> str | None:
    key = getattr(settings, "RESEND_API_KEY", "") or os.getenv("RESEND_API_KEY", "")
    return key if key else None


def _sender() -> str:
    from_email = settings.FROM_EMAIL.strip()
    if "<" in from_email and ">" in from_email:
        return from_email
    return f"Mizan <{from_email}>"


def send_email(recipient: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via Resend. Returns True on success, False otherwise."""
    api_key = _resend_api_key()
    if not api_key:
        logger.warning(
            "RESEND_API_KEY not configured, email would have been sent to %s: %s",
            recipient,
            subject,
        )
        return True

    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": _sender(),
                "to": [recipient],
                "subject": subject,
                "html": html_body,
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Email sent to %s: %s", recipient, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", recipient, exc)
        return False


def send_verification_email(recipient: str, token: str, user_name: str | None = None) -> bool:
    subject = "Your Mizan verification code"
    html_body = verification_email_html(token, user_name)
    return send_email(recipient, subject, html_body)


def send_password_reset_email(recipient: str, token: str) -> bool:
    subject = "Reset your Mizan password"
    html_body = password_reset_email_html(token)
    return send_email(recipient, subject, html_body)
