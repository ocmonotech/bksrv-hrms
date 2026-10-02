from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.utils.validators import validate_aadhaar, validate_ifsc, validate_indian_state, validate_mobile, validate_pan, validate_uan


class AuditFields(BaseModel):
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Nested detail schemas ---


class PersonalDetailBase(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=20)
    marital_status: Optional[str] = Field(default=None, max_length=30)
    blood_group: Optional[str] = Field(default=None, max_length=10)
    nationality: str = "Indian"
    personal_email: Optional[EmailStr] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    emergency_contact_name: Optional[str] = Field(default=None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=20)
    pan_number: Optional[str] = Field(default=None, max_length=10)
    aadhaar_number: Optional[str] = Field(default=None, max_length=12)

    @field_validator("pan_number")
    @classmethod
    def check_pan(cls, v: Optional[str]) -> Optional[str]:
        return validate_pan(v)

    @field_validator("aadhaar_number")
    @classmethod
    def check_aadhaar(cls, v: Optional[str]) -> Optional[str]:
        return validate_aadhaar(v)

    @field_validator("emergency_contact_phone")
    @classmethod
    def check_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_mobile(v)


class PersonalDetailResponse(PersonalDetailBase, AuditFields):
    id: UUID
    employee_id: UUID
    tenant_id: UUID


class JobDetailBase(BaseModel):
    job_title: Optional[str] = Field(default=None, max_length=255)
    work_location: Optional[str] = Field(default=None, max_length=255)
    shift_type: Optional[str] = Field(default=None, max_length=50)
    probation_end_date: Optional[date] = None
    notice_period_days: Optional[int] = Field(default=None, ge=0)
    cost_center_id: Optional[UUID] = None


class JobDetailResponse(JobDetailBase, AuditFields):
    id: UUID
    employee_id: UUID
    tenant_id: UUID


class BankDetailBase(BaseModel):
    account_holder_name: str = Field(..., min_length=2, max_length=255)
    bank_name: str = Field(..., min_length=2, max_length=255)
    account_number: str = Field(..., min_length=5, max_length=50)
    ifsc_code: str = Field(..., min_length=11, max_length=11)
    branch_name: Optional[str] = Field(default=None, max_length=255)
    is_primary: bool = True

    @field_validator("ifsc_code")
    @classmethod
    def check_ifsc(cls, v: str) -> str:
        result = validate_ifsc(v)
        return result if result is not None else v


class BankDetailResponse(BankDetailBase, AuditFields):
    id: UUID
    employee_id: UUID
    tenant_id: UUID


class SalaryDetailBase(BaseModel):
    basic_salary: Optional[Decimal] = Field(default=None, ge=0)
    gross_salary: Optional[Decimal] = Field(default=None, ge=0)
    net_salary: Optional[Decimal] = Field(default=None, ge=0)
    ctc_annual: Optional[Decimal] = Field(default=None, ge=0)
    currency: str = "INR"
    pay_frequency: str = "monthly"
    effective_from: Optional[date] = None


class SalaryDetailResponse(SalaryDetailBase, AuditFields):
    id: UUID
    employee_id: UUID
    tenant_id: UUID


class StatutoryDetailBase(BaseModel):
    pf_number: Optional[str] = Field(default=None, max_length=50)
    uan: Optional[str] = Field(default=None, max_length=20)
    esi_number: Optional[str] = Field(default=None, max_length=50)
    pt_state: Optional[str] = Field(default=None, max_length=100)
    tax_regime: str = "new"
    pan_linked: bool = False

    @field_validator("uan")
    @classmethod
    def check_uan(cls, v: Optional[str]) -> Optional[str]:
        return validate_uan(v)

    @field_validator("pt_state")
    @classmethod
    def check_pt_state(cls, v: Optional[str]) -> Optional[str]:
        return validate_indian_state(v)


class StatutoryDetailResponse(StatutoryDetailBase, AuditFields):
    id: UUID
    employee_id: UUID
    tenant_id: UUID


class FamilyMemberCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    relationship: str = Field(..., min_length=1, max_length=50)
    date_of_birth: Optional[date] = None
    contact_number: Optional[str] = None
    is_dependent: bool = False

    @field_validator("contact_number")
    @classmethod
    def check_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_mobile(v)


class FamilyMemberResponse(AuditFields):
    id: UUID
    employee_id: UUID
    tenant_id: UUID
    name: str
    relationship: str
    date_of_birth: Optional[date] = None
    contact_number: Optional[str] = None
    is_dependent: bool = False

    @model_validator(mode="before")
    @classmethod
    def map_relationship(cls, data: object) -> object:
        if hasattr(data, "relation_type"):
            return {
                "id": data.id,
                "employee_id": data.employee_id,
                "tenant_id": data.tenant_id,
                "name": data.name,
                "relationship": data.relation_type,
                "date_of_birth": data.date_of_birth,
                "contact_number": data.contact_number,
                "is_dependent": data.is_dependent,
                "created_by": data.created_by,
                "updated_by": data.updated_by,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
        return data


class EducationCreate(BaseModel):
    institution: str = Field(..., min_length=1, max_length=255)
    degree: str = Field(..., min_length=1, max_length=255)
    field_of_study: Optional[str] = Field(default=None, max_length=255)
    start_year: Optional[int] = Field(default=None, ge=1950, le=2100)
    end_year: Optional[int] = Field(default=None, ge=1950, le=2100)
    grade: Optional[str] = Field(default=None, max_length=50)


class EducationResponse(EducationCreate, AuditFields):
    id: UUID
    employee_id: UUID
    tenant_id: UUID


class ExperienceCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    job_title: str = Field(..., min_length=1, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    is_current: bool = False


class ExperienceResponse(ExperienceCreate, AuditFields):
    id: UUID
    employee_id: UUID
    tenant_id: UUID


class DocumentResponse(AuditFields):
    id: UUID
    employee_id: UUID
    tenant_id: UUID
    document_type: str
    title: str
    file_path: str
    file_name: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: Optional[UUID] = None


class TimelineResponse(BaseModel):
    id: UUID
    employee_id: UUID
    tenant_id: UUID
    event_type: str
    title: str
    description: Optional[str] = None
    metadata_json: Optional[str] = None
    actor_id: Optional[UUID] = None
    occurred_at: datetime

    model_config = {"from_attributes": True}


# --- Employee CRUD ---


class EmployeeCreate(BaseModel):
    employee_code: Optional[str] = Field(default=None, max_length=50, description="Auto-generated if omitted")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    mobile: Optional[str] = Field(default=None, max_length=20)
    photo_url: Optional[str] = Field(default=None, max_length=512)
    company_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None
    grade_id: Optional[UUID] = None
    reporting_manager_id: Optional[UUID] = None
    joining_date: Optional[date] = None
    confirmation_date: Optional[date] = None
    employment_type: str = Field(default="full_time", max_length=50)
    status: str = Field(default="active", max_length=50)
    personal_detail: Optional[PersonalDetailBase] = None
    job_detail: Optional[JobDetailBase] = None
    bank_detail: Optional[BankDetailBase] = None
    salary_detail: Optional[SalaryDetailBase] = None
    statutory_detail: Optional[StatutoryDetailBase] = None
    family_members: Optional[List[FamilyMemberCreate]] = None
    education: Optional[List[EducationCreate]] = None
    experience: Optional[List[ExperienceCreate]] = None

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v: Optional[str]) -> Optional[str]:
        return validate_mobile(v)


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    mobile: Optional[str] = Field(default=None, max_length=20)
    photo_url: Optional[str] = Field(default=None, max_length=512)
    branch_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None
    grade_id: Optional[UUID] = None
    reporting_manager_id: Optional[UUID] = None
    joining_date: Optional[date] = None
    confirmation_date: Optional[date] = None
    exit_date: Optional[date] = None
    employment_type: Optional[str] = Field(default=None, max_length=50)
    personal_detail: Optional[PersonalDetailBase] = None
    job_detail: Optional[JobDetailBase] = None
    bank_detail: Optional[BankDetailBase] = None
    salary_detail: Optional[SalaryDetailBase] = None
    statutory_detail: Optional[StatutoryDetailBase] = None
    submit_profile_update_request: bool = Field(
        default=False,
        description="When true, sensitive personal changes are queued for HR approval",
    )

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v: Optional[str]) -> Optional[str]:
        return validate_mobile(v)


class EmployeeStatusUpdate(BaseModel):
    status: str = Field(..., max_length=50)
    exit_date: Optional[date] = None
    reason: Optional[str] = Field(default=None, max_length=500)


class EmployeeListItem(BaseModel):
    id: UUID
    tenant_id: UUID
    company_id: Optional[UUID] = None
    employee_code: str
    first_name: str
    last_name: str
    email: str
    mobile: Optional[str] = None
    branch_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None
    employment_type: str
    status: str
    is_active: bool
    joining_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class EmployeeProfileResponse(EmployeeListItem, AuditFields):
    grade_id: Optional[UUID] = None
    reporting_manager_id: Optional[UUID] = None
    confirmation_date: Optional[date] = None
    exit_date: Optional[date] = None
    photo_url: Optional[str] = None
    personal_detail: Optional[PersonalDetailResponse] = None
    job_detail: Optional[JobDetailResponse] = None
    bank_detail: Optional[BankDetailResponse] = None
    salary_detail: Optional[SalaryDetailResponse] = None
    statutory_detail: Optional[StatutoryDetailResponse] = None
    family_members: List[FamilyMemberResponse] = Field(default_factory=list)
    education: List[EducationResponse] = Field(default_factory=list)
    experience: List[ExperienceResponse] = Field(default_factory=list)
    documents: List[DocumentResponse] = Field(default_factory=list)
