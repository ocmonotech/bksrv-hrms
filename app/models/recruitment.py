from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class JobOpening(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "job_openings"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    designation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("designations.id", ondelete="SET NULL"), nullable=True
    )
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )
    openings_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_job_openings_tenant_code"),)


class Candidate(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "candidates"

    job_opening_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="direct", nullable=False)
    current_stage: Mapped[str] = mapped_column(String(50), default="applied", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    resume_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    experience_years: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    current_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    referred_by_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CandidateDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "candidate_documents"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="uploaded", nullable=False)


class CandidateStageHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "candidate_stage_histories"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class Interview(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "interviews"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_opening_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interview_type: Mapped[str] = mapped_column(String(50), default="technical", nullable=False)
    interviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    mode: Mapped[str] = mapped_column(String(30), default="online", nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class InterviewFeedback(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "interview_feedbacks"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[str] = mapped_column(String(30), default="hold", nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class OfferLetter(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "offer_letters"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_opening_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    offered_ctc: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    designation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("designations.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    document_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Referral(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "referrals"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    referrer_employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bonus_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    bonus_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class JobBoardConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "job_board_connections"

    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="disconnected", nullable=False)
    account_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    api_key_hint: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "platform", name="uq_job_board_connections_tenant_platform"),)


class JobBoardPosting(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "job_board_postings"

    job_opening_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    applicant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "job_opening_id", "platform", name="uq_job_board_postings_tenant_job_platform"),
    )
