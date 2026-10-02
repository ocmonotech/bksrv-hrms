from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_meta, get_tenant_context
from app.api.v1.routes.company_setup.crud_factory import require_tenant_scope
from app.core.config import get_settings
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError, ValidationError
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.employee import (
    DocumentResponse,
    EmployeeCreate,
    EmployeeListItem,
    EmployeeProfileResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
    TimelineResponse,
)
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["Employees"])
settings = get_settings()


def check_employee_permission(
    ctx: TenantContext,
    current_user: User,
    action: PermissionAction,
    db: Session,
) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.EMPLOYEES, action, db=db, role_id=ctx.role_id)


def get_employee_service(db: Session = Depends(get_db)) -> EmployeeService:
    return EmployeeService(db)


@router.get("", response_model=PaginatedResponse[EmployeeListItem])
def list_employees(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: EmployeeService = Depends(get_employee_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None, max_length=100),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    employment_type: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_employee_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_employees(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        search=search,
        branch_id=branch_id,
        department_id=department_id,
        status=status,
        employment_type=employment_type,
        is_active=is_active,
    )


@router.post("", response_model=APIResponse[EmployeeProfileResponse], status_code=201)
def create_employee(
    payload: EmployeeCreate,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: EmployeeService = Depends(get_employee_service),
):
    check_employee_permission(ctx, current_user, PermissionAction.CREATE, db)
    employee = service.create_employee(
        ctx.tenant_id,
        payload,
        actor_id=current_user.id,
        company_id=ctx.company_id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=employee, message="Employee created successfully")


@router.get("/{employee_id}", response_model=APIResponse[EmployeeProfileResponse])
def get_employee(
    employee_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: EmployeeService = Depends(get_employee_service),
):
    check_employee_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_employee(ctx.tenant_id, employee_id))


@router.put("/{employee_id}", response_model=APIResponse[EmployeeProfileResponse])
def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: EmployeeService = Depends(get_employee_service),
):
    check_employee_permission(ctx, current_user, PermissionAction.EDIT, db)
    employee = service.update_employee(
        ctx.tenant_id,
        employee_id,
        payload,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=employee, message="Employee updated successfully")


@router.delete("/{employee_id}", response_model=APIResponse[dict])
def delete_employee(
    employee_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: EmployeeService = Depends(get_employee_service),
):
    check_employee_permission(ctx, current_user, PermissionAction.DELETE, db)
    service.delete_employee(
        ctx.tenant_id,
        employee_id,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data={"deleted": True}, message="Employee deleted successfully")


@router.put("/{employee_id}/status", response_model=APIResponse[EmployeeProfileResponse])
def update_employee_status(
    employee_id: UUID,
    payload: EmployeeStatusUpdate,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: EmployeeService = Depends(get_employee_service),
):
    check_employee_permission(ctx, current_user, PermissionAction.EDIT, db)
    employee = service.update_status(
        ctx.tenant_id,
        employee_id,
        payload,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=employee, message="Employee status updated successfully")


@router.post("/{employee_id}/documents", response_model=APIResponse[DocumentResponse], status_code=201)
async def upload_employee_document(
    employee_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: EmployeeService = Depends(get_employee_service),
    document_type: str = Form(..., min_length=1, max_length=100),
    title: str = Form(..., min_length=1, max_length=255),
    file: UploadFile = File(...),
):
    check_employee_permission(ctx, current_user, PermissionAction.CREATE, db)

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationError(f"File size exceeds {settings.max_upload_size_mb}MB limit")

    doc = service.upload_document(
        ctx.tenant_id,
        employee_id,
        document_type=document_type,
        title=title,
        file_name=file.filename or "document",
        content=content,
        mime_type=file.content_type,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=doc, message="Document uploaded successfully")


@router.get("/{employee_id}/timeline", response_model=PaginatedResponse[TimelineResponse])
def get_employee_timeline(
    employee_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: EmployeeService = Depends(get_employee_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    check_employee_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.get_timeline(ctx.tenant_id, employee_id, page=page, page_size=page_size)
