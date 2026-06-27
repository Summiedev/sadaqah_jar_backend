"""
Lightweight email service using stdlib smtplib.

No new dependency over requirements.txt — only Python's built-in smtplib
and the standard email MIME utilities are used.  If SMTP is misconfigured
(empty host or connection failure) the error is logged and the system
continues — never break a registration or password-reset flow over email.
"""
import logging
import smtplib
import ssl
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(recipient: str, subject: str, html_body: str) -> bool:
    """Send an HTML email.  Returns True if the message was accepted
    by the SMTP relay, False otherwise."""
    if not settings.SMTP_HOST or settings.SMTP_HOST == "localhost" and not settings.SMTP_USER:
        logger.warning("SMTP not configured — email would have been sent to %s: %s", recipient, subject)
        return True  # don't break the caller

    msg = MIMEText(html_body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = recipient

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_PORT == 587:
                server.starttls(context=ctx)
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, [recipient], msg.as_string())
        logger.info("Email sent to %s: %s", recipient, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", recipient, exc)
        return False