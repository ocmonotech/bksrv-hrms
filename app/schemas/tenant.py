from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    plan: Optional[str] = Field(default="standard", max_length=50)

    @field_validator("name", "slug")
    @classmethod
    def strip_value(cls, v: str) -> str:
        return v.strip()


class TenantResponse(ORMModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    plan: str
    created_at: datetime
    updated_at: datetime
