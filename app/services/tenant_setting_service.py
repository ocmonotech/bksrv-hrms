from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_setup import Department
from app.models.employee import Employee
from app.repositories.tenant_setting_repository import TenantSettingRepository
from app.schemas.company_settings import (
    CareerPageResponse,
    CareerPageUpdate,
    ManagerAssignmentItem,
    ManagerAssignmentsResponse,
    ManagerAssignmentsUpdate,
    WeeklyOffResponse,
    WeeklyOffUpdate,
)


DEFAULT_WEEKLY_OFF = {"days": ["saturday", "sunday"]}
DEFAULT_CAREER_PAGE = {
    "enabled": True,
    "headline": "Join Our Team",
    "description": "Explore open roles and grow your career with us.",
    "banner_url": None,
    "show_openings": True,
}


class TenantSettingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = TenantSettingRepository(db)

    def get_weekly_off(self, tenant_id: UUID) -> WeeklyOffResponse:
        value = self.repo.get_value(tenant_id, "weekly_off", DEFAULT_WEEKLY_OFF)
        days = value.get("days", DEFAULT_WEEKLY_OFF["days"]) if isinstance(value, dict) else DEFAULT_WEEKLY_OFF["days"]
        return WeeklyOffResponse(days=days)

    def update_weekly_off(self, tenant_id: UUID, payload: WeeklyOffUpdate) -> WeeklyOffResponse:
        entity = self.repo.upsert(tenant_id, "weekly_off", {"days": payload.days})
        self.db.commit()
        self.db.refresh(entity)
        return WeeklyOffResponse(days=payload.days)

    def get_manager_assignments(self, tenant_id: UUID) -> ManagerAssignmentsResponse:
        stored = self.repo.get_value(tenant_id, "manager_assignments")
        if isinstance(stored, dict) and stored.get("assignments"):
            items = [ManagerAssignmentItem(**item) for item in stored["assignments"]]
            return ManagerAssignmentsResponse(assignments=items, source="stored")

        departments = list(
            self.db.scalars(
                select(Department).where(
                    Department.tenant_id == str(tenant_id),
                    Department.deleted_at.is_(None),
                    Department.is_active.is_(True),
                )
            ).all()
        )
        employees = list(
            self.db.scalars(
                select(Employee).where(
                    Employee.tenant_id == str(tenant_id),
                    Employee.deleted_at.is_(None),
                    Employee.status == "active",
                    Employee.reporting_manager_id.isnot(None),
                )
            ).all()
        )

        by_dept: dict[str, dict[str, Any]] = {}
        for dept in departments:
            by_dept[str(dept.id)] = {
                "department_id": UUID(dept.id),
                "department_name": dept.name,
                "department_code": dept.code,
                "manager_employee_id": None,
                "manager_name": dept.head_name,
                "direct_reports_count": 0,
            }

        for emp in employees:
            dept_id = str(emp.department_id) if emp.department_id else None
            if dept_id and dept_id in by_dept and by_dept[dept_id]["manager_employee_id"] is None:
                manager = self.db.get(Employee, str(emp.reporting_manager_id))
                if manager:
                    by_dept[dept_id]["manager_employee_id"] = UUID(manager.id)
                    by_dept[dept_id]["manager_name"] = f"{manager.first_name} {manager.last_name}"

        for emp in employees:
            dept_id = str(emp.department_id) if emp.department_id else None
            if dept_id and dept_id in by_dept:
                manager_id = by_dept[dept_id].get("manager_employee_id")
                if manager_id and str(emp.reporting_manager_id) == str(manager_id):
                    by_dept[dept_id]["direct_reports_count"] += 1

        items = [ManagerAssignmentItem(**row) for row in by_dept.values()]
        return ManagerAssignmentsResponse(assignments=items, source="derived")

    def update_manager_assignments(
        self, tenant_id: UUID, payload: ManagerAssignmentsUpdate
    ) -> ManagerAssignmentsResponse:
        data = {"assignments": [item.model_dump(mode="json") for item in payload.assignments]}
        self.repo.upsert(tenant_id, "manager_assignments", data)
        self.db.commit()
        return ManagerAssignmentsResponse(assignments=payload.assignments, source="stored")

    def get_career_page(self, tenant_id: UUID) -> CareerPageResponse:
        value = self.repo.get_value(tenant_id, "career_page", DEFAULT_CAREER_PAGE)
        if not isinstance(value, dict):
            value = DEFAULT_CAREER_PAGE
        merged = {**DEFAULT_CAREER_PAGE, **value}
        return CareerPageResponse(**merged)

    def update_career_page(self, tenant_id: UUID, payload: CareerPageUpdate) -> CareerPageResponse:
        current = self.get_career_page(tenant_id).model_dump()
        updates = payload.model_dump(exclude_unset=True)
        current.update(updates)
        self.repo.upsert(tenant_id, "career_page", current)
        self.db.commit()
        return CareerPageResponse(**current)
