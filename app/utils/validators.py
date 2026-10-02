from __future__ import annotations

import re
from typing import Optional

from app.constants.india import INDIA_DEFAULTS, INDIAN_STATE_SET

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
AADHAAR_PATTERN = re.compile(r"^[2-9]\d{11}$")
MOBILE_PATTERN = re.compile(r"^(\+91)?[6-9]\d{9}$")
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
PINCODE_PATTERN = re.compile(r"^[1-9][0-9]{5}$")
IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
UAN_PATTERN = re.compile(r"^\d{12}$")


def normalize_pan(value: str) -> str:
    return value.strip().upper()


def validate_pan(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    normalized = normalize_pan(value)
    if not PAN_PATTERN.match(normalized):
        raise ValueError("Invalid PAN format. Expected format: ABCDE1234F")
    return normalized


def validate_aadhaar(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    cleaned = re.sub(r"\s|-", "", value.strip())
    if not AADHAAR_PATTERN.match(cleaned):
        raise ValueError("Invalid Aadhaar number. Must be 12 digits and not start with 0 or 1")
    return cleaned


def validate_mobile(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    cleaned = re.sub(r"[\s-]", "", value.strip())
    if not MOBILE_PATTERN.match(cleaned):
        raise ValueError("Invalid mobile number. Use 10-digit Indian mobile or +91 prefix")
    if cleaned.startswith("+91"):
        return cleaned
    return cleaned


def validate_gstin(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    normalized = value.strip().upper()
    if not GSTIN_PATTERN.match(normalized):
        raise ValueError("Invalid GSTIN. Expected 15-character Indian GSTIN format")
    return normalized


def validate_pincode(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    cleaned = value.strip()
    if not PINCODE_PATTERN.match(cleaned):
        raise ValueError("Invalid pincode. Must be a 6-digit Indian pincode")
    return cleaned


def validate_ifsc(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    normalized = value.strip().upper()
    if not IFSC_PATTERN.match(normalized):
        raise ValueError("Invalid IFSC code. Expected format: HDFC0001234")
    return normalized


def validate_indian_state(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    cleaned = value.strip()
    if cleaned not in INDIAN_STATE_SET:
        raise ValueError("Invalid state / UT. Select a valid Indian state or union territory")
    return cleaned


def validate_uan(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    cleaned = value.strip()
    if not UAN_PATTERN.match(cleaned):
        raise ValueError("Invalid UAN. Must be 12 digits")
    return cleaned


def validate_india_country(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    if value.strip() != INDIA_DEFAULTS["country"]:
        raise ValueError("Only India is supported as country")
    return INDIA_DEFAULTS["country"]


def validate_inr_currency(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    if value.strip().upper() != INDIA_DEFAULTS["currency"]:
        raise ValueError("Only INR currency is supported")
    return INDIA_DEFAULTS["currency"]


def validate_india_timezone(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    if value.strip() != INDIA_DEFAULTS["timezone"]:
        raise ValueError("Only Asia/Kolkata (IST) timezone is supported")
    return INDIA_DEFAULTS["timezone"]


def validate_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or len(email) < 5:
        raise ValueError("Invalid email address")
    return email
