from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ModuleActions(BaseModel):
    view: bool = False
    create: bool = False
    edit: bool = False
    delete: bool = False
    approve: bool = False
    export: bool = False
    manage: bool = False


class PermissionMatrixItem(BaseModel):
    module: str
    actions: ModuleActions


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    is_system: bool = False

    @field_validator("name", "slug")
    @classmethod
    def strip_value(cls, v: str) -> str:
        return v.strip()


class RoleResponse(BaseModel):
    id: UUID
    tenant_id: Optional[UUID] = None
    slug: str
    name: str
    description: Optional[str] = None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RoleWithPermissionsResponse(RoleResponse):
    permissions: list[PermissionMatrixItem]


class RolePermissionsUpdate(BaseModel):
    permissions: list[PermissionMatrixItem] = Field(..., min_length=1)


class PermissionCatalogItem(BaseModel):
    module: str
    actions: list[str]


class PermissionCatalogResponse(BaseModel):
    permissions: list[PermissionCatalogItem]
    total: int
