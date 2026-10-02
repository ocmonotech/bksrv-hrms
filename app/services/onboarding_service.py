from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.onboarding import NewJoinerDocument, OnboardingChecklist, OnboardingTask, ProbationReview
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.onboarding_repository import (
    NewJoinerDocumentRepository,
    OnboardingChecklistRepository,
    OnboardingTaskRepository,
    ProbationReviewRepository,
)
from app.schemas.common import PaginatedResponse
from app.schemas.onboarding import (
    DocumentVerifyRequest,
    NewJoinerDocumentResponse,
    OnboardingChecklistCreate,
    OnboardingChecklistResponse,
    OnboardingChecklistUpdate,
    OnboardingTaskCreate,
    OnboardingTaskResponse,
    OnboardingTaskUpdate,
    ProbationApproveRequest,
    ProbationReviewCreate,
    ProbationReviewResponse,
    ProbationReviewUpdate,
)
from app.services.audit_service import AuditService
from app.services.company_setup.base import _coerce_payload
from app.utils.file_storage import onboarding_document_relative_path, save_upload_file
from app.utils.pagination import total_pages


class OnboardingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.checklist_repo = OnboardingChecklistRepository(db)
        self.task_repo = OnboardingTaskRepository(db)
        self.document_repo = NewJoinerDocumentRepository(db)
        self.probation_repo = ProbationReviewRepository(db)
        self.employee_repo = EmployeeRepository(db)
        self.audit = AuditService(db)

    def create_checklist(
        self, tenant_id: UUID, payload: OnboardingChecklistCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> OnboardingChecklistResponse:
        if self.checklist_repo.get_by_code(tenant_id, payload.code.upper()):
            raise ConflictError(f"Checklist '{payload.code}' already exists")
        entity = OnboardingChecklist(
            tenant_id=str(tenant_id),
            code=payload.code.upper(),
            name=payload.name,
            description=payload.description,
            department_id=str(payload.department_id) if payload.department_id else None,
            is_default=payload.is_default,
            is_active=payload.is_active,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.checklist_repo.add(entity)
        self._log("onboarding.checklist.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return OnboardingChecklistResponse.model_validate(entity)

    def list_checklists(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[OnboardingChecklistResponse]:
        items, total = self.checklist_repo.list_paginated(
            tenant_id, page=page, page_size=page_size, search=search, is_active=is_active
        )
        return PaginatedResponse(
            data=[OnboardingChecklistResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_checklist(
        self,
        tenant_id: UUID,
        checklist_id: UUID,
        payload: OnboardingChecklistUpdate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> OnboardingChecklistResponse:
        entity = self.checklist_repo.get_by_id(checklist_id, tenant_id)
        if not entity:
            raise NotFoundError("Checklist not found")
        data = _coerce_payload(payload.model_dump(exclude_unset=True))
        for key, value in data.items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("onboarding.checklist.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return OnboardingChecklistResponse.model_validate(entity)

    def create_task(
        self, tenant_id: UUID, payload: OnboardingTaskCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> OnboardingTaskResponse:
        if not self.checklist_repo.get_by_id(payload.checklist_id, tenant_id):
            raise NotFoundError("Checklist not found")
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        data = _coerce_payload(payload.model_dump())
        entity = OnboardingTask(
            tenant_id=str(tenant_id),
            status="pending",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.task_repo.add(entity)
        self._log("onboarding.task.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return OnboardingTaskResponse.model_validate(entity)

    def list_tasks(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        checklist_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[OnboardingTaskResponse]:
        items, total = self.task_repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            employee_id=employee_id,
            checklist_id=checklist_id,
            status=status,
        )
        return PaginatedResponse(
            data=[OnboardingTaskResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_task(
        self, tenant_id: UUID, task_id: UUID, payload: OnboardingTaskUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> OnboardingTaskResponse:
        entity = self.task_repo.get_by_id(task_id, tenant_id)
        if not entity:
            raise NotFoundError("Task not found")
        data = payload.model_dump(exclude_unset=True)
        if data.get("status") == "completed":
            entity.completed_at = datetime.now(timezone.utc)
        for key, value in data.items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("onboarding.task.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return OnboardingTaskResponse.model_validate(entity)

    def upload_document(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        *,
        document_type: str,
        file_name: str,
        content: bytes,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> NewJoinerDocumentResponse:
        if not self.employee_repo.get_by_id(employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        rel_path = onboarding_document_relative_path(
            str(tenant_id), str(employee_id), document_type, file_name
        )
        save_upload_file(rel_path, content)
        doc = NewJoinerDocument(
            tenant_id=str(tenant_id),
            employee_id=str(employee_id),
            document_type=document_type,
            file_name=file_name,
            file_path=rel_path,
            status="pending",
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.document_repo.add(doc)
        self._log("onboarding.document.upload", tenant_id, actor_id, str(doc.id), meta)
        self.db.commit()
        self.db.refresh(doc)
        return NewJoinerDocumentResponse.model_validate(doc)

    def list_documents(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[NewJoinerDocumentResponse]:
        items, total = self.document_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, employee_id=employee_id, status=status
        )
        return PaginatedResponse(
            data=[NewJoinerDocumentResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def verify_document(
        self,
        tenant_id: UUID,
        document_id: UUID,
        payload: DocumentVerifyRequest,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> NewJoinerDocumentResponse:
        doc = self.document_repo.get_by_id(document_id, tenant_id)
        if not doc:
            raise NotFoundError("Document not found")
        doc.status = payload.status
        doc.verified_by = str(actor_id)
        doc.verified_at = datetime.now(timezone.utc)
        doc.rejection_reason = payload.rejection_reason if payload.status == "rejected" else None
        doc.updated_by = str(actor_id)
        self._log("onboarding.document.verify", tenant_id, actor_id, str(doc.id), meta)
        self.db.commit()
        self.db.refresh(doc)
        return NewJoinerDocumentResponse.model_validate(doc)

    def create_probation_review(
        self, tenant_id: UUID, payload: ProbationReviewCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> ProbationReviewResponse:
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        data = _coerce_payload(payload.model_dump())
        entity = ProbationReview(
            tenant_id=str(tenant_id),
            status="draft",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.probation_repo.add(entity)
        self._log("onboarding.probation.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return ProbationReviewResponse.model_validate(entity)

    def list_probation_reviews(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[ProbationReviewResponse]:
        items, total = self.probation_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, employee_id=employee_id, status=status
        )
        return PaginatedResponse(
            data=[ProbationReviewResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def approve_probation(
        self,
        tenant_id: UUID,
        review_id: UUID,
        *,
        actor_id: UUID,
        payload: Optional[ProbationApproveRequest] = None,
        meta: Optional[dict] = None,
    ) -> ProbationReviewResponse:
        entity = self.probation_repo.get_by_id(review_id, tenant_id)
        if not entity:
            raise NotFoundError("Probation review not found")
        if entity.status not in ("draft", "submitted"):
            raise ValidationError("Review cannot be approved in current status")
        entity.status = "approved"
        entity.approver_id = str(actor_id)
        entity.approved_at = datetime.now(timezone.utc)
        entity.updated_by = str(actor_id)
        self._log("onboarding.probation.approve", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return ProbationReviewResponse.model_validate(entity)

    def update_probation(
        self,
        tenant_id: UUID,
        review_id: UUID,
        payload: ProbationReviewUpdate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> ProbationReviewResponse:
        entity = self.probation_repo.get_by_id(review_id, tenant_id)
        if not entity:
            raise NotFoundError("Probation review not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("onboarding.probation.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return ProbationReviewResponse.model_validate(entity)

    def _log(self, action: str, tenant_id: UUID, actor_id: UUID, resource_id: str, meta: Optional[dict]) -> None:
        self.audit.log(
            action,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="onboarding",
            resource_id=resource_id,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
