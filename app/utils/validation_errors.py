from __future__ import annotations

from typing import Any


def format_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Convert Pydantic/FastAPI validation errors into a stable, client-friendly shape."""
    formatted: list[dict[str, str]] = []
    for error in errors:
        loc = error.get("loc", ())
        field_parts = [str(part) for part in loc if part not in ("body", "query", "path")]
        field = ".".join(field_parts) if field_parts else "request"
        formatted.append(
            {
                "field": field,
                "message": str(error.get("msg", "Invalid value")),
                "type": str(error.get("type", "value_error")),
            }
        )
    return formatted
