from __future__ import annotations

import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_sms(*, to: str, body: str) -> bool:
    """Send SMS via Twilio when configured; otherwise log to console."""
    settings = get_settings()
    if not to:
        return False

    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.info("SMS (dev console): to=%s body=%s", to, body[:300])
        return True

    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        from_number = settings.twilio_sms_from
        if not from_number:
            raise ValueError("TWILIO_SMS_FROM is not configured")
        client.messages.create(to=to, from_=from_number, body=body)
        logger.info("SMS sent to %s", to)
        return True
    except Exception:
        logger.exception("Failed to send SMS to %s", to)
        if settings.is_production:
            raise
        logger.info("SMS fallback console: to=%s body=%s", to, body[:300])
        return False


def send_whatsapp(*, to: str, body: str) -> bool:
    """Send WhatsApp message via Twilio when configured; otherwise log to console."""
    settings = get_settings()
    if not to:
        return False

    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.info("WhatsApp (dev console): to=%s body=%s", to, body[:300])
        return True

    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        from_number = settings.twilio_whatsapp_from
        if not from_number:
            raise ValueError("TWILIO_WHATSAPP_FROM is not configured")
        recipient = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        sender = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        client.messages.create(to=recipient, from_=sender, body=body)
        logger.info("WhatsApp sent to %s", to)
        return True
    except Exception:
        logger.exception("Failed to send WhatsApp to %s", to)
        if settings.is_production:
            raise
        logger.info("WhatsApp fallback console: to=%s body=%s", to, body[:300])
        return False
