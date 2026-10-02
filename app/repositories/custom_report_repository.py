from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRegularization
from app.models.employee import Employee
from app.models.helpdesk import Ticket
from app.models.leave import LeaveRequest
from app.models.reports import CustomReport
from app.repositories.base import BaseRepository


class CustomReportRepository(BaseRepository[CustomReport]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, CustomReport)

    def list_for_tenant(self, tenant_id: UUID) -> list[CustomReport]:
        stmt = (
            select(CustomReport)
            .where(CustomReport.tenant_id == str(tenant_id))
            .order_by(CustomReport.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_by_id(self, report_id: UUID, tenant_id: UUID) -> Optional[CustomReport]:
        stmt = select(CustomReport).where(
            CustomReport.id == str(report_id),
            CustomReport.tenant_id == str(tenant_id),
        )
        return self.db.scalar(stmt)

    def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(CustomReport).where(CustomReport.tenant_id == str(tenant_id))
        return int(self.db.scalar(stmt) or 0)

    def count_pending_regularizations(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(AttendanceRegularization).where(
            AttendanceRegularization.tenant_id == str(tenant_id),
            AttendanceRegularization.status == "pending",
            AttendanceRegularization.deleted_at.is_(None),
        )
        return int(self.db.scalar(stmt) or 0)

    def count_active_employees(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Employee).where(
            Employee.tenant_id == str(tenant_id),
            Employee.deleted_at.is_(None),
            Employee.status == "active",
        )
        return int(self.db.scalar(stmt) or 0)

    def count_on_leave_today(self, tenant_id: UUID) -> int:
        from datetime import date

        today = date.today()
        stmt = select(func.count(func.distinct(LeaveRequest.employee_id))).where(
            LeaveRequest.tenant_id == str(tenant_id),
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
            LeaveRequest.deleted_at.is_(None),
        )
        return int(self.db.scalar(stmt) or 0)

    def count_open_tickets(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Ticket).where(
            Ticket.tenant_id == str(tenant_id),
            Ticket.status.in_(["open", "in_progress", "waiting"]),
            Ticket.deleted_at.is_(None),
        )
        return int(self.db.scalar(stmt) or 0)

    @staticmethod
    def serialize_json_fields(entity: CustomReport) -> dict:
        return {
            "modules": json.loads(entity.modules or "[]"),
            "columns": json.loads(entity.columns or "[]"),
            "filters": json.loads(entity.filters or "{}"),
        }
