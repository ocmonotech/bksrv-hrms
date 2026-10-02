from __future__ import annotations

from typing import Callable, Optional
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.permissions import require_permission
from app.core.security import safe_decode_token
from app.core.tenant import TenantContext, resolve_tenant_headers
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.permission_service import PermissionService
from app.services.role_service import RoleService
from app.services.tenant_service import TenantService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_tenant_service(db: Session = Depends(get_db)) -> TenantService:
    return TenantService(db)


def get_role_service(db: Session = Depends(get_db)) -> RoleService:
    return RoleService(db)


def get_permission_service(db: Session = Depends(get_db)) -> PermissionService:
    return PermissionService(db)


def _parse_uuid(value: Optional[str]) -> Optional[UUID]:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise ForbiddenError(f"Invalid UUID header: {value}") from exc


def get_request_meta(request: Request) -> dict:
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
    }


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Authentication required")

    payload = safe_decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired access token")

    user = UserRepository(db).get_by_id(UUID(payload["sub"]))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


async def get_tenant_context(
    request: Request,
    current_user: User = Depends(get_current_user),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    x_company_id: Optional[str] = Header(default=None, alias="X-Company-Id"),
) -> TenantContext:
    tenant_id = _parse_uuid(x_tenant_id) or getattr(request.state, "tenant_id", None)
    company_id = _parse_uuid(x_company_id) or getattr(request.state, "company_id", None)

    try:
        return resolve_tenant_headers(
            is_super_admin=current_user.is_super_admin,
            tenant_id=tenant_id,
            company_id=company_id,
            role=getattr(request.state, "role", None),
            role_id=getattr(request.state, "role_id", None),
        )
    except ValueError as exc:
        raise ForbiddenError(str(exc)) from exc


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_super_admin:
        raise ForbiddenError("Super admin access required")
    return current_user


def require_permission_dep(module: PermissionModule, action: PermissionAction) -> Callable:
    """FastAPI dependency factory for RBAC permission checks."""

    async def _checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.is_super_admin:
            return current_user

        role_slug = getattr(request.state, "role", None)
        role_id = getattr(request.state, "role_id", None)
        if not role_slug:
            raise ForbiddenError("Role context missing from token")

        require_permission(role_slug, module, action, db=db, role_id=role_id)
        return current_user

    return _checker


# Alias for route modules that prefer shorter naming.
require_module_permission = require_permission_dep
