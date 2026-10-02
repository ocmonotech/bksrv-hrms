from __future__ import annotations

import logging
from typing import Iterable, Optional

from app.services.email_service import send_email
from app.services.sms_service import send_sms, send_whatsapp

logger = logging.getLogger(__name__)


def notify_channels(
    *,
    email: Optional[str] = None,
    mobile: Optional[str] = None,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    channels: Optional[Iterable[str]] = None,
) -> dict[str, bool]:
    """
    Deliver a notification across requested channels.
    channels: email, sms, whatsapp, in_app (in_app is logged only).
    """
    selected = {c.lower().strip() for c in (channels or ["email"])}
    results: dict[str, bool] = {}

    if "email" in selected and email:
        results["email"] = send_email(to=email, subject=subject, body=body, html_body=html_body)
    if "sms" in selected and mobile:
        results["sms"] = send_sms(to=mobile, body=f"{subject}\n\n{body}"[:1600])
    if "whatsapp" in selected and mobile:
        results["whatsapp"] = send_whatsapp(to=mobile, body=f"*{subject}*\n{body}"[:1600])
    if "in_app" in selected:
        logger.info("In-app notification: subject=%s", subject)
        results["in_app"] = True

    return results
