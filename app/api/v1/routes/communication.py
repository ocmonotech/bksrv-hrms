from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_meta
from app.api.v1.routes.company_setup.crud_factory import require_tenant_scope
from app.core.config import get_settings
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.communication import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
    CommunicationLogCreate,
    CommunicationLogResponse,
    CommunicationLogUpdate,
    CommunicationTemplateCreate,
    CommunicationTemplateResponse,
    CommunicationTemplateUpdate,
)
from app.services.extended_modules_service import CommunicationService
from app.workers import enqueue

router = APIRouter(prefix="/communication", tags=["Communication"])
settings = get_settings()


def check_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.SETTINGS, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> CommunicationService:
    return CommunicationService(db)


@router.get("/announcements", response_model=PaginatedResponse[AnnouncementResponse])
def list_announcements(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.announcements.list(ctx.tenant_id, page=page, page_size=page_size, search=search)


@router.post("/announcements", response_model=APIResponse[AnnouncementResponse], status_code=201)
def create_announcement(
    request: Request,
    payload: AnnouncementCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.announcements.create(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Announcement created")


@router.put("/announcements/{announcement_id}", response_model=APIResponse[AnnouncementResponse])
def update_announcement(
    announcement_id: UUID,
    request: Request,
    payload: AnnouncementUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.announcements.update(
        ctx.tenant_id, announcement_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Announcement updated")


@router.post("/announcements/{announcement_id}/send", response_model=APIResponse[AnnouncementResponse])
def send_announcement(
    announcement_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
    channels: Optional[str] = Query(default=None, description="Comma-separated: email,sms,whatsapp,in_app"),
    background: bool = Query(default=False, description="Enqueue send as background job"),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    channel_list = [c.strip() for c in channels.split(",") if c.strip()] if channels else None
    if background:
        job_id = enqueue(
            "send_announcement",
            str(ctx.tenant_id),
            str(announcement_id),
            str(current_user.id),
            channel_list,
        )
        announcement = service.announcements.get(ctx.tenant_id, announcement_id)
        return APIResponse(data=announcement, message=f"Announcement send queued (job {job_id})")
    data = service.send_announcement(
        ctx.tenant_id,
        announcement_id,
        actor_id=current_user.id,
        meta=get_request_meta(request),
        channels=channel_list,
    )
    return APIResponse(data=data, message="Announcement sent")


@router.get("/templates", response_model=PaginatedResponse[CommunicationTemplateResponse])
def list_templates(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.templates.list(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@router.post("/templates", response_model=APIResponse[CommunicationTemplateResponse], status_code=201)
def create_template(
    request: Request,
    payload: CommunicationTemplateCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.templates.create(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Template created")


@router.put("/templates/{template_id}", response_model=APIResponse[CommunicationTemplateResponse])
def update_template(
    template_id: UUID,
    request: Request,
    payload: CommunicationTemplateUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.templates.update(ctx.tenant_id, template_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Template updated")


@router.get("/logs", response_model=PaginatedResponse[CommunicationLogResponse])
def list_logs(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
):
    check_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.logs.list(ctx.tenant_id, page=page, page_size=page_size, search=search)


@router.post("/logs", response_model=APIResponse[CommunicationLogResponse], status_code=201)
def create_log(
    request: Request,
    payload: CommunicationLogCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.logs.create(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Communication log created")


@router.put("/logs/{log_id}", response_model=APIResponse[CommunicationLogResponse])
def update_log(
    log_id: UUID,
    request: Request,
    payload: CommunicationLogUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: CommunicationService = Depends(get_service),
):
    check_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.logs.update(ctx.tenant_id, log_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Communication log updated")
