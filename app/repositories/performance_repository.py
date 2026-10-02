from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.performance import Appraisal, Feedback360, Goal, ManagerReview, OKR, ReviewCycle, SelfReview
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class GoalRepository(TenantScopedRepository[Goal]):
    search_fields = ("title",)

    def __init__(self, db: Session) -> None:
        super().__init__(db, Goal, search_fields=self.search_fields)

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
            extra.append(Goal.employee_id == str(employee_id))
        if status:
            extra.append(Goal.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)


class OKRRepository(TenantScopedRepository[OKR]):
    search_fields = ("objective",)

    def __init__(self, db: Session) -> None:
        super().__init__(db, OKR, search_fields=self.search_fields)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        year: Optional[int] = None,
        quarter: Optional[int] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if employee_id:
            extra.append(OKR.employee_id == str(employee_id))
        if year:
            extra.append(OKR.year == year)
        if quarter:
            extra.append(OKR.quarter == quarter)
        if status:
            extra.append(OKR.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)


class ReviewCycleRepository(TenantScopedRepository[ReviewCycle]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ReviewCycle)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        extra = []
        if status:
            extra.append(ReviewCycle.status == status)
        return self.list_paginated(
            tenant_id, page=page, page_size=page_size, is_active=is_active, extra_filters=extra or None
        )


class SelfReviewRepository(TenantScopedRepository[SelfReview]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, SelfReview)


class ManagerReviewRepository(TenantScopedRepository[ManagerReview]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ManagerReview)


class Feedback360Repository(TenantScopedRepository[Feedback360]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Feedback360)


class AppraisalRepository(TenantScopedRepository[Appraisal]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Appraisal)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        review_cycle_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if employee_id:
            extra.append(Appraisal.employee_id == str(employee_id))
        if review_cycle_id:
            extra.append(Appraisal.review_cycle_id == str(review_cycle_id))
        if status:
            extra.append(Appraisal.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)
