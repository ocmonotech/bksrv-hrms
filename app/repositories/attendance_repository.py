from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import (
    AttendanceDailySummary,
    AttendanceLog,
    AttendancePolicy,
    AttendanceRegularization,
    BiometricDevice,
    FieldVisit,
)
from app.models.employee import Employee
from app.models.shift import EmployeeShiftAssignment, Roster, Shift
from app.repositories.base import BaseRepository
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class AttendanceLogRepository(BaseRepository[AttendanceLog]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AttendanceLog)

    def list_for_day(self, tenant_id: UUID, employee_id: UUID, attendance_date: date) -> list[AttendanceLog]:
        stmt = (
            select(AttendanceLog)
            .where(
                AttendanceLog.tenant_id == str(tenant_id),
                AttendanceLog.employee_id == str(employee_id),
                func.date(AttendanceLog.punch_time) == attendance_date,
                AttendanceLog.is_valid.is_(True),
            )
            .order_by(AttendanceLog.punch_time)
        )
        return list(self.db.scalars(stmt))


class AttendanceDailySummaryRepository(BaseRepository[AttendanceDailySummary]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AttendanceDailySummary)

    def get_for_day(
        self, tenant_id: UUID, employee_id: UUID, attendance_date: date
    ) -> Optional[AttendanceDailySummary]:
        stmt = select(AttendanceDailySummary).where(
            AttendanceDailySummary.tenant_id == str(tenant_id),
            AttendanceDailySummary.employee_id == str(employee_id),
            AttendanceDailySummary.attendance_date == attendance_date,
        )
        return self.db.scalar(stmt)

    def list_for_month(
        self,
        tenant_id: UUID,
        *,
        year: int,
        month: int,
        employee_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> list[AttendanceDailySummary]:
        stmt = select(AttendanceDailySummary).where(
            AttendanceDailySummary.tenant_id == str(tenant_id),
            func.extract("year", AttendanceDailySummary.attendance_date) == year,
            func.extract("month", AttendanceDailySummary.attendance_date) == month,
        )
        if employee_id:
            stmt = stmt.where(AttendanceDailySummary.employee_id == str(employee_id))
        if status:
            stmt = stmt.where(AttendanceDailySummary.status == status)
        if branch_id or department_id:
            stmt = stmt.join(Employee, Employee.id == AttendanceDailySummary.employee_id)
            if branch_id:
                stmt = stmt.where(Employee.branch_id == str(branch_id))
            if department_id:
                stmt = stmt.where(Employee.department_id == str(department_id))
        stmt = stmt.order_by(AttendanceDailySummary.attendance_date)
        return list(self.db.scalars(stmt))


class AttendanceRegularizationRepository(TenantScopedRepository[AttendanceRegularization]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AttendanceRegularization)

    def list_pending(self, tenant_id: UUID) -> list[AttendanceRegularization]:
        stmt = (
            select(AttendanceRegularization)
            .where(
                AttendanceRegularization.tenant_id == str(tenant_id),
                AttendanceRegularization.status == "pending",
                AttendanceRegularization.deleted_at.is_(None),
            )
            .order_by(AttendanceRegularization.attendance_date.desc())
        )
        return list(self.db.scalars(stmt))


class AttendancePolicyRepository(TenantScopedRepository[AttendancePolicy]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AttendancePolicy)

    def get_first_or_none(self, tenant_id: UUID) -> Optional[AttendancePolicy]:
        stmt = (
            select(AttendancePolicy)
            .where(
                AttendancePolicy.tenant_id == str(tenant_id),
                AttendancePolicy.deleted_at.is_(None),
            )
            .order_by(AttendancePolicy.created_at)
            .limit(1)
        )
        return self.db.scalar(stmt)


class BiometricDeviceRepository(TenantScopedRepository[BiometricDevice]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, BiometricDevice)


class FieldVisitRepository(TenantScopedRepository[FieldVisit]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, FieldVisit)

    def list_for_tenant(self, tenant_id: UUID, *, visit_date: Optional[date] = None) -> list[FieldVisit]:
        stmt = select(FieldVisit).where(
            FieldVisit.tenant_id == str(tenant_id),
            FieldVisit.deleted_at.is_(None),
        )
        if visit_date:
            stmt = stmt.where(FieldVisit.visit_date == visit_date)
        stmt = stmt.order_by(FieldVisit.visit_date.desc(), FieldVisit.created_at.desc())
        return list(self.db.scalars(stmt))


class ShiftRepository(TenantScopedRepository[Shift]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Shift)


class RosterRepository(TenantScopedRepository[Roster]):
    search_fields = ("notes",)

    def __init__(self, db: Session) -> None:
        super().__init__(db, Roster, search_fields=self.search_fields)

    def get_for_day(self, tenant_id: UUID, employee_id: UUID, roster_date: date) -> Optional[Roster]:
        stmt = select(Roster).where(
            Roster.tenant_id == str(tenant_id),
            Roster.employee_id == str(employee_id),
            Roster.roster_date == roster_date,
            Roster.deleted_at.is_(None),
            Roster.is_active.is_(True),
        )
        return self.db.scalar(stmt)


class EmployeeShiftAssignmentRepository(TenantScopedRepository[EmployeeShiftAssignment]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, EmployeeShiftAssignment)

    def get_active_for_date(
        self, tenant_id: UUID, employee_id: UUID, on_date: date
    ) -> Optional[EmployeeShiftAssignment]:
        stmt = (
            select(EmployeeShiftAssignment)
            .where(
                EmployeeShiftAssignment.tenant_id == str(tenant_id),
                EmployeeShiftAssignment.employee_id == str(employee_id),
                EmployeeShiftAssignment.is_active.is_(True),
                EmployeeShiftAssignment.deleted_at.is_(None),
                EmployeeShiftAssignment.effective_from <= on_date,
            )
            .order_by(EmployeeShiftAssignment.effective_from.desc())
        )
        assignments = list(self.db.scalars(stmt))
        for assignment in assignments:
            if assignment.effective_to is None or assignment.effective_to >= on_date:
                return assignment
        return None
