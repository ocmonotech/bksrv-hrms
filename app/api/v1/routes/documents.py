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
from app.schemas.documents import (
    CompanyDocumentCreate,
    CompanyDocumentResponse,
    DocumentCategoryCreate,
    DocumentCategoryResponse,
    DocumentCategoryUpdate,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    GeneratedLetterCreate,
    GeneratedLetterResponse,
    GeneratedLetterSignRequest,
    LetterTemplateCreate,
    LetterTemplateResponse,
    LetterTemplateUpdate,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])
settings = get_settings()


def check_documents_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.DOCUMENTS, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


@router.post("/categories", response_model=APIResponse[DocumentCategoryResponse], status_code=201)
def create_category(
    request: Request,
    payload: DocumentCategoryCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
):
    check_documents_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_category(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Category created")


@router.get("/categories", response_model=PaginatedResponse[DocumentCategoryResponse])
def list_categories(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_documents_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_categories(ctx.tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)


@router.patch("/categories/{category_id}", response_model=APIResponse[DocumentCategoryResponse])
def update_category(
    request: Request,
    category_id: UUID,
    payload: DocumentCategoryUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
):
    check_documents_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_category(ctx.tenant_id, category_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Category updated")


@router.delete("/categories/{category_id}", response_model=APIResponse[dict])
def delete_category(
    request: Request,
    category_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
):
    check_documents_permission(ctx, current_user, PermissionAction.DELETE, db)
    service.delete_category(ctx.tenant_id, category_id, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data={"id": str(category_id)}, message="Category deleted")


@router.get("/employee", response_model=PaginatedResponse[EmployeeDocumentResponse])
def list_employee_documents(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_documents_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_employee_documents(
        ctx.tenant_id, page=page, page_size=page_size, search=search, employee_id=employee_id, category_id=category_id, status=status
    )


@router.post("/employee", response_model=APIResponse[EmployeeDocumentResponse], status_code=201)
async def upload_employee_document(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
    employee_id: UUID = Form(...),
    title: str = Form(...),
    category_id: Optional[UUID] = Form(default=None),
    description: Optional[str] = Form(default=None),
    status: str = Form(default="active"),
    is_confidential: bool = Form(default=False),
    file: UploadFile = File(...),
):
    check_documents_permission(ctx, current_user, PermissionAction.CREATE, db)
    content = await file.read()
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise ValidationError(f"File exceeds {settings.max_upload_size_mb}MB limit")
    payload = EmployeeDocumentCreate(
        employee_id=employee_id,
        category_id=category_id,
        title=title,
        description=description,
        status=status,
        is_confidential=is_confidential,
    )
    data = service.upload_employee_document(
        ctx.tenant_id,
        payload,
        file_name=file.filename or "document",
        content=content,
        mime_type=file.content_type,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Employee document uploaded")


@router.get("/company", response_model=PaginatedResponse[CompanyDocumentResponse])
def list_company_documents(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    category_id: Optional[UUID] = Query(default=None),
    branch_id: Optional[UUID] = Query(default=None),
    department_id: Optional[UUID] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_documents_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_company_documents(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id,
        branch_id=branch_id,
        department_id=department_id,
        is_active=is_active,
    )


@router.post("/company", response_model=APIResponse[CompanyDocumentResponse], status_code=201)
async def upload_company_document(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
    title: str = Form(...),
    category_id: Optional[UUID] = Form(default=None),
    description: Optional[str] = Form(default=None),
    branch_id: Optional[UUID] = Form(default=None),
    department_id: Optional[UUID] = Form(default=None),
    visibility: str = Form(default="all"),
    version: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
):
    check_documents_permission(ctx, current_user, PermissionAction.CREATE, db)
    content = await file.read()
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise ValidationError(f"File exceeds {settings.max_upload_size_mb}MB limit")
    payload = CompanyDocumentCreate(
        title=title,
        category_id=category_id,
        description=description,
        branch_id=branch_id,
        department_id=department_id,
        visibility=visibility,
        version=version,
    )
    data = service.upload_company_document(
        ctx.tenant_id,
        payload,
        file_name=file.filename or "document",
        content=content,
        mime_type=file.content_type,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Company document uploaded")


@router.post("/letter-templates", response_model=APIResponse[LetterTemplateResponse], status_code=201)
def create_letter_template(
    request: Request,
    payload: LetterTemplateCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
):
    check_documents_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_letter_template(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Letter template created")


@router.get("/letter-templates", response_model=PaginatedResponse[LetterTemplateResponse])
def list_letter_templates(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    letter_type: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_documents_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_letter_templates(
        ctx.tenant_id, page=page, page_size=page_size, search=search, letter_type=letter_type, is_active=is_active
    )


@router.patch("/letter-templates/{template_id}", response_model=APIResponse[LetterTemplateResponse])
def update_letter_template(
    request: Request,
    template_id: UUID,
    payload: LetterTemplateUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
):
    check_documents_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_letter_template(ctx.tenant_id, template_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Letter template updated")


@router.get("/generated-letters", response_model=PaginatedResponse[GeneratedLetterResponse])
def list_generated_letters(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    employee_id: Optional[UUID] = Query(default=None),
    template_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_documents_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_generated_letters(
        ctx.tenant_id, page=page, page_size=page_size, search=search, employee_id=employee_id, template_id=template_id, status=status
    )


@router.post("/generated-letters", response_model=APIResponse[GeneratedLetterResponse], status_code=201)
def create_generated_letter(
    request: Request,
    payload: GeneratedLetterCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
):
    check_documents_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_generated_letter(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Letter generated")


@router.put("/generated-letters/{letter_id}/sign", response_model=APIResponse[GeneratedLetterResponse])
def sign_generated_letter(
    letter_id: UUID,
    request: Request,
    payload: GeneratedLetterSignRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: DocumentService = Depends(get_service),
):
    check_documents_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.sign_generated_letter(
        ctx.tenant_id,
        letter_id,
        signed_by=payload.signed_by,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Letter signed")
