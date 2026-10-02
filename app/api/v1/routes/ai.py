from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.ai.ai_service import AIService
from app.api.deps import get_current_user, get_request_meta
from app.api.v1.routes.company_setup.crud_factory import require_tenant_scope
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.ai import (
    AIChatRequest,
    AIResponse,
    AIUsageResponse,
    AIInsightsResponse,
    AnalyzeAttendanceRequest,
    AnalyzeLeavePatternRequest,
    GenerateJobDescriptionRequest,
    GenerateLetterRequest,
    GeneratePolicyRequest,
    PayrollErrorCheckRequest,
    PerformanceSummaryRequest,
    ResumeScoreRequest,
    SummarizeEmployeeRequest,
    TokenUsage,
)
from app.schemas.common import APIResponse

router = APIRouter(prefix="/ai", tags=["AI"])


def check_ai_permission(ctx: TenantContext, current_user: User, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.AI, PermissionAction.VIEW, db=db, role_id=ctx.role_id)


def get_ai_service(db: Session = Depends(get_db)) -> AIService:
    return AIService(db)


def _wrap(data: dict) -> APIResponse[AIResponse]:
    return APIResponse(
        data=AIResponse(
            content=data["content"],
            prompt_type=data["prompt_type"],
            module=data["module"],
            provider=data["provider"],
            model=data.get("model"),
            is_fallback=data["is_fallback"],
            token_usage=TokenUsage(**data["token_usage"]),
            log_id=data["log_id"],
        )
    )


@router.get("/usage", response_model=APIResponse[AIUsageResponse])
def ai_usage(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return APIResponse(data=AIUsageResponse(**service.get_usage(ctx.tenant_id)))


@router.get("/insights", response_model=APIResponse[AIInsightsResponse])
def module_insights(
    request: Request,
    module: str = Query(..., min_length=2, max_length=50),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return APIResponse(data=AIInsightsResponse(**service.module_insights(
        ctx.tenant_id, current_user.id, module=module, meta=get_request_meta(request)
    )))


@router.post("/chat", response_model=APIResponse[AIResponse])
def ai_chat(
    request: Request,
    payload: AIChatRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.chat(
            ctx.tenant_id,
            current_user.id,
            message=payload.message,
            context=payload.context,
            meta=get_request_meta(request),
        )
    )


@router.post("/generate-policy", response_model=APIResponse[AIResponse])
def generate_policy(
    request: Request,
    payload: GeneratePolicyRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.generate_policy(
            ctx.tenant_id,
            current_user.id,
            policy_type=payload.policy_type,
            requirements=payload.requirements,
            context=payload.context,
            meta=get_request_meta(request),
        )
    )


@router.post("/generate-letter", response_model=APIResponse[AIResponse])
def generate_letter(
    request: Request,
    payload: GenerateLetterRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.generate_letter(
            ctx.tenant_id,
            current_user.id,
            letter_type=payload.letter_type,
            details=payload.details,
            employee_id=payload.employee_id,
            meta=get_request_meta(request),
        )
    )


@router.post("/summarize-employee", response_model=APIResponse[AIResponse])
def summarize_employee(
    request: Request,
    payload: SummarizeEmployeeRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.summarize_employee(
            ctx.tenant_id, current_user.id, employee_id=payload.employee_id, meta=get_request_meta(request)
        )
    )


@router.post("/analyze-attendance", response_model=APIResponse[AIResponse])
def analyze_attendance(
    request: Request,
    payload: AnalyzeAttendanceRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.analyze_attendance(
            ctx.tenant_id,
            current_user.id,
            employee_id=payload.employee_id,
            month=payload.month,
            year=payload.year,
            meta=get_request_meta(request),
        )
    )


@router.post("/analyze-leave-pattern", response_model=APIResponse[AIResponse])
def analyze_leave_pattern(
    request: Request,
    payload: AnalyzeLeavePatternRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.analyze_leave_pattern(
            ctx.tenant_id,
            current_user.id,
            employee_id=payload.employee_id,
            department_id=payload.department_id,
            meta=get_request_meta(request),
        )
    )


@router.post("/payroll-error-check", response_model=APIResponse[AIResponse])
def payroll_error_check(
    request: Request,
    payload: PayrollErrorCheckRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.payroll_error_check(
            ctx.tenant_id,
            current_user.id,
            payroll_run_id=payload.payroll_run_id,
            meta=get_request_meta(request),
        )
    )


@router.post("/resume-score", response_model=APIResponse[AIResponse])
def resume_score(
    request: Request,
    payload: ResumeScoreRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.resume_score(
            ctx.tenant_id, current_user.id, candidate_id=payload.candidate_id, meta=get_request_meta(request)
        )
    )


@router.post("/generate-job-description", response_model=APIResponse[AIResponse])
def generate_job_description(
    request: Request,
    payload: GenerateJobDescriptionRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.generate_job_description(
            ctx.tenant_id,
            current_user.id,
            job_opening_id=payload.job_opening_id,
            title=payload.title,
            requirements=payload.requirements,
            meta=get_request_meta(request),
        )
    )


@router.post("/performance-summary", response_model=APIResponse[AIResponse])
def performance_summary(
    request: Request,
    payload: PerformanceSummaryRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AIService = Depends(get_ai_service),
):
    check_ai_permission(ctx, current_user, db)
    return _wrap(
        service.performance_summary(
            ctx.tenant_id,
            current_user.id,
            employee_id=payload.employee_id,
            review_cycle_id=payload.review_cycle_id,
            meta=get_request_meta(request),
        )
    )
