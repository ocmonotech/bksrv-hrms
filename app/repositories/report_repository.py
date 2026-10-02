from __future__ import annotations

from datetime import date
from math import ceil
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceDailySummary
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.payroll import PayrollEmployee, PayrollRun
from app.models.performance import Goal
from app.models.recruitment import Candidate, JobOpening


def _paginate_orm(db: Session, stmt, *, page: int, page_size: int):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 500)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(db.scalar(count_stmt) or 0)
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return items, total


def _paginate_rows(db: Session, stmt, *, page: int, page_size: int):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 500)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(db.scalar(count_stmt) or 0)
    items = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return items, total


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _employee_filters(
        self,
        tenant_id: UUID,
        *,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
    ) -> list:
        conditions = [Employee.tenant_id == str(tenant_id), Employee.deleted_at.is_(None)]
        if branch_id:
            conditions.append(Employee.branch_id == str(branch_id))
        if department_id:
            conditions.append(Employee.department_id == str(department_id))
        if employee_id:
            conditions.append(Employee.id == str(employee_id))
        return conditions

    def headcount_summary(
        self,
        tenant_id: UUID,
        *,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        conditions = self._employee_filters(
            tenant_id, branch_id=branch_id, department_id=department_id, employee_id=employee_id
        )
        stmt = (
            select(
                Employee.department_id,
                Employee.branch_id,
                Employee.status,
                func.count(Employee.id).label("count"),
            )
            .where(*conditions)
            .group_by(Employee.department_id, Employee.branch_id, Employee.status)
            .order_by(func.count(Employee.id).desc())
        )
        items, total = _paginate_rows(self.db, stmt, page=page, page_size=page_size)
        rows = [
            {
                "department_id": r.department_id,
                "branch_id": r.branch_id,
                "status": r.status,
                "count": r.count,
            }
            for r in items
        ]
        total_employees = self.db.scalar(select(func.count()).select_from(Employee).where(*conditions)) or 0
        summary = {"total_employees": int(total_employees), "group_count": total}
        return rows, total, summary

    def attendance_report(
        self,
        tenant_id: UUID,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        conditions = [AttendanceDailySummary.tenant_id == str(tenant_id)]
        if date_from:
            conditions.append(AttendanceDailySummary.attendance_date >= date_from)
        if date_to:
            conditions.append(AttendanceDailySummary.attendance_date <= date_to)
        if employee_id:
            conditions.append(AttendanceDailySummary.employee_id == str(employee_id))

        stmt = select(AttendanceDailySummary).where(*conditions)
        if branch_id or department_id:
            emp_conditions = [Employee.tenant_id == str(tenant_id), Employee.deleted_at.is_(None)]
            if branch_id:
                emp_conditions.append(Employee.branch_id == str(branch_id))
            if department_id:
                emp_conditions.append(Employee.department_id == str(department_id))
            stmt = (
                select(AttendanceDailySummary)
                .join(Employee, Employee.id == AttendanceDailySummary.employee_id)
                .where(*conditions, *emp_conditions)
            )
        stmt = stmt.order_by(AttendanceDailySummary.attendance_date.desc())

        items, total = _paginate_orm(self.db, stmt, page=page, page_size=page_size)
        rows = [
            {
                "employee_id": str(r.employee_id),
                "attendance_date": str(r.attendance_date),
                "day_status": r.status,
                "worked_minutes": r.total_work_minutes,
                "late_minutes": r.late_minutes,
                "is_lop": r.is_lop,
            }
            for r in items
        ]
        present_count = sum(1 for r in rows if r["day_status"] in ("present", "late", "half_day"))
        summary = {"total_records": total, "present_in_page": present_count}
        return rows, total, summary

    def leave_report(
        self,
        tenant_id: UUID,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        conditions = [LeaveRequest.tenant_id == str(tenant_id), LeaveRequest.deleted_at.is_(None)]
        if date_from:
            conditions.append(LeaveRequest.start_date >= date_from)
        if date_to:
            conditions.append(LeaveRequest.end_date <= date_to)
        if employee_id:
            conditions.append(LeaveRequest.employee_id == str(employee_id))

        stmt = select(LeaveRequest)
        if branch_id or department_id:
            emp_conditions = [Employee.tenant_id == str(tenant_id), Employee.deleted_at.is_(None)]
            if branch_id:
                emp_conditions.append(Employee.branch_id == str(branch_id))
            if department_id:
                emp_conditions.append(Employee.department_id == str(department_id))
            stmt = (
                select(LeaveRequest)
                .join(Employee, Employee.id == LeaveRequest.employee_id)
                .where(*conditions, *emp_conditions)
            )
        else:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(LeaveRequest.start_date.desc())

        items, total = _paginate_orm(self.db, stmt, page=page, page_size=page_size)
        rows = [
            {
                "id": str(r.id),
                "employee_id": str(r.employee_id),
                "start_date": str(r.start_date),
                "end_date": str(r.end_date),
                "total_days": str(r.total_days),
                "status": r.status,
                "lop_days": str(r.lop_days),
            }
            for r in items
        ]
        approved = sum(1 for r in rows if r["status"] == "approved")
        summary = {"total_records": total, "approved_in_page": approved}
        return rows, total, summary

    def payroll_report(
        self,
        tenant_id: UUID,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        conditions = [PayrollRun.tenant_id == str(tenant_id), PayrollRun.deleted_at.is_(None)]
        stmt = select(PayrollRun).where(*conditions).order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
        runs, total = _paginate_orm(self.db, stmt, page=page, page_size=page_size)

        rows = []
        for run in runs:
            emp_stmt = select(PayrollEmployee).where(PayrollEmployee.payroll_run_id == str(run.id))
            if employee_id:
                emp_stmt = emp_stmt.where(PayrollEmployee.employee_id == str(employee_id))
            employees = list(self.db.scalars(emp_stmt).all())
            if branch_id or department_id:
                filtered = []
                for pe in employees:
                    emp = self.db.get(Employee, str(pe.employee_id))
                    if not emp:
                        continue
                    if branch_id and emp.branch_id != str(branch_id):
                        continue
                    if department_id and emp.department_id != str(department_id):
                        continue
                    filtered.append(pe)
                employees = filtered
            rows.append(
                {
                    "payroll_run_id": str(run.id),
                    "month": run.month,
                    "year": run.year,
                    "status": run.status,
                    "total_gross": str(run.total_gross),
                    "total_net": str(run.total_net),
                    "employee_count": len(employees),
                }
            )
        summary = {
            "total_runs": total,
            "total_gross": str(sum(run.total_gross or 0 for run in runs)),
            "total_net": str(sum(run.total_net or 0 for run in runs)),
        }
        return rows, total, summary

    def recruitment_report(
        self,
        tenant_id: UUID,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        conditions = [JobOpening.tenant_id == str(tenant_id), JobOpening.deleted_at.is_(None)]
        stmt = select(JobOpening).where(*conditions).order_by(JobOpening.created_at.desc())
        jobs, total = _paginate_orm(self.db, stmt, page=page, page_size=page_size)

        rows = []
        for job in jobs:
            cand_stmt = select(func.count()).select_from(Candidate).where(
                Candidate.job_opening_id == str(job.id),
                Candidate.tenant_id == str(tenant_id),
                Candidate.deleted_at.is_(None),
            )
            candidate_count = int(self.db.scalar(cand_stmt) or 0)
            rows.append(
                {
                    "job_id": str(job.id),
                    "title": job.title,
                    "code": job.code,
                    "status": job.status,
                    "candidate_count": candidate_count,
                }
            )
        summary = {"total_jobs": total, "open_jobs": sum(1 for j in jobs if j.status == "open")}
        return rows, total, summary

    def performance_report(
        self,
        tenant_id: UUID,
        *,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        conditions = [Goal.tenant_id == str(tenant_id), Goal.deleted_at.is_(None)]
        if employee_id:
            conditions.append(Goal.employee_id == str(employee_id))

        stmt = select(Goal)
        if branch_id or department_id:
            emp_conditions = [Employee.tenant_id == str(tenant_id), Employee.deleted_at.is_(None)]
            if branch_id:
                emp_conditions.append(Employee.branch_id == str(branch_id))
            if department_id:
                emp_conditions.append(Employee.department_id == str(department_id))
            stmt = select(Goal).join(Employee, Employee.id == Goal.employee_id).where(*conditions, *emp_conditions)
        else:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(Goal.created_at.desc())

        goals, total = _paginate_orm(self.db, stmt, page=page, page_size=page_size)
        rows = [
            {
                "goal_id": str(g.id),
                "employee_id": str(g.employee_id),
                "title": g.title,
                "status": g.status,
                "progress": str(g.progress),
            }
            for g in goals
        ]
        completed = sum(1 for g in goals if g.status == "completed")
        summary = {"total_goals": total, "completed_in_page": completed}
        return rows, total, summary

    def attrition_report(
        self,
        tenant_id: UUID,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        conditions = [
            Employee.tenant_id == str(tenant_id),
            Employee.deleted_at.is_(None),
            Employee.status.in_(["terminated", "inactive"]),
        ]
        if date_from:
            conditions.append(Employee.exit_date >= date_from)
        if date_to:
            conditions.append(Employee.exit_date <= date_to)
        if branch_id:
            conditions.append(Employee.branch_id == str(branch_id))
        if department_id:
            conditions.append(Employee.department_id == str(department_id))

        stmt = select(Employee).where(*conditions).order_by(Employee.exit_date.desc())
        items, total = _paginate_orm(self.db, stmt, page=page, page_size=page_size)
        rows = [
            {
                "employee_id": str(e.id),
                "employee_code": e.employee_code,
                "name": f"{e.first_name} {e.last_name}",
                "department_id": str(e.department_id) if e.department_id else None,
                "branch_id": str(e.branch_id) if e.branch_id else None,
                "exit_date": str(e.exit_date) if e.exit_date else None,
                "status": e.status,
            }
            for e in items
        ]
        active_count = self.db.scalar(
            select(func.count()).select_from(Employee).where(
                Employee.tenant_id == str(tenant_id),
                Employee.deleted_at.is_(None),
                Employee.status == "active",
            )
        ) or 0
        summary = {"exits": total, "active_employees": int(active_count)}
        return rows, total, summary
