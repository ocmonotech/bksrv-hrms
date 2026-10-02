from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.surveys import Survey, SurveyQuestion, SurveyResponse
from app.repositories.survey_repository import SurveyQuestionRepository, SurveyRepository, SurveyResponseRepository
from app.schemas.common import PaginatedResponse
from app.schemas.surveys import (
    SurveyCreate,
    SurveyDashboardStats,
    SurveyQuestionCreate,
    SurveyQuestionResponse,
    SurveyResponse as SurveyResponseSchema,
    SurveySubmissionCreate,
    SurveyUpdate,
)
from app.services.audit_service import AuditService
from app.services.company_setup.base import _coerce_payload
from app.utils.pagination import total_pages


class SurveyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.survey_repo = SurveyRepository(db)
        self.question_repo = SurveyQuestionRepository(db)
        self.response_repo = SurveyResponseRepository(db)
        self.audit = AuditService(db)

    def _log(self, action: str, tenant_id: UUID, actor_id: UUID, resource_id: str, meta: Optional[dict]) -> None:
        self.audit.log(
            action,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="survey",
            resource_id=resource_id,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )

    def get_dashboard_stats(self, tenant_id: UUID) -> SurveyDashboardStats:
        return SurveyDashboardStats(
            active_surveys=self.survey_repo.count_active(tenant_id),
            total_responses=self.response_repo.total_responses(tenant_id),
            avg_engagement_score=self.response_repo.avg_rating_for_type(tenant_id, "engagement"),
            wellbeing_index=self.response_repo.avg_rating_for_type(tenant_id, "wellbeing"),
        )

    def create_survey(
        self, tenant_id: UUID, payload: SurveyCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> SurveyResponseSchema:
        data = _coerce_payload(payload.model_dump())
        entity = Survey(
            tenant_id=str(tenant_id),
            status="draft",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.survey_repo.add(entity)
        self._log("survey.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return SurveyResponseSchema.model_validate(entity)

    def list_surveys(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        survey_type: Optional[str] = None,
    ) -> PaginatedResponse[SurveyResponseSchema]:
        items, total = self.survey_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, search=search, status=status, survey_type=survey_type
        )
        return PaginatedResponse(
            data=[SurveyResponseSchema.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_survey(
        self, tenant_id: UUID, survey_id: UUID, payload: SurveyUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> SurveyResponseSchema:
        entity = self.survey_repo.get_by_id(survey_id, tenant_id)
        if not entity:
            raise NotFoundError("Survey not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("survey.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return SurveyResponseSchema.model_validate(entity)

    def add_question(
        self, tenant_id: UUID, survey_id: UUID, payload: SurveyQuestionCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> SurveyQuestionResponse:
        if not self.survey_repo.get_by_id(survey_id, tenant_id):
            raise NotFoundError("Survey not found")
        data = _coerce_payload(payload.model_dump())
        entity = SurveyQuestion(
            tenant_id=str(tenant_id),
            survey_id=str(survey_id),
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.question_repo.add(entity)
        self._log("survey.question.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return SurveyQuestionResponse.model_validate(entity)

    def list_questions(self, tenant_id: UUID, survey_id: UUID) -> list[SurveyQuestionResponse]:
        if not self.survey_repo.get_by_id(survey_id, tenant_id):
            raise NotFoundError("Survey not found")
        items = self.question_repo.list_for_survey(tenant_id, survey_id)
        return [SurveyQuestionResponse.model_validate(i) for i in items]

    def submit_responses(
        self,
        tenant_id: UUID,
        survey_id: UUID,
        payload: SurveySubmissionCreate,
        *,
        employee_id: Optional[UUID],
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> dict:
        survey = self.survey_repo.get_by_id(survey_id, tenant_id)
        if not survey:
            raise NotFoundError("Survey not found")
        if survey.status != "active":
            raise ValidationError("Survey is not active")
        now = datetime.now(timezone.utc)
        count = 0
        for answer in payload.answers:
            if not self.question_repo.get_by_id(answer.question_id, tenant_id):
                raise NotFoundError(f"Question {answer.question_id} not found")
            entity = SurveyResponse(
                tenant_id=str(tenant_id),
                survey_id=str(survey_id),
                question_id=str(answer.question_id),
                employee_id=str(employee_id) if employee_id and not survey.is_anonymous else None,
                response_value=answer.response_value,
                submitted_at=now,
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.response_repo.add(entity)
            count += 1
        self._log("survey.response.submit", tenant_id, actor_id, str(survey_id), meta)
        self.db.commit()
        return {"submitted": count}
