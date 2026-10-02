from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Employee(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employees"

    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    designation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("designations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    grade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("grades.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reporting_manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )
    joining_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    confirmation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    exit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_type: Mapped[str] = mapped_column(String(50), default="full_time", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    personal_detail: Mapped[Optional["EmployeePersonalDetail"]] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    job_detail: Mapped[Optional["EmployeeJobDetail"]] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    bank_detail: Mapped[Optional["EmployeeBankDetail"]] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    salary_detail: Mapped[Optional["EmployeeSalaryDetail"]] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    statutory_detail: Mapped[Optional["EmployeeStatutoryDetail"]] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    family_members: Mapped[list["EmployeeFamilyDetail"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    education: Mapped[list["EmployeeEducation"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    experience: Mapped[list["EmployeeExperience"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    documents: Mapped[list["EmployeeDocument"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    timeline: Mapped[list["EmployeeTimeline"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan", order_by="EmployeeTimeline.occurred_at.desc()"
    )
    profile_update_requests: Mapped[list["EmployeeProfileUpdateRequest"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("tenant_id", "employee_code", name="uq_employees_tenant_code"),)


class EmployeePersonalDetail(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_personal_details"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    marital_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    blood_group: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    nationality: Mapped[str] = mapped_column(String(100), default="Indian", nullable=False)
    personal_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permanent_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pan_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    aadhaar_number: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="personal_detail")


class EmployeeJobDetail(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_job_details"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shift_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    probation_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notice_period_days: Mapped[Optional[int]] = mapped_column(nullable=True)
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True
    )

    employee: Mapped["Employee"] = relationship(back_populates="job_detail")


class EmployeeBankDetail(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_bank_details"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    account_holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    ifsc_code: Mapped[str] = mapped_column(String(20), nullable=False)
    branch_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee: Mapped["Employee"] = relationship(back_populates="bank_detail")


class EmployeeFamilyDetail(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_family_details"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relation_type: Mapped[str] = mapped_column("relationship", String(50), nullable=False)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contact_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_dependent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    employee: Mapped["Employee"] = relationship(back_populates="family_members")


class EmployeeEducation(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_education"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(255), nullable=False)
    field_of_study: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_year: Mapped[Optional[int]] = mapped_column(nullable=True)
    end_year: Mapped[Optional[int]] = mapped_column(nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="education")


class EmployeeExperience(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_experience"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    employee: Mapped["Employee"] = relationship(back_populates="experience")


class EmployeeDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_documents"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="documents")


class EmployeeSalaryDetail(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_salary_details"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    basic_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    gross_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    net_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    ctc_annual: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    pay_frequency: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="salary_detail")


class EmployeeStatutoryDetail(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_statutory_details"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    pf_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    uan: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    esi_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pt_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tax_regime: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    pan_linked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    employee: Mapped["Employee"] = relationship(back_populates="statutory_detail")


class EmployeeTimeline(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "employee_timeline"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    employee: Mapped["Employee"] = relationship(back_populates="timeline")


class EmployeeProfileUpdateRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "employee_profile_update_requests"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    changes_json: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="profile_update_requests")
