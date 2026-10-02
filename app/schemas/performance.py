from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    employee_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: date
    end_date: date
    weight: Decimal = Field(default=Decimal("100"), ge=0, le=100)
    manager_id: Optional[UUID] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    weight: Optional[Decimal] = Field(default=None, ge=0, le=100)
    progress: Optional[Decimal] = Field(default=None, ge=0, le=100)
    status: Optional[str] = None


class GoalResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    title: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    weight: Decimal
    progress: Decimal
    status: str
    manager_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class KeyResultItem(BaseModel):
    title: str
    target: Optional[str] = None
    progress: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class OKRCreate(BaseModel):
    employee_id: UUID
    objective: str = Field(..., min_length=1, max_length=500)
    key_results: List[KeyResultItem] = Field(default_factory=list)
    quarter: int = Field(..., ge=1, le=4)
    year: int = Field(..., ge=2000, le=2100)


class OKRUpdate(BaseModel):
    objective: Optional[str] = Field(default=None, min_length=1, max_length=500)
    key_results: Optional[List[KeyResultItem]] = None
    progress: Optional[Decimal] = Field(default=None, ge=0, le=100)
    status: Optional[str] = None


class OKRResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    objective: str
    key_results: List[KeyResultItem]
    quarter: int
    year: int
    progress: Decimal
    status: str
    created_at: datetime


class ReviewCycleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    cycle_type: str = Field(default="annual", max_length=30)
    start_date: date
    end_date: date
    is_active: bool = True


class ReviewCycleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    cycle_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class ReviewCycleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    cycle_type: str
    start_date: date
    end_date: date
    status: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    review_type: str = Field(..., pattern="^(self|manager|360)$")
    review_cycle_id: UUID
    employee_id: UUID
    manager_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    relationship: Optional[str] = Field(default="peer", max_length=50)
    responses: Optional[dict[str, Any]] = None
    rating: Optional[Decimal] = Field(default=None, ge=0, le=5)
    feedback: Optional[str] = None


class ReviewUpdate(BaseModel):
    responses: Optional[dict[str, Any]] = None
    rating: Optional[Decimal] = Field(default=None, ge=0, le=5)
    feedback: Optional[str] = None
    status: Optional[str] = None
    hr_override: Optional[bool] = None


class ReviewResponse(BaseModel):
    id: UUID
    review_type: str
    review_cycle_id: UUID
    employee_id: UUID
    rating: Optional[Decimal] = None
    feedback: Optional[str] = None
    status: str
    submitted_at: Optional[datetime] = None
    created_at: datetime


class AppraisalCreate(BaseModel):
    review_cycle_id: UUID
    employee_id: UUID
    final_rating: Optional[Decimal] = Field(default=None, ge=0, le=5)
    increment_percent: Optional[Decimal] = Field(default=None, ge=0)
    promotion_recommended: bool = False
    notes: Optional[str] = None


class AppraisalUpdate(BaseModel):
    final_rating: Optional[Decimal] = Field(default=None, ge=0, le=5)
    increment_percent: Optional[Decimal] = Field(default=None, ge=0)
    promotion_recommended: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AppraisalApproveRequest(BaseModel):
    notes: Optional[str] = None


class AppraisalResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    review_cycle_id: UUID
    employee_id: UUID
    final_rating: Optional[Decimal] = None
    increment_percent: Optional[Decimal] = None
    promotion_recommended: bool
    status: str
    approver_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
