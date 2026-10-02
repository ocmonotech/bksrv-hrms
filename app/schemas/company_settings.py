from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WeeklyOffUpdate(BaseModel):
    days: list[str] = Field(..., min_length=1)


class WeeklyOffResponse(BaseModel):
    days: list[str]


class ManagerAssignmentItem(BaseModel):
    department_id: UUID
    department_name: str
    department_code: str
    manager_employee_id: Optional[UUID] = None
    manager_name: Optional[str] = None
    direct_reports_count: int = 0


class ManagerAssignmentsUpdate(BaseModel):
    assignments: list[ManagerAssignmentItem]


class ManagerAssignmentsResponse(BaseModel):
    assignments: list[ManagerAssignmentItem]
    source: str


class CareerPageUpdate(BaseModel):
    enabled: Optional[bool] = None
    headline: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    banner_url: Optional[str] = Field(default=None, max_length=512)
    show_openings: Optional[bool] = None


class CareerPageResponse(BaseModel):
    enabled: bool = True
    headline: str
    description: str
    banner_url: Optional[str] = None
    show_openings: bool = True
