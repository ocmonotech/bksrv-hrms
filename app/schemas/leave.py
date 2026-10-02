from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class LeaveTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    is_paid: bool = True
    requires_approval: bool = True
    allow_half_day: bool = True
    max_days_per_year: Optional[Decimal] = Field(default=None, ge=0)
    color: str = "#3B82F6"
    is_active: bool = True


class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    is_paid: Optional[bool] = None
    requires_approval: Optional[bool] = None
    allow_half_day: Optional[bool] = None
    max_days_per_year: Optional[Decimal] = Field(default=None, ge=0)
    color: Optional[str] = None
    is_active: Optional[bool] = None


class LeaveTypeResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    is_paid: bool
    requires_approval: bool
    allow_half_day: bool
    max_days_per_year: Optional[Decimal] = None
    color: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeavePolicyCreate(BaseModel):
    leave_type_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    accrual_frequency: str = "monthly"
    accrual_days: Decimal = Field(default=Decimal("0"), ge=0)
    sandwich_rule_enabled: bool = False
    min_days_notice: int = Field(default=0, ge=0)
    carry_forward_max: Decimal = Field(default=Decimal("0"), ge=0)
    allow_lop: bool = True
    is_active: bool = True


class LeavePolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    accrual_frequency: Optional[str] = None
    accrual_days: Optional[Decimal] = Field(default=None, ge=0)
    sandwich_rule_enabled: Optional[bool] = None
    min_days_notice: Optional[int] = Field(default=None, ge=0)
    carry_forward_max: Optional[Decimal] = Field(default=None, ge=0)
    allow_lop: Optional[bool] = None
    is_active: Optional[bool] = None


class LeavePolicyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    leave_type_id: UUID
    name: str
    accrual_frequency: str
    accrual_days: Decimal
    sandwich_rule_enabled: bool
    min_days_notice: int
    carry_forward_max: Decimal
    allow_lop: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaveApplyRequest(BaseModel):
    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    is_half_day: bool = False
    half_day_period: Optional[str] = Field(default=None, pattern="^(first_half|second_half)$")
    reason: str = Field(..., min_length=3, max_length=2000)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be on or after start_date")
        return v


class LeaveRequestResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    total_days: Decimal
    is_half_day: bool
    half_day_period: Optional[str] = None
    reason: str
    status: str
    approver_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    sandwich_days: Decimal
    lop_days: Decimal
    hr_override: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class LeaveApproveRequest(BaseModel):
    hr_override: bool = False
    notes: Optional[str] = None


class LeaveRejectRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=3, max_length=500)
    hr_override: bool = False


class LeaveBalanceResponse(BaseModel):
    employee_id: UUID
    leave_type_id: UUID
    leave_type_code: str
    leave_type_name: str
    year: int
    opening_balance: Decimal
    accrued: Decimal
    used: Decimal
    adjusted: Decimal
    closing_balance: Decimal


class LeaveCalendarEntry(BaseModel):
    date: date
    employee_id: UUID
    leave_request_id: UUID
    leave_type_code: str
    leave_type_name: str
    status: str
    is_half_day: bool


class CompOffCreate(BaseModel):
    employee_id: UUID
    worked_date: date
    comp_off_date: Optional[date] = None
    reason: str = Field(..., min_length=3, max_length=2000)


class CompOffResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    worked_date: date
    comp_off_date: Optional[date] = None
    reason: str
    status: str
    approver_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GenerateBalanceRequest(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    employee_ids: Optional[List[UUID]] = None
