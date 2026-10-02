from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_permission_service
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.role import PermissionCatalogResponse
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("", response_model=APIResponse[PermissionCatalogResponse])
def list_permissions(
    _: User = Depends(get_current_user),
    service: PermissionService = Depends(get_permission_service),
) -> APIResponse[PermissionCatalogResponse]:
    catalog = service.list_permissions()
    return APIResponse(data=catalog)
