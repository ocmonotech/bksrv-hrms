from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select

from app.models.timesheets import TimesheetEntry, TimesheetProject
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class TimesheetProjectRepository(TenantScopedRepository[TimesheetProject]):
    def __init__(self, db) -> None:
        super().__init__(db, TimesheetProject, search_fields=("name", "code", "client_name"))


class TimesheetEntryRepository(TenantScopedRepository[TimesheetEntry]):
    def __init__(self, db) -> None:
        super().__init__(db, TimesheetEntry)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> tuple[list[TimesheetEntry], int]:
        stmt = select(TimesheetEntry).where(
            TimesheetEntry.tenant_id == str(tenant_id),
            TimesheetEntry.deleted_at.is_(None),
        )
        if employee_id:
            stmt = stmt.where(TimesheetEntry.employee_id == str(employee_id))
        if project_id:
            stmt = stmt.where(TimesheetEntry.project_id == str(project_id))
        if status:
            stmt = stmt.where(TimesheetEntry.status == status)
        if date_from:
            stmt = stmt.where(TimesheetEntry.entry_date >= date_from)
        if date_to:
            stmt = stmt.where(TimesheetEntry.entry_date <= date_to)
        stmt = stmt.order_by(TimesheetEntry.entry_date.desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0
        offset = (page - 1) * page_size
        items = list(self.db.scalars(stmt.offset(offset).limit(page_size)).all())
        return items, total

    def sum_hours(
        self,
        tenant_id: UUID,
        *,
        employee_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[str] = None,
    ) -> float:
        stmt = select(func.coalesce(func.sum(TimesheetEntry.hours), 0)).where(
            TimesheetEntry.tenant_id == str(tenant_id),
            TimesheetEntry.deleted_at.is_(None),
        )
        if employee_id:
            stmt = stmt.where(TimesheetEntry.employee_id == str(employee_id))
        if date_from:
            stmt = stmt.where(TimesheetEntry.entry_date >= date_from)
        if date_to:
            stmt = stmt.where(TimesheetEntry.entry_date <= date_to)
        if status:
            stmt = stmt.where(TimesheetEntry.status == status)
        return float(self.db.scalar(stmt) or 0)

    def count_by_status(self, tenant_id: UUID, status: str, *, employee_id: Optional[UUID] = None) -> int:
        stmt = select(func.count()).where(
            TimesheetEntry.tenant_id == str(tenant_id),
            TimesheetEntry.status == status,
            TimesheetEntry.deleted_at.is_(None),
        )
        if employee_id:
            stmt = stmt.where(TimesheetEntry.employee_id == str(employee_id))
        return int(self.db.scalar(stmt) or 0)
