from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., min_length=1, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)
    purchase_date: Optional[date] = None
    status: str = Field(default="available", max_length=30)
    is_active: bool = True


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)
    purchase_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)
    is_active: Optional[bool] = None


class AssetResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    category: str
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    status: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetAssignmentCreate(BaseModel):
    asset_id: UUID
    employee_id: UUID
    assigned_date: date
    return_date: Optional[date] = None
    notes: Optional[str] = None


class AssetAssignmentUpdate(BaseModel):
    return_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)
    notes: Optional[str] = None


class AssetAssignmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    asset_id: UUID
    employee_id: UUID
    assigned_date: date
    return_date: Optional[date] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
