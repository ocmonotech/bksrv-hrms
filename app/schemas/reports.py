from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportColumn(BaseModel):
    key: str
    label: str
    type: str = "string"


class ReportFilters(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    branch_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    employee_id: Optional[UUID] = None


class ReportResponse(BaseModel):
    report_type: str
    generated_at: datetime
    filters: ReportFilters
    columns: list[ReportColumn]
    summary: dict[str, Any]
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReportQueryParams(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    branch_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    employee_id: Optional[UUID] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class CustomReportCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    modules: list[str] = Field(default_factory=list)
    columns: list[dict[str, Any]] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)


class CustomReportResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    modules: list[str]
    columns: list[dict[str, Any]]
    filters: dict[str, Any]
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportsDashboardStats(BaseModel):
    total_custom_reports: int
    report_types_available: list[str]
    recent_exports: int
    headcount_total: int
    pending_regularizations: int


class ReportExportRequest(BaseModel):
    report_type: str = Field(..., min_length=1, max_length=50)
    custom_report_id: Optional[UUID] = None
    filters: ReportFilters = Field(default_factory=ReportFilters)
    format: str = Field(default="csv", pattern="^(csv)$")


class ReportExportResponse(BaseModel):
    filename: str
    content_type: str
    content_base64: Optional[str] = None
    download_path: Optional[str] = None
    row_count: int


class LiveMetricPoint(BaseModel):
    label: str
    value: float
    change_pct: Optional[float] = None


class LiveAnalyticsResponse(BaseModel):
    generated_at: datetime
    headcount: int
    present_today: int
    on_leave_today: int
    pending_approvals: int
    open_tickets: int
    training_completion_pct: float
    engagement_score: float
    wellbeing_index: float
    trends: list[LiveMetricPoint]
