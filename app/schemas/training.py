from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TrainingCourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    category: str = Field(default="general", max_length=50)
    description: Optional[str] = None
    duration_hours: int = Field(default=1, ge=1, le=500)
    delivery_mode: str = Field(default="online", pattern="^(online|classroom|hybrid|self_paced)$")
    is_mandatory: bool = False
    is_active: bool = True


class TrainingCourseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    duration_hours: Optional[int] = Field(default=None, ge=1, le=500)
    delivery_mode: Optional[str] = Field(default=None, pattern="^(online|classroom|hybrid|self_paced)$")
    is_mandatory: Optional[bool] = None
    is_active: Optional[bool] = None


class TrainingCourseResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    title: str
    code: str
    category: str
    description: Optional[str] = None
    duration_hours: int
    delivery_mode: str
    is_mandatory: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingEnrollmentCreate(BaseModel):
    course_id: UUID
    employee_id: UUID
    due_date: Optional[date] = None


class TrainingEnrollmentUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(assigned|in_progress|completed|overdue)$")
    progress_pct: Optional[int] = Field(default=None, ge=0, le=100)
    due_date: Optional[date] = None


class TrainingEnrollmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    course_id: UUID
    employee_id: UUID
    status: str
    progress_pct: int
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingDashboardStats(BaseModel):
    total_courses: int
    active_enrollments: int
    completion_rate_pct: float
    overdue_count: int
