from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from app.core.permissions import get_role_permissions_from_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    safe_decode_token,
    verify_password,
)
from app.models.role import RefreshToken, UserTenantAccess
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository, UserTenantAccessRepository
from app.schemas.auth import CompanyOption, LoginResponse, TokenResponse, UserResponse
from app.schemas.role import ModuleActions, PermissionMatrixItem
from app.core.password_reset import consume_reset_token, create_otp_session, create_reset_token, verify_otp_session
from app.services.audit_service import AuditService
from app.services.email_service import send_email

settings = get_settings()


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.access = UserTenantAccessRepository(db)
        self.roles = RoleRepository(db)
        self.audit = AuditService(db)

    def login(
        self,
        identifier: str,
        password: str,
        company_code: Optional[str] = None,
        *,
        remember_me: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> LoginResponse:
        user = self.users.get_by_identifier(identifier)
        if not user or not verify_password(password, user.password_hash):
            self.audit.log_login_failure(identifier, reason="invalid_credentials", ip_address=ip_address, user_agent=user_agent)
            raise UnauthorizedError("Invalid email/mobile or password")

        if not user.is_active:
            self.audit.log_login_failure(identifier, reason="inactive_account", ip_address=ip_address, user_agent=user_agent)
            raise ForbiddenError("Your account is inactive. Contact your administrator.")

        if user.is_super_admin:
            response = self._build_super_admin_response(user, remember_me=remember_me)
            self.audit.log_login_success(
                user.id, role_slug="super_admin", ip_address=ip_address, user_agent=user_agent
            )
            return response

        records = self.access.get_active_for_user(user.id)
        if not records:
            self.audit.log_login_failure(identifier, reason="no_tenant_access", ip_address=ip_address, user_agent=user_agent)
            raise ForbiddenError("No company access assigned to this account")

        if company_code:
            records = [
                r for r in records if r.company and r.company.code.upper() == company_code.upper()
            ]
            if not records:
                raise NotFoundError(f"No access found for company code '{company_code}'")

        access_record = self._pick_access_record(records)
        if access_record.company_id is None:
            raise ValidationError("Company context is required for login")

        access_record.last_login_at = datetime.now(timezone.utc)
        self.db.flush()

        if user.two_factor_enabled:
            session_token = create_otp_session(user.id)
            self.audit.log_login_success(
                user.id,
                tenant_id=access_record.tenant_id,
                company_id=access_record.company_id,
                role_slug=access_record.role.slug if access_record.role else None,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            return LoginResponse(requires_2fa=True, session_token=session_token)

        response = self._build_login_response(user, access_record, remember_me=remember_me)
        self.audit.log_login_success(
            user.id,
            tenant_id=access_record.tenant_id,
            company_id=access_record.company_id,
            role_slug=access_record.role.slug if access_record.role else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return response

    def refresh(self, refresh_token: str) -> TokenResponse:
        payload = safe_decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid or expired refresh token")

        jti = payload.get("jti")
        if jti:
            stmt = select(RefreshToken).where(
                RefreshToken.token_jti == jti,
                RefreshToken.revoked_at.is_(None),
            )
            token_row = self.db.scalar(stmt)
            if not token_row:
                raise UnauthorizedError("Refresh token has been revoked")

        user = self.users.get_by_id(UUID(payload["sub"]))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        claims = {
            k: v
            for k, v in payload.items()
            if k in ("tenant_id", "company_id", "role", "role_id", "is_super_admin", "remember_me")
        }
        remember_me = bool(claims.get("remember_me", False))
        return self._issue_tokens(user, claims, remember_me=remember_me)

    def logout(
        self,
        user: User,
        refresh_token: Optional[str] = None,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        if refresh_token:
            payload = safe_decode_token(refresh_token)
            if payload and payload.get("jti"):
                stmt = select(RefreshToken).where(RefreshToken.token_jti == payload["jti"])
                token_row = self.db.scalar(stmt)
                if token_row:
                    token_row.revoked_at = datetime.now(timezone.utc)

        self.audit.log_logout(user.id, ip_address=ip_address, user_agent=user_agent)
        self.db.commit()

    def get_current_user_profile(
        self,
        user: User,
        *,
        tenant_id: Optional[UUID],
        company_id: Optional[UUID],
    ) -> UserResponse:
        if user.is_super_admin:
            return UserResponse(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_super_admin=True,
                is_active=user.is_active,
                role="super_admin",
            )

        access_record = self._resolve_access(user, tenant_id, company_id)
        return self._user_response(user, access_record)

    def list_user_companies(self, user: User) -> list[CompanyOption]:
        if user.is_super_admin:
            return []

        return [
            CompanyOption(
                id=r.company.id,
                name=r.company.name,
                code=r.company.code,
                tenant_id=r.tenant_id,
                tenant_name=r.tenant.name if r.tenant else "",
                role=r.role.slug if r.role else "",
                role_id=r.role_id,
                is_default=r.is_default,
            )
            for r in self.access.get_active_for_user(user.id)
            if r.company is not None and r.role is not None
        ]

    def _pick_access_record(self, records: list[UserTenantAccess]) -> UserTenantAccess:
        for record in records:
            if record.is_default:
                return record
        return records[0]

    def _resolve_access(
        self,
        user: User,
        tenant_id: Optional[UUID],
        company_id: Optional[UUID],
    ) -> UserTenantAccess:
        records = self.access.get_active_for_user(user.id)
        if company_id:
            match = self.access.get_for_user_company(user.id, company_id)
            if match:
                return match

        if tenant_id:
            for record in records:
                if str(record.tenant_id) == str(tenant_id):
                    return record

        if records:
            return records[0]

        raise ForbiddenError("No active company access for this user")

    def _build_super_admin_response(self, user: User, *, remember_me: bool = False) -> LoginResponse:
        tokens = self._issue_tokens(user, {"is_super_admin": True, "role": "super_admin"}, remember_me=remember_me)
        return LoginResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_super_admin=True,
                is_active=user.is_active,
                role="super_admin",
            ),
            tokens=tokens,
        )

    def _build_login_response(
        self, user: User, access_record: UserTenantAccess, *, remember_me: bool = False
    ) -> LoginResponse:
        role = access_record.role
        claims = {
            "tenant_id": str(access_record.tenant_id),
            "company_id": str(access_record.company_id) if access_record.company_id else None,
            "role": role.slug if role else None,
            "role_id": str(access_record.role_id),
            "is_super_admin": False,
        }
        tokens = self._issue_tokens(user, claims, remember_me=remember_me)
        return LoginResponse(
            user=self._user_response(user, access_record),
            tokens=tokens,
        )

    def _user_response(self, user: User, access_record: UserTenantAccess) -> UserResponse:
        company = access_record.company
        role = access_record.role
        permissions = None
        if role:
            permissions = self._permissions_matrix(role.id)

        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_super_admin=False,
            is_active=user.is_active,
            role=role.slug if role else None,
            role_id=access_record.role_id,
            tenant_id=access_record.tenant_id,
            company_id=access_record.company_id,
            company_name=company.name if company else None,
            permissions=permissions,
        )

    def _permissions_matrix(self, role_id: UUID) -> list[PermissionMatrixItem]:
        from app.core.enums import PermissionAction, PermissionModule

        role_perms = get_role_permissions_from_db(self.db, role_id)
        matrix: list[PermissionMatrixItem] = []
        for module in PermissionModule:
            actions = role_perms.get(module.value, set())
            matrix.append(
                PermissionMatrixItem(
                    module=module.value,
                    actions=ModuleActions(
                        **{action.value: action.value in actions for action in PermissionAction}
                    ),
                )
            )
        return matrix

    def forgot_password(self, identifier: str) -> None:
        user = self.users.get_by_identifier(identifier)
        if user and user.is_active:
            token = create_reset_token(user.id)
            reset_link = f"{settings.app_base_url.rstrip('/')}/reset-password?token={token}"
            send_email(
                to=user.email,
                subject="Password reset request",
                body=f"Use this link to reset your password: {reset_link}",
                html_body=f'<p>Use this link to reset your password:</p><p><a href="{reset_link}">{reset_link}</a></p>',
            )

    def reset_password(self, token: str, new_password: str) -> None:
        user_id = consume_reset_token(token)
        if not user_id:
            raise ValidationError("Invalid or expired reset token")
        user = self.users.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValidationError("Invalid or expired reset token")
        user.password_hash = hash_password(new_password)
        self.db.commit()

    def verify_otp(
        self, otp: str, session_token: Optional[str] = None, *, remember_me: bool = False
    ) -> TokenResponse:
        if not otp or len(otp.strip()) < 4:
            raise ValidationError("Invalid OTP")
        if not session_token:
            raise ValidationError("Session token is required")

        user_id = verify_otp_session(session_token, otp)
        if not user_id:
            raise ValidationError("Invalid or expired OTP")

        user = self.users.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValidationError("Invalid or expired OTP")

        if user.is_super_admin:
            return self._issue_tokens(
                user, {"is_super_admin": True, "role": "super_admin"}, remember_me=remember_me
            )

        records = self.access.get_active_for_user(user.id)
        if not records:
            raise ForbiddenError("No company access assigned to this account")
        access_record = self._pick_access_record(records)
        claims = {
            "tenant_id": str(access_record.tenant_id),
            "company_id": str(access_record.company_id) if access_record.company_id else None,
            "role": access_record.role.slug if access_record.role else None,
            "role_id": str(access_record.role_id),
            "is_super_admin": False,
        }
        return self._issue_tokens(user, claims, remember_me=remember_me)

    def create_otp_challenge(self, user: User) -> str:
        return create_otp_session(user.id)

    def _issue_tokens(self, user: User, claims: dict, *, remember_me: bool = False) -> TokenResponse:
        subject = str(user.id)
        token_claims = {**claims, "remember_me": remember_me}
        expire_days = (
            settings.remember_me_refresh_token_expire_days
            if remember_me
            else settings.refresh_token_expire_days
        )
        access = create_access_token(subject, token_claims)
        refresh = create_refresh_token(subject, token_claims, expire_days=expire_days)

        payload = safe_decode_token(refresh)
        if payload and payload.get("jti"):
            token_record = RefreshToken(
                user_id=user.id,
                token_jti=payload["jti"],
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
            self.db.add(token_record)
            self.db.commit()

        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )


def create_super_admin(db: Session) -> User:
    """Bootstrap platform super admin — run via seed script."""
    repo = UserRepository(db)
    existing = repo.get_by_email(settings.super_admin_email)
    if existing:
        return existing

    user = User(
        email=settings.super_admin_email.lower(),
        password_hash=hash_password(settings.super_admin_password),
        first_name="Platform",
        last_name="Admin",
        is_super_admin=True,
        is_active=True,
        email_verified=True,
    )
    repo.add(user)
    db.commit()
    db.refresh(user)
    return user
