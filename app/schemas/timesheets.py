from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TimesheetProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    client_name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    is_billable: bool = True
    is_active: bool = True


class TimesheetProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    client_name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    is_billable: Optional[bool] = None
    is_active: Optional[bool] = None


class TimesheetProjectResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    client_name: Optional[str] = None
    description: Optional[str] = None
    is_billable: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TimesheetEntryCreate(BaseModel):
    employee_id: UUID
    project_id: UUID
    entry_date: date
    hours: float = Field(..., gt=0, le=24)
    description: Optional[str] = None


class TimesheetEntryUpdate(BaseModel):
    project_id: Optional[UUID] = None
    entry_date: Optional[date] = None
    hours: Optional[float] = Field(default=None, gt=0, le=24)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(draft|submitted|approved|rejected)$")


class TimesheetEntryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    project_id: UUID
    entry_date: date
    hours: float
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TimesheetDashboardStats(BaseModel):
    total_hours_this_week: float
    pending_approval: int
    active_projects: int
    submitted_this_month: int
