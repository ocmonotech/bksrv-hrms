from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select

from app.models.surveys import Survey, SurveyQuestion, SurveyResponse
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class SurveyRepository(TenantScopedRepository[Survey]):
    def __init__(self, db) -> None:
        super().__init__(db, Survey, search_fields=("title", "survey_type"))

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        survey_type: Optional[str] = None,
    ) -> tuple[list[Survey], int]:
        extra = []
        if status:
            extra.append(Survey.status == status)
        if survey_type:
            extra.append(Survey.survey_type == survey_type)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, search=search, extra_filters=extra or None)

    def count_active(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).where(
            Survey.tenant_id == str(tenant_id),
            Survey.status == "active",
            Survey.deleted_at.is_(None),
        )
        return int(self.db.scalar(stmt) or 0)


class SurveyQuestionRepository(TenantScopedRepository[SurveyQuestion]):
    def __init__(self, db) -> None:
        super().__init__(db, SurveyQuestion)

    def list_for_survey(self, tenant_id: UUID, survey_id: UUID) -> list[SurveyQuestion]:
        stmt = (
            select(SurveyQuestion)
            .where(
                SurveyQuestion.tenant_id == str(tenant_id),
                SurveyQuestion.survey_id == str(survey_id),
                SurveyQuestion.deleted_at.is_(None),
            )
            .order_by(SurveyQuestion.order_index)
        )
        return list(self.db.scalars(stmt).all())


class SurveyResponseRepository(TenantScopedRepository[SurveyResponse]):
    def __init__(self, db) -> None:
        super().__init__(db, SurveyResponse)

    def count_for_survey(self, tenant_id: UUID, survey_id: UUID) -> int:
        stmt = select(func.count(func.distinct(SurveyResponse.employee_id))).where(
            SurveyResponse.tenant_id == str(tenant_id),
            SurveyResponse.survey_id == str(survey_id),
            SurveyResponse.deleted_at.is_(None),
        )
        return int(self.db.scalar(stmt) or 0)

    def total_responses(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).where(
            SurveyResponse.tenant_id == str(tenant_id),
            SurveyResponse.deleted_at.is_(None),
        )
        return int(self.db.scalar(stmt) or 0)

    def avg_rating_for_type(self, tenant_id: UUID, survey_type: str) -> float:
        responses = self.db.scalars(
            select(SurveyResponse.response_value)
            .join(Survey, Survey.id == SurveyResponse.survey_id)
            .where(
                SurveyResponse.tenant_id == str(tenant_id),
                Survey.survey_type == survey_type,
                SurveyResponse.deleted_at.is_(None),
            )
        ).all()
        ratings = [float(v) for v in responses if v and str(v).replace(".", "", 1).isdigit()]
        return round(sum(ratings) / len(ratings), 1) if ratings else 0.0
