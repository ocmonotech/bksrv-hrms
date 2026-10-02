from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.exceptions import ValidationError


def validate_password(password: str) -> str:
    """Enforce password policy when enabled (production by default)."""
    settings = get_settings()
    if not settings.password_policy_enabled:
        if len(password) < settings.password_min_length:
            raise ValidationError(f"Password must be at least {settings.password_min_length} characters")
        return password

    if len(password) < settings.password_min_length:
        raise ValidationError(f"Password must be at least {settings.password_min_length} characters")

    if settings.password_require_uppercase and not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter")

    if settings.password_require_lowercase and not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter")

    if settings.password_require_digit and not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one digit")

    if settings.password_require_special and not re.search(r"[^A-Za-z0-9]", password):
        raise ValidationError("Password must contain at least one special character")

    return password
