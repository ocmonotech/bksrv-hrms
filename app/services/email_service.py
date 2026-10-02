from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> bool:
    """Send email via SMTP when configured; otherwise log to console in development."""
    if not to:
        return False

    if not settings.smtp_host:
        logger.info(
            "Email (dev console): to=%s subject=%s body=%s",
            to,
            subject,
            body[:500],
        )
        return True

    message = EmailMessage()
    message["From"] = settings.smtp_from or settings.smtp_user or "noreply@ocmono.com"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
        logger.info("Email sent to %s subject=%s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        if settings.is_production:
            raise
        logger.info("Falling back to console log for email to=%s subject=%s", to, subject)
        return False
