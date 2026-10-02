from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.audit import AuditLog
from app.repositories.user_repository import AuditLogRepository


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AuditLogRepository(db)

    def log(
        self,
        action: str,
        *,
        actor_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        target_user_id: Optional[UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: str = "info",
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            actor_id=str(actor_id) if actor_id else None,
            tenant_id=str(tenant_id) if tenant_id else None,
            resource_type=resource_type,
            resource_id=resource_id,
            target_user_id=str(target_user_id) if target_user_id else None,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity,
        )
        self.repo.create(entry)
        return entry

    def log_login_success(
        self,
        user_id: UUID,
        *,
        tenant_id: Optional[UUID] = None,
        company_id: Optional[UUID] = None,
        role_slug: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.log(
            "auth.login.success",
            actor_id=user_id,
            tenant_id=tenant_id,
            resource_type="user",
            resource_id=str(user_id),
            details={"company_id": str(company_id) if company_id else None, "role": role_slug},
            ip_address=ip_address,
            user_agent=user_agent,
            severity="info",
        )

    def log_login_failure(
        self,
        identifier: str,
        *,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.log(
            "auth.login.failed",
            details={"identifier": identifier, "reason": reason},
            ip_address=ip_address,
            user_agent=user_agent,
            severity="warning",
        )

    def log_logout(
        self,
        user_id: UUID,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.log(
            "auth.logout",
            actor_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
        )
