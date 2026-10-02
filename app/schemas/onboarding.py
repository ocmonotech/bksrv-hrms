from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OnboardingChecklistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    department_id: Optional[UUID] = None
    is_default: bool = False
    is_active: bool = True


class OnboardingChecklistUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    department_id: Optional[UUID] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class OnboardingChecklistResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    department_id: Optional[UUID] = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OnboardingTaskCreate(BaseModel):
    checklist_id: UUID
    employee_id: UUID
    task_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    sequence: int = Field(default=0, ge=0)


class OnboardingTaskUpdate(BaseModel):
    task_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    sequence: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = None


class OnboardingTaskResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    checklist_id: UUID
    employee_id: UUID
    task_name: str
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None
    sequence: int
    status: str
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NewJoinerDocumentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    document_type: str
    file_name: str
    file_path: str
    status: str
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentVerifyRequest(BaseModel):
    status: str = Field(..., pattern="^(verified|rejected)$")
    rejection_reason: Optional[str] = None


class ProbationReviewCreate(BaseModel):
    employee_id: UUID
    review_date: date
    reviewer_id: Optional[UUID] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    outcome: str = Field(default="pending", max_length=30)
    feedback: Optional[str] = None
    extension_end_date: Optional[date] = None


class ProbationReviewUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    outcome: Optional[str] = None
    feedback: Optional[str] = None
    status: Optional[str] = None
    extension_end_date: Optional[date] = None


class ProbationApproveRequest(BaseModel):
    notes: Optional[str] = None


class ProbationReviewResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    review_date: date
    reviewer_id: Optional[UUID] = None
    rating: Optional[int] = None
    outcome: str
    feedback: Optional[str] = None
    status: str
    approver_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    extension_end_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}
