from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.training import TrainingCourse, TrainingEnrollment
from app.repositories.training_repository import TrainingCourseRepository, TrainingEnrollmentRepository
from app.schemas.common import PaginatedResponse
from app.schemas.training import (
    TrainingCourseCreate,
    TrainingCourseResponse,
    TrainingCourseUpdate,
    TrainingDashboardStats,
    TrainingEnrollmentCreate,
    TrainingEnrollmentResponse,
    TrainingEnrollmentUpdate,
)
from app.services.audit_service import AuditService
from app.services.company_setup.base import _coerce_payload
from app.utils.pagination import total_pages


class TrainingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.course_repo = TrainingCourseRepository(db)
        self.enrollment_repo = TrainingEnrollmentRepository(db)
        self.audit = AuditService(db)

    def _log(self, action: str, tenant_id: UUID, actor_id: UUID, resource_id: str, meta: Optional[dict]) -> None:
        self.audit.log(
            action,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="training",
            resource_id=resource_id,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )

    def get_dashboard_stats(self, tenant_id: UUID) -> TrainingDashboardStats:
        courses, total_courses = self.course_repo.list_paginated(tenant_id, page=1, page_size=1, is_active=True)
        active = self.enrollment_repo.count_by_status(tenant_id, "assigned") + self.enrollment_repo.count_by_status(
            tenant_id, "in_progress"
        )
        completed = self.enrollment_repo.count_by_status(tenant_id, "completed")
        total_enrollments = active + completed + self.enrollment_repo.count_by_status(tenant_id, "overdue")
        completion_rate = (completed / total_enrollments * 100) if total_enrollments else 0.0
        return TrainingDashboardStats(
            total_courses=total_courses,
            active_enrollments=active,
            completion_rate_pct=round(completion_rate, 1),
            overdue_count=self.enrollment_repo.count_by_status(tenant_id, "overdue"),
        )

    def create_course(
        self, tenant_id: UUID, payload: TrainingCourseCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TrainingCourseResponse:
        code = payload.code.upper()
        if self.course_repo.get_by_code(tenant_id, code):
            raise ConflictError(f"Course '{code}' already exists")
        data = _coerce_payload(payload.model_dump())
        entity = TrainingCourse(
            tenant_id=str(tenant_id),
            code=code,
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **{k: v for k, v in data.items() if k != "code"},
        )
        self.course_repo.add(entity)
        self._log("training.course.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TrainingCourseResponse.model_validate(entity)

    def list_courses(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20, search: Optional[str] = None, is_active: Optional[bool] = None
    ) -> PaginatedResponse[TrainingCourseResponse]:
        items, total = self.course_repo.list_paginated(tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)
        return PaginatedResponse(
            data=[TrainingCourseResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_course(
        self, tenant_id: UUID, course_id: UUID, payload: TrainingCourseUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TrainingCourseResponse:
        entity = self.course_repo.get_by_id(course_id, tenant_id)
        if not entity:
            raise NotFoundError("Course not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("training.course.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TrainingCourseResponse.model_validate(entity)

    def create_enrollment(
        self, tenant_id: UUID, payload: TrainingEnrollmentCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TrainingEnrollmentResponse:
        if not self.course_repo.get_by_id(payload.course_id, tenant_id):
            raise NotFoundError("Course not found")
        if self.enrollment_repo.get_by_course_employee(tenant_id, payload.course_id, payload.employee_id):
            raise ConflictError("Employee already enrolled in this course")
        data = _coerce_payload(payload.model_dump())
        entity = TrainingEnrollment(
            tenant_id=str(tenant_id),
            status="assigned",
            progress_pct=0,
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.enrollment_repo.add(entity)
        self._log("training.enrollment.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TrainingEnrollmentResponse.model_validate(entity)

    def list_enrollments(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        course_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[TrainingEnrollmentResponse]:
        items, total = self.enrollment_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, employee_id=employee_id, course_id=course_id, status=status
        )
        return PaginatedResponse(
            data=[TrainingEnrollmentResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_enrollment(
        self, tenant_id: UUID, enrollment_id: UUID, payload: TrainingEnrollmentUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TrainingEnrollmentResponse:
        entity = self.enrollment_repo.get_by_id(enrollment_id, tenant_id)
        if not entity:
            raise NotFoundError("Enrollment not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        if payload.status == "completed" or (payload.progress_pct is not None and payload.progress_pct >= 100):
            entity.status = "completed"
            entity.progress_pct = 100
            entity.completed_at = datetime.now(timezone.utc)
        entity.updated_by = str(actor_id)
        self._log("training.enrollment.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TrainingEnrollmentResponse.model_validate(entity)
