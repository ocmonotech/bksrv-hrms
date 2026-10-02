from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.onboarding import NewJoinerDocument, OnboardingChecklist, OnboardingTask, ProbationReview
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class OnboardingChecklistRepository(TenantScopedRepository[OnboardingChecklist]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, OnboardingChecklist)


class OnboardingTaskRepository(TenantScopedRepository[OnboardingTask]):
    search_fields = ("task_name",)

    def __init__(self, db: Session) -> None:
        super().__init__(db, OnboardingTask, search_fields=self.search_fields)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        checklist_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if employee_id:
            extra.append(OnboardingTask.employee_id == str(employee_id))
        if checklist_id:
            extra.append(OnboardingTask.checklist_id == str(checklist_id))
        if status:
            extra.append(OnboardingTask.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)


class NewJoinerDocumentRepository(TenantScopedRepository[NewJoinerDocument]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, NewJoinerDocument)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if employee_id:
            extra.append(NewJoinerDocument.employee_id == str(employee_id))
        if status:
            extra.append(NewJoinerDocument.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)


class ProbationReviewRepository(TenantScopedRepository[ProbationReview]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ProbationReview)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if employee_id:
            extra.append(ProbationReview.employee_id == str(employee_id))
        if status:
            extra.append(ProbationReview.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)
