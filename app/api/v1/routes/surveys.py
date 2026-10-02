from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_meta
from app.api.v1.routes.company_setup.crud_factory import require_tenant_scope
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.surveys import (
    SurveyCreate,
    SurveyDashboardStats,
    SurveyQuestionCreate,
    SurveyQuestionResponse,
    SurveyResponse as SurveyResponseSchema,
    SurveySubmissionCreate,
    SurveyUpdate,
)
from app.services.survey_service import SurveyService

router = APIRouter(prefix="/surveys", tags=["Surveys"])


def _check(ctx: TenantContext, user: User, action: PermissionAction, db: Session) -> None:
    if user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.SURVEYS, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> SurveyService:
    return SurveyService(db)


@router.get("/dashboard", response_model=APIResponse[SurveyDashboardStats])
def dashboard_stats(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: SurveyService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_dashboard_stats(ctx.tenant_id))


@router.post("", response_model=APIResponse[SurveyResponseSchema], status_code=201)
def create_survey(
    request: Request,
    payload: SurveyCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: SurveyService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.create_survey(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Survey created")


@router.get("", response_model=PaginatedResponse[SurveyResponseSchema])
def list_surveys(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: SurveyService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    survey_type: Optional[str] = Query(default=None),
):
    _check(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_surveys(
        ctx.tenant_id, page=page, page_size=page_size, search=search, status=status, survey_type=survey_type
    )


@router.patch("/{survey_id}", response_model=APIResponse[SurveyResponseSchema])
def update_survey(
    request: Request,
    survey_id: UUID,
    payload: SurveyUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: SurveyService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_survey(ctx.tenant_id, survey_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Survey updated")


@router.post("/{survey_id}/questions", response_model=APIResponse[SurveyQuestionResponse], status_code=201)
def add_question(
    request: Request,
    survey_id: UUID,
    payload: SurveyQuestionCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: SurveyService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.add_question(ctx.tenant_id, survey_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Question added")


@router.get("/{survey_id}/questions", response_model=APIResponse[list[SurveyQuestionResponse]])
def list_questions(
    survey_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: SurveyService = Depends(get_service),
):
    _check(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.list_questions(ctx.tenant_id, survey_id))


@router.post("/{survey_id}/responses", response_model=APIResponse[dict])
def submit_responses(
    request: Request,
    survey_id: UUID,
    payload: SurveySubmissionCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: SurveyService = Depends(get_service),
    employee_id: Optional[UUID] = Query(default=None),
):
    _check(ctx, current_user, PermissionAction.CREATE, db)
    data = service.submit_responses(
        ctx.tenant_id,
        survey_id,
        payload,
        employee_id=employee_id,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Responses submitted")
