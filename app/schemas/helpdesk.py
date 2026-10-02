from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TicketCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    default_sla_hours: Optional[int] = Field(default=None, ge=1, le=720)
    is_active: bool = True


class TicketCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    default_sla_hours: Optional[int] = Field(default=None, ge=1, le=720)
    is_active: Optional[bool] = None


class TicketCategoryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    default_sla_hours: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketCreate(BaseModel):
    category_id: Optional[UUID] = None
    subject: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10)
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    employee_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None


class TicketResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    category_id: Optional[UUID] = None
    ticket_number: str
    subject: str
    description: str
    priority: str
    status: str
    requester_id: UUID
    employee_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketReplyCreate(BaseModel):
    message: str = Field(..., min_length=1)
    is_internal: bool = False


class TicketReplyResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    author_id: UUID
    message: str
    is_internal: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketAssignRequest(BaseModel):
    assigned_to: UUID
    notes: Optional[str] = Field(default=None, max_length=500)


class TicketCloseRequest(BaseModel):
    resolution_note: Optional[str] = Field(default=None, max_length=1000)
