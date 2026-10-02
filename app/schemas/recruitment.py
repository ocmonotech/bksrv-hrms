from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobOpeningCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    openings_count: int = Field(default=1, ge=1)
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[Decimal] = Field(default=None, ge=0)
    salary_max: Optional[Decimal] = Field(default=None, ge=0)
    closing_date: Optional[date] = None
    is_active: bool = True


class JobOpeningUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    openings_count: Optional[int] = Field(default=None, ge=1)
    status: Optional[str] = Field(default=None, max_length=30)
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[Decimal] = Field(default=None, ge=0)
    salary_max: Optional[Decimal] = Field(default=None, ge=0)
    closing_date: Optional[date] = None
    is_active: Optional[bool] = None


class JobOpeningResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    title: str
    code: str
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    openings_count: int
    status: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    published_at: Optional[datetime] = None
    closing_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CandidateCreate(BaseModel):
    job_opening_id: UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    mobile: Optional[str] = Field(default=None, max_length=20)
    source: str = Field(default="direct", max_length=50)
    experience_years: Optional[Decimal] = None
    current_company: Optional[str] = None
    referred_by_employee_id: Optional[UUID] = None
    notes: Optional[str] = None


class CandidateUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    mobile: Optional[str] = None
    current_stage: Optional[str] = None
    status: Optional[str] = None
    experience_years: Optional[Decimal] = None
    current_company: Optional[str] = None
    notes: Optional[str] = None


class CandidateResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    job_opening_id: UUID
    first_name: str
    last_name: str
    email: str
    mobile: Optional[str] = None
    source: str
    current_stage: str
    status: str
    resume_path: Optional[str] = None
    experience_years: Optional[Decimal] = None
    current_company: Optional[str] = None
    referred_by_employee_id: Optional[UUID] = None
    employee_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateStartOnboardingResponse(BaseModel):
    candidate_id: UUID
    employee_id: UUID
    employee_code: str
    onboarding_tasks_created: int
    message: str


class CandidateDocumentResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    document_type: str
    file_name: str
    file_path: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InterviewCreate(BaseModel):
    candidate_id: UUID
    job_opening_id: UUID
    scheduled_at: datetime
    interview_type: str = Field(default="technical", max_length=50)
    interviewer_id: Optional[UUID] = None
    mode: str = Field(default="online", max_length=30)
    location: Optional[str] = None
    notes: Optional[str] = None


class InterviewUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    interview_type: Optional[str] = None
    interviewer_id: Optional[UUID] = None
    mode: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class InterviewResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    candidate_id: UUID
    job_opening_id: UUID
    scheduled_at: datetime
    interview_type: str
    interviewer_id: Optional[UUID] = None
    mode: str
    location: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OfferLetterCreate(BaseModel):
    candidate_id: UUID
    job_opening_id: UUID
    offered_ctc: Decimal = Field(..., ge=0)
    joining_date: date
    designation_id: Optional[UUID] = None
    notes: Optional[str] = None


class OfferLetterUpdate(BaseModel):
    offered_ctc: Optional[Decimal] = Field(default=None, ge=0)
    joining_date: Optional[date] = None
    designation_id: Optional[UUID] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class OfferApproveRequest(BaseModel):
    notes: Optional[str] = None


class OfferLetterResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    candidate_id: UUID
    job_opening_id: UUID
    offered_ctc: Decimal
    joining_date: date
    designation_id: Optional[UUID] = None
    status: str
    approver_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    document_path: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InterviewFeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    recommendation: str = Field(..., max_length=30)
    comments: str = Field(..., min_length=1)
    technical_skills: Optional[int] = Field(default=None, ge=1, le=5)
    communication: Optional[int] = Field(default=None, ge=1, le=5)
    culture_fit: Optional[int] = Field(default=None, ge=1, le=5)


class InterviewFeedbackResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    interview_id: UUID
    candidate_id: UUID
    candidate_name: str
    interviewer_name: str
    rating: Optional[int] = None
    recommendation: str
    comments: str
    technical_skills: Optional[int] = None
    communication: Optional[int] = None
    culture_fit: Optional[int] = None
    submitted_at: datetime

    model_config = {"from_attributes": True}


class JobBoardConnectionUpsert(BaseModel):
    account_name: Optional[str] = Field(default=None, max_length=255)
    api_key: Optional[str] = Field(default=None, max_length=500)


class JobBoardConnectionResponse(BaseModel):
    platform: str
    label: str
    status: str
    account_name: Optional[str] = None
    api_key_hint: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class JobBoardPostingResponse(BaseModel):
    id: UUID
    job_opening_id: UUID
    job_title: str
    platform: str
    external_job_id: Optional[str] = None
    external_url: Optional[str] = None
    status: str
    applicant_count: int
    posted_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobBoardPostRequest(BaseModel):
    job_opening_id: UUID
    platforms: list[str] = Field(..., min_length=1)


class JobBoardSyncResponse(BaseModel):
    synced_at: datetime
    connections_updated: int
    postings_updated: int
    applicants_imported: int = 0
