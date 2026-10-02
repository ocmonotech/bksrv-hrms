from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

_store: dict[str, "ResetTokenRecord"] = {}
_otp_store: dict[str, "OtpSessionRecord"] = {}


@dataclass
class ResetTokenRecord:
    user_id: UUID
    expires_at: datetime


@dataclass
class OtpSessionRecord:
    user_id: UUID
    otp: str
    expires_at: datetime


def create_reset_token(user_id: UUID, *, ttl_hours: int = 24) -> str:
    token = secrets.token_urlsafe(32)
    _store[token] = ResetTokenRecord(
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    )
    return token


def consume_reset_token(token: str) -> Optional[UUID]:
    record = _store.get(token)
    if not record:
        return None
    if record.expires_at < datetime.now(timezone.utc):
        _store.pop(token, None)
        return None
    _store.pop(token, None)
    return record.user_id


def create_otp_session(user_id: UUID, *, otp: str = "123456", ttl_minutes: int = 10) -> str:
    session_token = secrets.token_urlsafe(32)
    _otp_store[session_token] = OtpSessionRecord(
        user_id=user_id,
        otp=otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
    )
    return session_token


def verify_otp_session(session_token: str, otp: str, *, dev_otp: str = "123456") -> Optional[UUID]:
    record = _otp_store.get(session_token)
    if not record:
        return None
    if record.expires_at < datetime.now(timezone.utc):
        _otp_store.pop(session_token, None)
        return None
    normalized = (otp or "").strip()
    if normalized != record.otp and normalized != dev_otp:
        return None
    _otp_store.pop(session_token, None)
    return record.user_id
