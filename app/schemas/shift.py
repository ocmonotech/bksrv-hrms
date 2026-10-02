from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditFields(BaseModel):
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShiftCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    start_time: time
    end_time: time
    break_minutes: int = Field(default=60, ge=0)
    grace_minutes: int = Field(default=10, ge=0)
    is_night_shift: bool = False
    is_active: bool = True


class ShiftUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    break_minutes: Optional[int] = Field(default=None, ge=0)
    grace_minutes: Optional[int] = Field(default=None, ge=0)
    is_night_shift: Optional[bool] = None
    is_active: Optional[bool] = None


class ShiftResponse(AuditFields):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    start_time: time
    end_time: time
    break_minutes: int
    grace_minutes: int
    is_night_shift: bool
    is_active: bool


class RosterCreate(BaseModel):
    employee_id: UUID
    shift_id: UUID
    roster_date: date
    branch_id: Optional[UUID] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True


class RosterUpdate(BaseModel):
    shift_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class RosterResponse(AuditFields):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    shift_id: UUID
    roster_date: date
    branch_id: Optional[UUID] = None
    notes: Optional[str] = None
    is_active: bool


class ShiftSwapCreate(BaseModel):
    requester_id: UUID
    target_employee_id: Optional[UUID] = None
    roster_date: date
    current_shift_id: UUID
    requested_shift_id: UUID
    reason: Optional[str] = None


class ShiftSwapUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=30)
    reason: Optional[str] = None


class ShiftSwapResponse(AuditFields):
    id: UUID
    tenant_id: UUID
    requester_id: UUID
    target_employee_id: Optional[UUID] = None
    roster_date: date
    current_shift_id: UUID
    requested_shift_id: UUID
    reason: Optional[str] = None
    status: str
    approver_id: Optional[UUID] = None
