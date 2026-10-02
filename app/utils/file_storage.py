from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


def employee_document_relative_path(
    tenant_id: str,
    employee_id: str,
    document_type: str,
    original_filename: str,
) -> str:
    """uploads/{tenant_id}/employees/{employee_id}/documents/{document_type}/{uuid}_{filename}"""
    safe_type = re.sub(r"[^a-zA-Z0-9_-]", "_", document_type.lower())
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(original_filename).name)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    return f"uploads/{tenant_id}/employees/{employee_id}/documents/{safe_type}/{unique_name}"


def candidate_document_relative_path(
    tenant_id: str,
    candidate_id: str,
    document_type: str,
    original_filename: str,
) -> str:
    safe_type = re.sub(r"[^a-zA-Z0-9_-]", "_", document_type.lower())
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(original_filename).name)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    return f"uploads/{tenant_id}/recruitment/candidates/{candidate_id}/{safe_type}/{unique_name}"


def onboarding_document_relative_path(
    tenant_id: str,
    employee_id: str,
    document_type: str,
    original_filename: str,
) -> str:
    safe_type = re.sub(r"[^a-zA-Z0-9_-]", "_", document_type.lower())
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(original_filename).name)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    return f"uploads/{tenant_id}/onboarding/{employee_id}/{safe_type}/{unique_name}"


def employee_library_relative_path(
    tenant_id: str,
    employee_id: str,
    document_title: str,
    original_filename: str,
) -> str:
    safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", document_title.lower())[:50]
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(original_filename).name)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    return f"uploads/{tenant_id}/documents/employees/{employee_id}/{safe_title}/{unique_name}"


def company_document_relative_path(
    tenant_id: str,
    document_title: str,
    original_filename: str,
) -> str:
    safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", document_title.lower())[:50]
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(original_filename).name)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    return f"uploads/{tenant_id}/documents/company/{safe_title}/{unique_name}"


def save_upload_file(relative_path: str, content: bytes) -> str:
    base = Path(settings.upload_root)
    full_path = base / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    return relative_path


def get_absolute_path(relative_path: str) -> Path:
    return Path(settings.upload_root) / relative_path
