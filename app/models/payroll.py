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


class SalaryComponent(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "salary_components"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    component_type: Mapped[str] = mapped_column(String(20), nullable=False)  # earning | deduction
    calculation_type: Mapped[str] = mapped_column(String(30), default="fixed", nullable=False)
    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_statutory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pf_applicable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    esi_applicable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pt_applicable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_salary_components_tenant_code"),)


class SalaryStructure(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "salary_structures"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    annual_ctc: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    components_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_salary_structures_tenant_code"),)


class EmployeeSalaryStructure(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "employee_salary_structures"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    structure_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("salary_structures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    annual_ctc: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    arrears_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PayrollRun(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, AuditMixin):
    __tablename__ = "payroll_runs"

    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    working_days: Mapped[int] = mapped_column(Integer, default=26, nullable=False)
    run_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_gross: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0, nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0, nullable=False)
    total_net: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0, nullable=False)
    employee_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "month", "year", name="uq_payroll_runs_tenant_period"),
    )


class PayrollEmployee(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, AuditMixin):
    __tablename__ = "payroll_employees"

    payroll_run_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    working_days: Mapped[int] = mapped_column(Integer, default=26, nullable=False)
    payable_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    lop_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    overtime_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gross_earnings: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    arrears_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    reimbursement_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    pf_employee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    pf_employer: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    esi_employee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    esi_employer: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    professional_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    tds_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    lop_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("payroll_run_id", "employee_id", name="uq_payroll_employees_run_emp"),
    )


class PayrollEarning(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "payroll_earnings"

    payroll_employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("payroll_employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("salary_components.id", ondelete="SET NULL"), nullable=True
    )
    component_code: Mapped[str] = mapped_column(String(50), nullable=False)
    component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    earning_type: Mapped[str] = mapped_column(String(30), default="regular", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class PayrollDeduction(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "payroll_deductions"

    payroll_employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("payroll_employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("salary_components.id", ondelete="SET NULL"), nullable=True
    )
    component_code: Mapped[str] = mapped_column(String(50), nullable=False)
    component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    deduction_type: Mapped[str] = mapped_column(String(30), default="other", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class Payslip(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, AuditMixin):
    __tablename__ = "payslips"

    payroll_employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("payroll_employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payroll_run_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_earnings: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_items_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "month", "year", name="uq_payslips_emp_period"),
    )


class TaxDeclaration(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "tax_declarations"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    financial_year: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    regime: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    section: Mapped[str] = mapped_column(String(50), nullable=False)
    declared_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)


class InvestmentProof(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "investment_proofs"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tax_declaration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("tax_declarations.id", ondelete="SET NULL"), nullable=True
    )
    proof_type: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    document_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)


class StatutorySetting(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "statutory_settings"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    pf_employee_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.12"), nullable=False)
    pf_employer_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.12"), nullable=False)
    pf_wage_ceiling: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("15000"), nullable=False)
    esi_employee_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.0075"), nullable=False)
    esi_employer_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.0325"), nullable=False)
    esi_gross_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("21000"), nullable=False)
    pt_slabs_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    tds_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    overtime_multiplier: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_statutory_settings_tenant_code"),)


class FullAndFinalSettlement(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "full_and_final_settlements"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    last_working_date: Mapped[date] = mapped_column(Date, nullable=False)
    settlement_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    net_payable: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
