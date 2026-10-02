from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.employee import Employee
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class EmployeeRepository(TenantScopedRepository[Employee]):
    search_fields = ("first_name", "last_name", "email", "employee_code")

    def __init__(self, db: Session) -> None:
        super().__init__(db, Employee, search_fields=self.search_fields)

    def get_profile(self, employee_id: UUID, tenant_id: UUID) -> Optional[Employee]:
        stmt = (
            select(Employee)
            .options(
                joinedload(Employee.personal_detail),
                joinedload(Employee.job_detail),
                joinedload(Employee.bank_detail),
                joinedload(Employee.salary_detail),
                joinedload(Employee.statutory_detail),
                joinedload(Employee.family_members),
                joinedload(Employee.education),
                joinedload(Employee.experience),
                joinedload(Employee.documents),
            )
            .where(
                Employee.id == str(employee_id),
                Employee.tenant_id == str(tenant_id),
                Employee.deleted_at.is_(None),
            )
        )
        return self.db.scalar(stmt)

    def get_by_email(self, tenant_id: UUID, email: str) -> Optional[Employee]:
        stmt = select(Employee).where(
            Employee.tenant_id == str(tenant_id),
            Employee.email == email.lower(),
            Employee.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def get_by_code(self, tenant_id: UUID, code: str) -> Optional[Employee]:
        stmt = select(Employee).where(
            Employee.tenant_id == str(tenant_id),
            Employee.employee_code == code.upper(),
            Employee.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        status: Optional[str] = None,
        employment_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[Employee], int]:
        extra = []
        if branch_id:
            extra.append(Employee.branch_id == str(branch_id))
        if department_id:
            extra.append(Employee.department_id == str(department_id))
        if status:
            extra.append(Employee.status == status)
        if employment_type:
            extra.append(Employee.employment_type == employment_type)
        return self.list_paginated(
            tenant_id,
            page=page,
            page_size=page_size,
            search=search,
            is_active=is_active,
            extra_filters=extra or None,
        )

    def next_employee_code(self, tenant_id: UUID) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"EMP{year}"
        stmt = select(func.count()).select_from(Employee).where(
            Employee.tenant_id == str(tenant_id),
            Employee.employee_code.like(f"{prefix}%"),
        )
        count = self.db.scalar(stmt) or 0
        return f"{prefix}{count + 1:05d}"
