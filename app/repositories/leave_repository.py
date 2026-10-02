from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_setup import Holiday
from app.models.employee import Employee
from app.models.leave import CompOffRequest, LeaveBalance, LeavePolicy, LeaveRequest, LeaveType
from app.repositories.base import BaseRepository
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class LeaveTypeRepository(TenantScopedRepository[LeaveType]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, LeaveType)


class LeavePolicyRepository(TenantScopedRepository[LeavePolicy]):
    search_fields = ("name",)

    def __init__(self, db: Session) -> None:
        super().__init__(db, LeavePolicy, search_fields=self.search_fields)

    def get_active_for_type(self, tenant_id: UUID, leave_type_id: UUID) -> Optional[LeavePolicy]:
        stmt = select(LeavePolicy).where(
            LeavePolicy.tenant_id == str(tenant_id),
            LeavePolicy.leave_type_id == str(leave_type_id),
            LeavePolicy.is_active.is_(True),
            LeavePolicy.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)


class LeaveBalanceRepository(BaseRepository[LeaveBalance]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, LeaveBalance)

    def get_balance(
        self, tenant_id: UUID, employee_id: UUID, leave_type_id: UUID, year: int
    ) -> Optional[LeaveBalance]:
        stmt = select(LeaveBalance).where(
            LeaveBalance.tenant_id == str(tenant_id),
            LeaveBalance.employee_id == str(employee_id),
            LeaveBalance.leave_type_id == str(leave_type_id),
            LeaveBalance.year == year,
        )
        return self.db.scalar(stmt)

    def list_for_employee(self, tenant_id: UUID, employee_id: UUID, year: int) -> list[LeaveBalance]:
        stmt = select(LeaveBalance).where(
            LeaveBalance.tenant_id == str(tenant_id),
            LeaveBalance.employee_id == str(employee_id),
            LeaveBalance.year == year,
        )
        return list(self.db.scalars(stmt))


class LeaveRequestRepository(TenantScopedRepository[LeaveRequest]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, LeaveRequest)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> tuple[list[LeaveRequest], int]:
        extra = []
        if employee_id:
            extra.append(LeaveRequest.employee_id == str(employee_id))
        if status:
            extra.append(LeaveRequest.status == status)
        if start_date:
            extra.append(LeaveRequest.end_date >= start_date)
        if end_date:
            extra.append(LeaveRequest.start_date <= end_date)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)

    def overlapping(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        start_date: date,
        end_date: date,
        exclude_id: Optional[UUID] = None,
    ) -> list[LeaveRequest]:
        stmt = select(LeaveRequest).where(
            LeaveRequest.tenant_id == str(tenant_id),
            LeaveRequest.employee_id == str(employee_id),
            LeaveRequest.deleted_at.is_(None),
            LeaveRequest.status.in_(("pending", "approved")),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        if exclude_id:
            stmt = stmt.where(LeaveRequest.id != str(exclude_id))
        return list(self.db.scalars(stmt))

    def calendar_entries(
        self,
        tenant_id: UUID,
        *,
        start_date: date,
        end_date: date,
        employee_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
    ) -> list[tuple[LeaveRequest, LeaveType]]:
        stmt = (
            select(LeaveRequest, LeaveType)
            .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
            .where(
                LeaveRequest.tenant_id == str(tenant_id),
                LeaveRequest.deleted_at.is_(None),
                LeaveRequest.status.in_(("pending", "approved")),
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= start_date,
            )
        )
        if employee_id:
            stmt = stmt.where(LeaveRequest.employee_id == str(employee_id))
        if branch_id or department_id:
            stmt = stmt.join(Employee, Employee.id == LeaveRequest.employee_id)
            if branch_id:
                stmt = stmt.where(Employee.branch_id == str(branch_id))
            if department_id:
                stmt = stmt.where(Employee.department_id == str(department_id))
        return list(self.db.execute(stmt))


class CompOffRequestRepository(TenantScopedRepository[CompOffRequest]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, CompOffRequest)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> tuple[list[CompOffRequest], int]:
        extra = []
        if employee_id:
            extra.append(CompOffRequest.employee_id == str(employee_id))
        if status:
            extra.append(CompOffRequest.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)


class HolidayRepository(BaseRepository[Holiday]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Holiday)

    def dates_in_range(self, tenant_id: UUID, start: date, end: date) -> list[date]:
        stmt = select(Holiday.holiday_date).where(
            Holiday.tenant_id == str(tenant_id),
            Holiday.holiday_date >= start,
            Holiday.holiday_date <= end,
            Holiday.deleted_at.is_(None),
            Holiday.is_active.is_(True),
        )
        return [row[0] for row in self.db.execute(stmt)]
