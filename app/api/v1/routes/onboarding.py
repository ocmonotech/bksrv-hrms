from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_meta
from app.api.v1.routes.company_setup.crud_factory import require_tenant_scope
from app.core.config import get_settings
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError, ValidationError
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
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
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])
settings = get_settings()


def check_onboarding_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.ONBOARDING, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> OnboardingService:
    return OnboardingService(db)


@router.post("/checklists", response_model=APIResponse[OnboardingChecklistResponse], status_code=201)
def create_checklist(
    request: Request,
    payload: OnboardingChecklistCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_checklist(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Checklist created")


@router.get("/checklists", response_model=PaginatedResponse[OnboardingChecklistResponse])
def list_checklists(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_checklists(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@router.put("/checklists/{checklist_id}", response_model=APIResponse[OnboardingChecklistResponse])
def update_checklist(
    checklist_id: UUID,
    request: Request,
    payload: OnboardingChecklistUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_checklist(
        ctx.tenant_id, checklist_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Checklist updated")


@router.post("/tasks", response_model=APIResponse[OnboardingTaskResponse], status_code=201)
def create_task(
    request: Request,
    payload: OnboardingTaskCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_task(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Task created")


@router.get("/tasks", response_model=PaginatedResponse[OnboardingTaskResponse])
def list_tasks(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    checklist_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_tasks(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        checklist_id=checklist_id,
        status=status,
    )


@router.put("/tasks/{task_id}", response_model=APIResponse[OnboardingTaskResponse])
def update_task(
    task_id: UUID,
    request: Request,
    payload: OnboardingTaskUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_task(
        ctx.tenant_id, task_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Task updated")


@router.post("/documents", response_model=APIResponse[NewJoinerDocumentResponse], status_code=201)
async def upload_document(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
    file: UploadFile = File(...),
    employee_id: UUID = Form(...),
    document_type: str = Form(..., min_length=1, max_length=100),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.CREATE, db)
    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationError(f"File size exceeds {settings.max_upload_size_mb}MB limit")
    data = service.upload_document(
        ctx.tenant_id,
        employee_id,
        document_type=document_type,
        file_name=file.filename or "document",
        content=content,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Document uploaded")


@router.get("/documents", response_model=PaginatedResponse[NewJoinerDocumentResponse])
def list_documents(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_documents(
        ctx.tenant_id, page=page, page_size=page_size, employee_id=employee_id, status=status
    )


@router.put("/documents/{document_id}/verify", response_model=APIResponse[NewJoinerDocumentResponse])
def verify_document(
    document_id: UUID,
    request: Request,
    payload: DocumentVerifyRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.verify_document(
        ctx.tenant_id, document_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Document verified")


@router.post("/probation", response_model=APIResponse[ProbationReviewResponse], status_code=201)
def create_probation(
    request: Request,
    payload: ProbationReviewCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_probation_review(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Probation review created")


@router.get("/probation", response_model=PaginatedResponse[ProbationReviewResponse])
def list_probation(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_probation_reviews(
        ctx.tenant_id, page=page, page_size=page_size, employee_id=employee_id, status=status
    )


@router.put("/probation/{review_id}", response_model=APIResponse[ProbationReviewResponse])
def update_probation(
    review_id: UUID,
    request: Request,
    payload: ProbationReviewUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_probation(
        ctx.tenant_id, review_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Probation review updated")


@router.put("/probation/{review_id}/approve", response_model=APIResponse[ProbationReviewResponse])
def approve_probation(
    review_id: UUID,
    request: Request,
    payload: ProbationApproveRequest = ProbationApproveRequest(),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: OnboardingService = Depends(get_service),
):
    check_onboarding_permission(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.approve_probation(
        ctx.tenant_id, review_id, actor_id=current_user.id, payload=payload, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Probation review approved")
