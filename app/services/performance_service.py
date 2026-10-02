from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.performance import Appraisal, Feedback360, Goal, ManagerReview, OKR, ReviewCycle, SelfReview
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.performance_repository import (
    AppraisalRepository,
    Feedback360Repository,
    GoalRepository,
    ManagerReviewRepository,
    OKRRepository,
    ReviewCycleRepository,
    SelfReviewRepository,
)
from app.schemas.common import PaginatedResponse
from app.schemas.performance import (
    AppraisalApproveRequest,
    AppraisalCreate,
    AppraisalResponse,
    AppraisalUpdate,
    GoalCreate,
    GoalResponse,
    GoalUpdate,
    KeyResultItem,
    OKRCreate,
    OKRResponse,
    OKRUpdate,
    ReviewCreate,
    ReviewCycleCreate,
    ReviewCycleResponse,
    ReviewCycleUpdate,
    ReviewResponse,
    ReviewUpdate,
)
from app.services.audit_service import AuditService
from app.services.company_setup.base import _coerce_payload
from app.utils.pagination import total_pages


class PerformanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.goal_repo = GoalRepository(db)
        self.okr_repo = OKRRepository(db)
        self.cycle_repo = ReviewCycleRepository(db)
        self.self_repo = SelfReviewRepository(db)
        self.manager_repo = ManagerReviewRepository(db)
        self.feedback360_repo = Feedback360Repository(db)
        self.appraisal_repo = AppraisalRepository(db)
        self.employee_repo = EmployeeRepository(db)
        self.audit = AuditService(db)

    def create_goal(
        self, tenant_id: UUID, payload: GoalCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> GoalResponse:
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        data = _coerce_payload(payload.model_dump())
        entity = Goal(
            tenant_id=str(tenant_id),
            status="draft",
            progress=0,
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.goal_repo.add(entity)
        self._log("performance.goal.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return GoalResponse.model_validate(entity)

    def list_goals(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[GoalResponse]:
        items, total = self.goal_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, employee_id=employee_id, status=status
        )
        return PaginatedResponse(
            data=[GoalResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_goal(
        self, tenant_id: UUID, goal_id: UUID, payload: GoalUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> GoalResponse:
        entity = self.goal_repo.get_by_id(goal_id, tenant_id)
        if not entity:
            raise NotFoundError("Goal not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("performance.goal.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return GoalResponse.model_validate(entity)

    def create_okr(
        self, tenant_id: UUID, payload: OKRCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> OKRResponse:
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        entity = OKR(
            tenant_id=str(tenant_id),
            employee_id=str(payload.employee_id),
            objective=payload.objective,
            key_results_json=json.dumps([kr.model_dump(mode="json") for kr in payload.key_results]),
            quarter=payload.quarter,
            year=payload.year,
            status="draft",
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.okr_repo.add(entity)
        self._log("performance.okr.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return self._okr_response(entity)

    def list_okrs(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        year: Optional[int] = None,
        quarter: Optional[int] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[OKRResponse]:
        items, total = self.okr_repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            employee_id=employee_id,
            year=year,
            quarter=quarter,
            status=status,
        )
        return PaginatedResponse(
            data=[self._okr_response(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_okr(
        self, tenant_id: UUID, okr_id: UUID, payload: OKRUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> OKRResponse:
        entity = self.okr_repo.get_by_id(okr_id, tenant_id)
        if not entity:
            raise NotFoundError("OKR not found")
        data = payload.model_dump(exclude_unset=True)
        if "key_results" in data and data["key_results"] is not None:
            entity.key_results_json = json.dumps(
                [kr.model_dump(mode="json") if hasattr(kr, "model_dump") else kr for kr in data["key_results"]]
            )
            del data["key_results"]
        for key, value in data.items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("performance.okr.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return self._okr_response(entity)

    def create_review_cycle(
        self, tenant_id: UUID, payload: ReviewCycleCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> ReviewCycleResponse:
        if self.cycle_repo.get_by_code(tenant_id, payload.code.upper()):
            raise ConflictError(f"Review cycle '{payload.code}' already exists")
        entity = ReviewCycle(
            tenant_id=str(tenant_id),
            code=payload.code.upper(),
            name=payload.name,
            cycle_type=payload.cycle_type,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status="draft",
            is_active=payload.is_active,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.cycle_repo.add(entity)
        self._log("performance.cycle.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return ReviewCycleResponse.model_validate(entity)

    def list_review_cycles(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[ReviewCycleResponse]:
        items, total = self.cycle_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, status=status, is_active=is_active
        )
        return PaginatedResponse(
            data=[ReviewCycleResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_review_cycle(
        self, tenant_id: UUID, cycle_id: UUID, payload: ReviewCycleUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> ReviewCycleResponse:
        entity = self.cycle_repo.get_by_id(cycle_id, tenant_id)
        if not entity:
            raise NotFoundError("Review cycle not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("performance.cycle.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return ReviewCycleResponse.model_validate(entity)

    def create_review(
        self, tenant_id: UUID, payload: ReviewCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> ReviewResponse:
        if not self.cycle_repo.get_by_id(payload.review_cycle_id, tenant_id):
            raise NotFoundError("Review cycle not found")
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")

        if payload.review_type == "self":
            entity = SelfReview(
                tenant_id=str(tenant_id),
                review_cycle_id=str(payload.review_cycle_id),
                employee_id=str(payload.employee_id),
                responses_json=json.dumps(payload.responses or {}),
                rating=payload.rating,
                status="draft",
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.self_repo.add(entity)
            review_type = "self"
        elif payload.review_type == "manager":
            entity = ManagerReview(
                tenant_id=str(tenant_id),
                review_cycle_id=str(payload.review_cycle_id),
                employee_id=str(payload.employee_id),
                manager_id=str(payload.manager_id) if payload.manager_id else None,
                rating=payload.rating,
                feedback=payload.feedback,
                status="draft",
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.manager_repo.add(entity)
            review_type = "manager"
        elif payload.review_type == "360":
            if not payload.reviewer_id:
                raise ValidationError("reviewer_id is required for 360 feedback")
            entity = Feedback360(
                tenant_id=str(tenant_id),
                review_cycle_id=str(payload.review_cycle_id),
                employee_id=str(payload.employee_id),
                reviewer_id=str(payload.reviewer_id),
                relationship=payload.relationship or "peer",
                rating=payload.rating,
                feedback=payload.feedback,
                status="pending",
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.feedback360_repo.add(entity)
            review_type = "360"
        else:
            raise ValidationError("Invalid review_type")

        self._log(f"performance.review.{review_type}.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return self._review_response(entity, review_type)

    def list_reviews(
        self,
        tenant_id: UUID,
        *,
        review_type: str,
        page: int = 1,
        page_size: int = 20,
        review_cycle_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[ReviewResponse]:
        if review_type == "self":
            extra = []
            if review_cycle_id:
                extra.append(SelfReview.review_cycle_id == str(review_cycle_id))
            if employee_id:
                extra.append(SelfReview.employee_id == str(employee_id))
            if status:
                extra.append(SelfReview.status == status)
            items, total = self.self_repo.list_paginated(
                tenant_id, page=page, page_size=page_size, extra_filters=extra or None
            )
            data = [self._review_response(i, "self") for i in items]
        elif review_type == "manager":
            extra = []
            if review_cycle_id:
                extra.append(ManagerReview.review_cycle_id == str(review_cycle_id))
            if employee_id:
                extra.append(ManagerReview.employee_id == str(employee_id))
            if status:
                extra.append(ManagerReview.status == status)
            items, total = self.manager_repo.list_paginated(
                tenant_id, page=page, page_size=page_size, extra_filters=extra or None
            )
            data = [self._review_response(i, "manager") for i in items]
        elif review_type == "360":
            extra = []
            if review_cycle_id:
                extra.append(Feedback360.review_cycle_id == str(review_cycle_id))
            if employee_id:
                extra.append(Feedback360.employee_id == str(employee_id))
            if status:
                extra.append(Feedback360.status == status)
            items, total = self.feedback360_repo.list_paginated(
                tenant_id, page=page, page_size=page_size, extra_filters=extra or None
            )
            data = [self._review_response(i, "360") for i in items]
        else:
            raise ValidationError("review_type must be self, manager, or 360")

        return PaginatedResponse(
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_review(
        self,
        tenant_id: UUID,
        review_id: UUID,
        review_type: str,
        payload: ReviewUpdate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> ReviewResponse:
        repo_map = {"self": self.self_repo, "manager": self.manager_repo, "360": self.feedback360_repo}
        repo = repo_map.get(review_type)
        if not repo:
            raise ValidationError("Invalid review_type")
        entity = repo.get_by_id(review_id, tenant_id)
        if not entity:
            raise NotFoundError("Review not found")

        data = payload.model_dump(exclude_unset=True)
        if review_type == "self" and "responses" in data:
            entity.responses_json = json.dumps(data.pop("responses") or {})
        if data.get("status") == "submitted":
            if review_type == "self":
                entity.submitted_at = datetime.now(timezone.utc)
            elif review_type == "360":
                entity.submitted_at = datetime.now(timezone.utc)
        for key, value in data.items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log(f"performance.review.{review_type}.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return self._review_response(entity, review_type)

    def create_appraisal(
        self, tenant_id: UUID, payload: AppraisalCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> AppraisalResponse:
        if not self.cycle_repo.get_by_id(payload.review_cycle_id, tenant_id):
            raise NotFoundError("Review cycle not found")
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        data = _coerce_payload(payload.model_dump())
        entity = Appraisal(
            tenant_id=str(tenant_id),
            status="draft",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.appraisal_repo.add(entity)
        self._log("performance.appraisal.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return AppraisalResponse.model_validate(entity)

    def list_appraisals(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        review_cycle_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[AppraisalResponse]:
        items, total = self.appraisal_repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            employee_id=employee_id,
            review_cycle_id=review_cycle_id,
            status=status,
        )
        return PaginatedResponse(
            data=[AppraisalResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def approve_appraisal(
        self,
        tenant_id: UUID,
        appraisal_id: UUID,
        *,
        actor_id: UUID,
        payload: Optional[AppraisalApproveRequest] = None,
        meta: Optional[dict] = None,
    ) -> AppraisalResponse:
        entity = self.appraisal_repo.get_by_id(appraisal_id, tenant_id)
        if not entity:
            raise NotFoundError("Appraisal not found")
        if entity.status not in ("draft", "pending_approval"):
            raise ValidationError("Appraisal cannot be approved in current status")
        entity.status = "approved"
        entity.approver_id = str(actor_id)
        entity.approved_at = datetime.now(timezone.utc)
        entity.updated_by = str(actor_id)
        self._log("performance.appraisal.approve", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return AppraisalResponse.model_validate(entity)

    def update_appraisal(
        self, tenant_id: UUID, appraisal_id: UUID, payload: AppraisalUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> AppraisalResponse:
        entity = self.appraisal_repo.get_by_id(appraisal_id, tenant_id)
        if not entity:
            raise NotFoundError("Appraisal not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("performance.appraisal.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return AppraisalResponse.model_validate(entity)

    def _okr_response(self, entity: OKR) -> OKRResponse:
        raw = json.loads(entity.key_results_json or "[]")
        return OKRResponse(
            id=UUID(entity.id),
            tenant_id=UUID(entity.tenant_id),
            employee_id=UUID(entity.employee_id),
            objective=entity.objective,
            key_results=[KeyResultItem.model_validate(kr) for kr in raw],
            quarter=entity.quarter,
            year=entity.year,
            progress=entity.progress,
            status=entity.status,
            created_at=entity.created_at,
        )

    def _review_response(self, entity, review_type: str) -> ReviewResponse:
        feedback = getattr(entity, "feedback", None)
        submitted = getattr(entity, "submitted_at", None)
        return ReviewResponse(
            id=UUID(entity.id),
            review_type=review_type,
            review_cycle_id=UUID(entity.review_cycle_id),
            employee_id=UUID(entity.employee_id),
            rating=entity.rating,
            feedback=feedback,
            status=entity.status,
            submitted_at=submitted,
            created_at=entity.created_at,
        )

    def _log(self, action: str, tenant_id: UUID, actor_id: UUID, resource_id: str, meta: Optional[dict]) -> None:
        self.audit.log(
            action,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="performance",
            resource_id=resource_id,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
