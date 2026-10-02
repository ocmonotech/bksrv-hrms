from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_tenant_context, get_tenant_service
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post("", response_model=APIResponse[TenantResponse], status_code=201)
def create_tenant(
    payload: TenantCreate,
    current_user: User = Depends(get_current_user),
    service: TenantService = Depends(get_tenant_service),
) -> APIResponse[TenantResponse]:
    tenant = service.create(payload, is_super_admin=current_user.is_super_admin)
    return APIResponse(data=tenant, message="Tenant created successfully")


@router.get("", response_model=APIResponse[list[TenantResponse]])
def list_tenants(
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
    service: TenantService = Depends(get_tenant_service),
) -> APIResponse[list[TenantResponse]]:
    tenants = service.list_tenants(is_super_admin=current_user.is_super_admin, tenant_id=ctx.tenant_id)
    return APIResponse(data=tenants)
