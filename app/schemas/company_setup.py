from __future__ import annotations

import json
from datetime import date, datetime
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants.india import INDIA_DEFAULTS
from app.utils.validators import (
    validate_gstin,
    validate_india_country,
    validate_india_timezone,
    validate_indian_state,
    validate_inr_currency,
    validate_mobile,
    validate_pincode,
)

T = TypeVar("T")


class ListQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None


class AuditFields(BaseModel):
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Company Profile ---


class CompanyProfileUpdate(BaseModel):
    company_id: Optional[UUID] = None
    display_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=100)
    tax_id: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = Field(default=None, max_length=512)
    address_line1: Optional[str] = Field(default=None, max_length=255)
    address_line2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    timezone: Optional[str] = Field(default=None, max_length=64)
    currency: Optional[str] = Field(default=None, max_length=8)
    fiscal_year_start_month: Optional[int] = Field(default=None, ge=1, le=12)
    is_active: Optional[bool] = None

    @field_validator("tax_id")
    @classmethod
    def check_tax_id(cls, v: Optional[str]) -> Optional[str]:
        return validate_gstin(v)

    @field_validator("postal_code")
    @classmethod
    def check_postal_code(cls, v: Optional[str]) -> Optional[str]:
        return validate_pincode(v)

    @field_validator("state")
    @classmethod
    def check_state(cls, v: Optional[str]) -> Optional[str]:
        return validate_indian_state(v)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_mobile(v)

    @field_validator("country")
    @classmethod
    def check_country(cls, v: Optional[str]) -> Optional[str]:
        return validate_india_country(v)

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: Optional[str]) -> Optional[str]:
        return validate_inr_currency(v)

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, v: Optional[str]) -> Optional[str]:
        return validate_india_timezone(v)


class CompanyProfileCreate(CompanyProfileUpdate):
    display_name: str = Field(..., min_length=2, max_length=255)


class CompanyProfileResponse(AuditFields):
    id: UUID
    tenant_id: UUID
    company_id: Optional[UUID] = None
    display_name: str
    legal_name: Optional[str] = None
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    postal_code: Optional[str] = None
    timezone: str
    currency: str
    fiscal_year_start_month: int
    is_active: bool


# --- Shared CRUD schemas ---


class TenantEntityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True


class TenantEntityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class TenantEntityResponse(AuditFields):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool


# --- Branch ---


class BranchCreate(TenantEntityBase):
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    postal_code: Optional[str] = None
    is_head_office: bool = False

    @field_validator("postal_code")
    @classmethod
    def check_postal_code(cls, v: Optional[str]) -> Optional[str]:
        return validate_pincode(v)

    @field_validator("state")
    @classmethod
    def check_state(cls, v: Optional[str]) -> Optional[str]:
        return validate_indian_state(v)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_mobile(v)

    @field_validator("country")
    @classmethod
    def check_country(cls, v: str) -> str:
        return validate_india_country(v) or INDIA_DEFAULTS["country"]


class BranchUpdate(TenantEntityUpdate):
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    is_head_office: Optional[bool] = None

    @field_validator("postal_code")
    @classmethod
    def check_postal_code(cls, v: Optional[str]) -> Optional[str]:
        return validate_pincode(v)

    @field_validator("state")
    @classmethod
    def check_state(cls, v: Optional[str]) -> Optional[str]:
        return validate_indian_state(v)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_mobile(v)

    @field_validator("country")
    @classmethod
    def check_country(cls, v: Optional[str]) -> Optional[str]:
        return validate_india_country(v) if v is not None else None


class BranchResponse(TenantEntityResponse):
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    postal_code: Optional[str] = None
    is_head_office: bool


# --- Department ---


class DepartmentCreate(TenantEntityBase):
    branch_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    head_name: Optional[str] = None


class DepartmentUpdate(TenantEntityUpdate):
    branch_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    head_name: Optional[str] = None


class DepartmentResponse(TenantEntityResponse):
    branch_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    head_name: Optional[str] = None


# --- Grade ---


class GradeCreate(TenantEntityBase):
    level: int = Field(default=1, ge=1)


class GradeUpdate(TenantEntityUpdate):
    level: Optional[int] = Field(default=None, ge=1)


class GradeResponse(TenantEntityResponse):
    level: int


# --- Designation ---


class DesignationCreate(TenantEntityBase):
    department_id: Optional[UUID] = None
    grade_id: Optional[UUID] = None


class DesignationUpdate(TenantEntityUpdate):
    department_id: Optional[UUID] = None
    grade_id: Optional[UUID] = None


class DesignationResponse(TenantEntityResponse):
    department_id: Optional[UUID] = None
    grade_id: Optional[UUID] = None


# --- Cost Center ---


class CostCenterCreate(TenantEntityBase):
    department_id: Optional[UUID] = None
    budget_code: Optional[str] = None


class CostCenterUpdate(TenantEntityUpdate):
    department_id: Optional[UUID] = None
    budget_code: Optional[str] = None


class CostCenterResponse(TenantEntityResponse):
    department_id: Optional[UUID] = None
    budget_code: Optional[str] = None


# --- Holiday ---


class HolidayCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    holiday_date: date
    holiday_type: str = Field(default="public", max_length=50)
    branch_id: Optional[UUID] = None
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True


class HolidayUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    holiday_date: Optional[date] = None
    holiday_type: Optional[str] = Field(default=None, max_length=50)
    branch_id: Optional[UUID] = None
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class HolidayResponse(AuditFields):
    id: UUID
    tenant_id: UUID
    name: str
    holiday_date: date
    holiday_type: str
    branch_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: bool


# --- Policy ---


class PolicyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    category: str = Field(default="general", max_length=100)
    summary: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    version: str = Field(default="1.0", max_length=20)
    document_url: Optional[str] = Field(default=None, max_length=512)
    is_active: bool = True


class PolicyUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    category: Optional[str] = Field(default=None, max_length=100)
    summary: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    version: Optional[str] = Field(default=None, max_length=20)
    document_url: Optional[str] = Field(default=None, max_length=512)
    is_active: Optional[bool] = None


class PolicyResponse(AuditFields):
    id: UUID
    tenant_id: UUID
    title: str
    code: str
    category: str
    summary: Optional[str] = None
    content: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    version: str
    document_url: Optional[str] = None
    is_active: bool


# --- Approval Workflow ---


class ApprovalStepCreate(BaseModel):
    step_order: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=255)
    approver_type: str = Field(default="role", max_length=50)
    approver_role: Optional[str] = Field(default=None, max_length=50)
    approver_user_id: Optional[UUID] = None
    is_required: bool = True
    is_active: bool = True


class ApprovalStepUpdate(BaseModel):
    step_order: Optional[int] = Field(default=None, ge=1)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    approver_type: Optional[str] = Field(default=None, max_length=50)
    approver_role: Optional[str] = Field(default=None, max_length=50)
    approver_user_id: Optional[UUID] = None
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None


class ApprovalStepResponse(AuditFields):
    id: UUID
    tenant_id: UUID
    workflow_id: UUID
    step_order: int
    name: str
    approver_type: str
    approver_role: Optional[str] = None
    approver_user_id: Optional[UUID] = None
    is_required: bool
    is_active: bool


class ApprovalWorkflowCreate(TenantEntityBase):
    entity_type: str = Field(..., min_length=1, max_length=100)
    steps: list[ApprovalStepCreate] = Field(default_factory=list)


class ApprovalWorkflowUpdate(TenantEntityUpdate):
    entity_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    steps: Optional[list[ApprovalStepCreate]] = None


class ApprovalWorkflowSummary(TenantEntityResponse):
    entity_type: str


class ApprovalWorkflowResponse(TenantEntityResponse):
    entity_type: str
    steps: list[ApprovalStepResponse] = Field(default_factory=list)
