from __future__ import annotations

import calendar
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceDailySummary
from app.models.employee import Employee, EmployeeBankDetail
from app.models.payroll import (
    EmployeeSalaryStructure,
    PayrollDeduction,
    PayrollEmployee,
    PayrollEarning,
    PayrollRun,
    Payslip,
    SalaryComponent,
    SalaryStructure,
    StatutorySetting,
    TaxDeclaration,
)
from app.repositories.base import BaseRepository
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class SalaryComponentRepository(TenantScopedRepository[SalaryComponent]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, SalaryComponent)


class SalaryStructureRepository(TenantScopedRepository[SalaryStructure]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, SalaryStructure)


class EmployeeSalaryStructureRepository(TenantScopedRepository[EmployeeSalaryStructure]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, EmployeeSalaryStructure)

    def get_active_for_employee(
        self, tenant_id: UUID, employee_id: UUID, on_date: date
    ) -> Optional[EmployeeSalaryStructure]:
        stmt = (
            select(EmployeeSalaryStructure)
            .where(
                EmployeeSalaryStructure.tenant_id == str(tenant_id),
                EmployeeSalaryStructure.employee_id == str(employee_id),
                EmployeeSalaryStructure.is_active.is_(True),
                EmployeeSalaryStructure.deleted_at.is_(None),
                EmployeeSalaryStructure.effective_from <= on_date,
            )
            .order_by(EmployeeSalaryStructure.effective_from.desc())
        )
        for row in self.db.scalars(stmt):
            if row.effective_to is None or row.effective_to >= on_date:
                return row
        return None


class PayrollRunRepository(BaseRepository[PayrollRun]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PayrollRun)

    def get_by_period(self, tenant_id: UUID, month: int, year: int) -> Optional[PayrollRun]:
        stmt = select(PayrollRun).where(
            PayrollRun.tenant_id == str(tenant_id),
            PayrollRun.month == month,
            PayrollRun.year == year,
        )
        return self.db.scalar(stmt)

    def get_scoped(self, run_id: UUID, tenant_id: UUID) -> Optional[PayrollRun]:
        stmt = select(PayrollRun).where(
            PayrollRun.id == str(run_id),
            PayrollRun.tenant_id == str(tenant_id),
        )
        return self.db.scalar(stmt)

    def list_runs(self, tenant_id: UUID, *, limit: int = 24) -> list[PayrollRun]:
        stmt = (
            select(PayrollRun)
            .where(PayrollRun.tenant_id == str(tenant_id))
            .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))


class PayrollEmployeeRepository(BaseRepository[PayrollEmployee]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PayrollEmployee)

    def list_for_run(self, run_id: UUID) -> list[PayrollEmployee]:
        stmt = select(PayrollEmployee).where(PayrollEmployee.payroll_run_id == str(run_id))
        return list(self.db.scalars(stmt))

    def get_for_run_employee(self, run_id: UUID, employee_id: UUID) -> Optional[PayrollEmployee]:
        stmt = select(PayrollEmployee).where(
            PayrollEmployee.payroll_run_id == str(run_id),
            PayrollEmployee.employee_id == str(employee_id),
        )
        return self.db.scalar(stmt)


class PayrollEarningRepository(BaseRepository[PayrollEarning]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PayrollEarning)

    def list_for_payroll_employee(self, payroll_employee_id: UUID) -> list[PayrollEarning]:
        stmt = select(PayrollEarning).where(
            PayrollEarning.payroll_employee_id == str(payroll_employee_id)
        )
        return list(self.db.scalars(stmt))


class PayrollDeductionRepository(BaseRepository[PayrollDeduction]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PayrollDeduction)

    def list_for_payroll_employee(self, payroll_employee_id: UUID) -> list[PayrollDeduction]:
        stmt = select(PayrollDeduction).where(
            PayrollDeduction.payroll_employee_id == str(payroll_employee_id)
        )
        return list(self.db.scalars(stmt))


class PayslipRepository(BaseRepository[Payslip]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Payslip)

    def list_for_employee(
        self, tenant_id: UUID, employee_id: UUID, *, year: Optional[int] = None
    ) -> list[Payslip]:
        stmt = select(Payslip).where(
            Payslip.tenant_id == str(tenant_id),
            Payslip.employee_id == str(employee_id),
        )
        if year:
            stmt = stmt.where(Payslip.year == year)
        stmt = stmt.order_by(Payslip.year.desc(), Payslip.month.desc())
        return list(self.db.scalars(stmt))


class StatutorySettingRepository(TenantScopedRepository[StatutorySetting]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, StatutorySetting)

    def get_active(self, tenant_id: UUID) -> Optional[StatutorySetting]:
        stmt = select(StatutorySetting).where(
            StatutorySetting.tenant_id == str(tenant_id),
            StatutorySetting.is_active.is_(True),
            StatutorySetting.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)


class TaxDeclarationRepository(TenantScopedRepository[TaxDeclaration]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, TaxDeclaration)


class AttendanceSummaryRepository(BaseRepository[AttendanceDailySummary]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AttendanceDailySummary)

    def aggregate_for_month(
        self, tenant_id: UUID, employee_id: UUID, month: int, year: int
    ) -> tuple[float, float, int]:
        stmt = select(
            func.coalesce(func.sum(AttendanceDailySummary.payable_days), 0),
            func.coalesce(func.sum(AttendanceDailySummary.lop_days), 0),
            func.coalesce(func.sum(AttendanceDailySummary.overtime_minutes), 0),
        ).where(
            AttendanceDailySummary.tenant_id == str(tenant_id),
            AttendanceDailySummary.employee_id == str(employee_id),
            func.extract("month", AttendanceDailySummary.attendance_date) == month,
            func.extract("year", AttendanceDailySummary.attendance_date) == year,
            AttendanceDailySummary.is_payroll_locked.is_(False),
        )
        row = self.db.execute(stmt).one()
        return float(row[0]), float(row[1]), int(row[2] or 0)


class EmployeeBankRepository(BaseRepository[EmployeeBankDetail]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, EmployeeBankDetail)

    def get_for_employee(self, employee_id: UUID) -> Optional[EmployeeBankDetail]:
        stmt = select(EmployeeBankDetail).where(EmployeeBankDetail.employee_id == str(employee_id))
        return self.db.scalar(stmt)
