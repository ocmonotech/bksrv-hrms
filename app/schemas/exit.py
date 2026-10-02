from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ResignationCreate(BaseModel):
    employee_id: UUID
    resignation_date: date
    last_working_date: date
    reason: str = Field(..., min_length=3)


class ResignationUpdate(BaseModel):
    last_working_date: Optional[date] = None
    reason: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=30)


class ResignationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    resignation_date: date
    last_working_date: date
    reason: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExitClearanceUpdate(BaseModel):
    checklist: Optional[List[dict[str, Any]]] = None
    status: Optional[str] = Field(default=None, max_length=30)


class ExitClearanceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    resignation_id: UUID
    checklist: List[dict[str, Any]]
    status: str
    cleared_at: Optional[datetime] = None
    created_at: datetime


class ExitInterviewCreate(BaseModel):
    resignation_id: UUID
    employee_id: UUID
    conducted_by: Optional[UUID] = None
    feedback: str = Field(..., min_length=3)
    interview_date: date
    status: str = Field(default="scheduled", max_length=30)


class ExitInterviewUpdate(BaseModel):
    conducted_by: Optional[UUID] = None
    feedback: Optional[str] = None
    interview_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)


class ExitInterviewResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    resignation_id: UUID
    employee_id: UUID
    conducted_by: Optional[UUID] = None
    feedback: str
    interview_date: date
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
