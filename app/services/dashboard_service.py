from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceDailySummary
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.payroll import PayrollRun
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.payroll_repository import PayrollRunRepository
from app.schemas.dashboard import DashboardStatsResponse


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.employee_repo = EmployeeRepository(db)
        self.run_repo = PayrollRunRepository(db)

    def get_stats(self, tenant_id: UUID) -> DashboardStatsResponse:
        total_employees = self._count_active_employees(tenant_id)
        attendance_today = self._attendance_today(tenant_id, total_employees)
        pending_leaves = self._pending_leave_count(tenant_id)
        payroll_status = self._latest_payroll_status(tenant_id)

        return DashboardStatsResponse(
            total_employees=total_employees,
            attendance_today=attendance_today,
            pending_leave_approvals=pending_leaves,
            payroll_run_status=payroll_status,
        )

    def _count_active_employees(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Employee).where(
            Employee.tenant_id == str(tenant_id),
            Employee.deleted_at.is_(None),
            Employee.is_active.is_(True),
        )
        return int(self.db.scalar(stmt) or 0)

    def _attendance_today(self, tenant_id: UUID, total_employees: int) -> dict:
        today = date.today()
        stmt = (
            select(AttendanceDailySummary.status, func.count())
            .where(
                AttendanceDailySummary.tenant_id == str(tenant_id),
                AttendanceDailySummary.attendance_date == today,
            )
            .group_by(AttendanceDailySummary.status)
        )
        rows = self.db.execute(stmt).all()
        if not rows:
            return {
                "date": today.isoformat(),
                "present": 0,
                "absent": 0,
                "on_leave": 0,
                "total_marked": 0,
                "total_employees": total_employees,
            }

        counts = {status: int(count) for status, count in rows}
        present = counts.get("present", 0) + counts.get("late", 0) + counts.get("half_day", 0)
        return {
            "date": today.isoformat(),
            "present": present,
            "absent": counts.get("absent", 0),
            "on_leave": counts.get("on_leave", 0),
            "total_marked": sum(counts.values()),
            "total_employees": total_employees,
            "by_status": counts,
        }

    def _pending_leave_count(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(LeaveRequest).where(
            LeaveRequest.tenant_id == str(tenant_id),
            LeaveRequest.status == "pending",
            LeaveRequest.deleted_at.is_(None),
        )
        return int(self.db.scalar(stmt) or 0)

    def _latest_payroll_status(self, tenant_id: UUID) -> Optional[dict]:
        runs = self.run_repo.list_runs(tenant_id, limit=1)
        if not runs:
            return None
        run = runs[0]
        return {
            "id": str(run.id),
            "month": run.month,
            "year": run.year,
            "status": run.status,
            "employee_count": run.employee_count,
            "total_net": float(run.total_net),
            "run_date": run.run_date.isoformat() if run.run_date else None,
        }
