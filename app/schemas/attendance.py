from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PunchRequest(BaseModel):
    employee_id: UUID
    punch_type: str = Field(..., pattern="^(in|out)$")
    punch_time: Optional[datetime] = None
    source: str = Field(default="web", max_length=30)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    gps_accuracy: Optional[Decimal] = None
    selfie_path: Optional[str] = Field(default=None, max_length=1024)
    device_id: Optional[UUID] = None
    device_log_id: Optional[str] = None
    remarks: Optional[str] = Field(default=None, max_length=500)


class PunchResponse(BaseModel):
    log_id: UUID
    employee_id: UUID
    punch_type: str
    punch_time: datetime
    daily_summary: "DailySummaryResponse"

    model_config = {"from_attributes": True}


class DailySummaryResponse(BaseModel):
    id: UUID
    employee_id: UUID
    tenant_id: UUID
    attendance_date: date
    shift_id: Optional[UUID] = None
    first_in: Optional[datetime] = None
    last_out: Optional[datetime] = None
    total_work_minutes: int
    status: str
    late_minutes: int
    early_leave_minutes: int
    overtime_minutes: int
    is_lop: bool
    lop_days: Decimal
    payable_days: Decimal
    regularization_status: Optional[str] = None

    model_config = {"from_attributes": True}


class DailyAttendanceQuery(BaseModel):
    attendance_date: Optional[date] = None
    employee_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    status: Optional[str] = None


class MonthlyAttendanceSummary(BaseModel):
    employee_id: UUID
    month: int
    year: int
    present_days: Decimal
    absent_days: Decimal
    half_days: Decimal
    late_days: int
    lop_days: Decimal
    payable_days: Decimal
    total_work_minutes: int


class RegularizationCreate(BaseModel):
    employee_id: UUID
    attendance_date: date
    requested_in: Optional[datetime] = None
    requested_out: Optional[datetime] = None
    reason: str = Field(..., min_length=5, max_length=2000)


class RegularizationResponse(BaseModel):
    id: UUID
    employee_id: UUID
    tenant_id: UUID
    attendance_date: date
    requested_in: Optional[datetime] = None
    requested_out: Optional[datetime] = None
    reason: str
    status: str
    approver_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    hr_override: bool = False

    model_config = {"from_attributes": True}


class RegularizationApprove(BaseModel):
    hr_override: bool = False
    rejection_reason: Optional[str] = None


class AttendancePolicyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    grace_minutes: int
    late_threshold_minutes: int
    half_day_hours: Decimal
    full_day_hours: Decimal
    early_leave_threshold_minutes: int
    require_gps_for_mobile: bool
    require_selfie_for_mobile: bool
    is_active: bool

    model_config = {"from_attributes": True}


class AttendancePolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    grace_minutes: Optional[int] = Field(default=None, ge=0, le=120)
    late_threshold_minutes: Optional[int] = Field(default=None, ge=0, le=120)
    half_day_hours: Optional[Decimal] = Field(default=None, ge=0)
    full_day_hours: Optional[Decimal] = Field(default=None, ge=0)
    early_leave_threshold_minutes: Optional[int] = Field(default=None, ge=0, le=120)
    require_gps_for_mobile: Optional[bool] = None
    require_selfie_for_mobile: Optional[bool] = None
    is_active: Optional[bool] = None


class BiometricDeviceCreate(BaseModel):
    device_code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    branch_id: Optional[UUID] = None
    ip_address: Optional[str] = Field(default=None, max_length=45)
    is_active: bool = True


class BiometricDeviceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    device_code: str
    name: str
    branch_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    is_active: bool

    model_config = {"from_attributes": True}


class BiometricSyncResponse(BaseModel):
    device_id: UUID
    records_synced: int
    last_sync_at: datetime


class FieldVisitCreate(BaseModel):
    employee_id: UUID
    visit_date: date
    client_name: str = Field(..., min_length=1, max_length=255)
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    address: Optional[str] = Field(default=None, max_length=500)
    status: str = Field(default="active", max_length=30)
    source: str = Field(default="mobile", max_length=30)


class FieldVisitResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    visit_date: date
    client_name: str
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    address: Optional[str] = None
    status: str
    source: str

    model_config = {"from_attributes": True}


class AttendanceDashboardStats(BaseModel):
    present_today: int
    absent_today: int
    late_today: int
    pending_regularizations: int
    active_biometric_devices: int
    field_visits_today: int
