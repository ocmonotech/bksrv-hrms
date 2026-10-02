from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select

from app.models.training import TrainingCourse, TrainingEnrollment
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class TrainingCourseRepository(TenantScopedRepository[TrainingCourse]):
    def __init__(self, db) -> None:
        super().__init__(db, TrainingCourse, search_fields=("title", "code", "category"))


class TrainingEnrollmentRepository(TenantScopedRepository[TrainingEnrollment]):
    def __init__(self, db) -> None:
        super().__init__(db, TrainingEnrollment)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        course_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> tuple[list[TrainingEnrollment], int]:
        stmt = select(TrainingEnrollment).where(
            TrainingEnrollment.tenant_id == str(tenant_id),
            TrainingEnrollment.deleted_at.is_(None),
        )
        if employee_id:
            stmt = stmt.where(TrainingEnrollment.employee_id == str(employee_id))
        if course_id:
            stmt = stmt.where(TrainingEnrollment.course_id == str(course_id))
        if status:
            stmt = stmt.where(TrainingEnrollment.status == status)
        stmt = stmt.order_by(TrainingEnrollment.created_at.desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0
        offset = (page - 1) * page_size
        items = list(self.db.scalars(stmt.offset(offset).limit(page_size)).all())
        return items, total

    def get_by_course_employee(self, tenant_id: UUID, course_id: UUID, employee_id: UUID) -> Optional[TrainingEnrollment]:
        stmt = select(TrainingEnrollment).where(
            TrainingEnrollment.tenant_id == str(tenant_id),
            TrainingEnrollment.course_id == str(course_id),
            TrainingEnrollment.employee_id == str(employee_id),
            TrainingEnrollment.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def count_by_status(self, tenant_id: UUID, status: str) -> int:
        stmt = select(func.count()).where(
            TrainingEnrollment.tenant_id == str(tenant_id),
            TrainingEnrollment.status == status,
            TrainingEnrollment.deleted_at.is_(None),
        )
        return int(self.db.scalar(stmt) or 0)

    def avg_completion_pct(self, tenant_id: UUID) -> float:
        stmt = select(func.coalesce(func.avg(TrainingEnrollment.progress_pct), 0)).where(
            TrainingEnrollment.tenant_id == str(tenant_id),
            TrainingEnrollment.deleted_at.is_(None),
        )
        return float(self.db.scalar(stmt) or 0)
