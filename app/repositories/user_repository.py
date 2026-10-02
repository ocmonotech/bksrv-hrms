from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.audit import AuditLog
from app.models.role import UserTenantAccess
from app.models.tenant import Company, Tenant
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, User)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower())
        return self.db.scalar(stmt)

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        normalized = identifier.strip().lower()
        stmt = select(User).where(
            (User.email == normalized) | (User.mobile == identifier.strip())
        )
        return self.db.scalar(stmt)

    def get_with_access(self, user_id: UUID) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                joinedload(User.tenant_access).joinedload(UserTenantAccess.tenant),
                joinedload(User.tenant_access).joinedload(UserTenantAccess.company),
                joinedload(User.tenant_access).joinedload(UserTenantAccess.role),
            )
            .where(User.id == str(user_id))
        )
        return self.db.scalar(stmt)


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Tenant)

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        stmt = select(Tenant).where(Tenant.slug == slug)
        return self.db.scalar(stmt)

    def list_active(self) -> list[Tenant]:
        stmt = select(Tenant).where(Tenant.is_active.is_(True)).order_by(Tenant.name)
        return list(self.db.scalars(stmt).all())


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Company)

    def list_by_tenant(self, tenant_id: UUID) -> list[Company]:
        stmt = select(Company).where(
            Company.tenant_id == str(tenant_id),
            Company.is_active.is_(True),
        )
        return list(self.db.scalars(stmt).all())

    def get_by_code(self, tenant_id: UUID, code: str) -> Optional[Company]:
        stmt = select(Company).where(
            Company.tenant_id == str(tenant_id),
            Company.code == code.upper(),
        )
        return self.db.scalar(stmt)


class UserTenantAccessRepository(BaseRepository[UserTenantAccess]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, UserTenantAccess)

    def get_active_for_user(self, user_id: UUID) -> list[UserTenantAccess]:
        stmt = (
            select(UserTenantAccess)
            .options(
                joinedload(UserTenantAccess.company),
                joinedload(UserTenantAccess.tenant),
                joinedload(UserTenantAccess.role),
            )
            .where(
                UserTenantAccess.user_id == str(user_id),
                UserTenantAccess.is_active.is_(True),
            )
        )
        return list(self.db.scalars(stmt).all())

    def get_for_user_company(self, user_id: UUID, company_id: UUID) -> Optional[UserTenantAccess]:
        stmt = (
            select(UserTenantAccess)
            .options(joinedload(UserTenantAccess.role))
            .where(
                UserTenantAccess.user_id == str(user_id),
                UserTenantAccess.company_id == str(company_id),
                UserTenantAccess.is_active.is_(True),
            )
        )
        return self.db.scalar(stmt)

    def get_default_for_user(self, user_id: UUID) -> Optional[UserTenantAccess]:
        stmt = (
            select(UserTenantAccess)
            .options(joinedload(UserTenantAccess.role), joinedload(UserTenantAccess.company))
            .where(
                UserTenantAccess.user_id == str(user_id),
                UserTenantAccess.is_default.is_(True),
                UserTenantAccess.is_active.is_(True),
            )
        )
        return self.db.scalar(stmt)


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AuditLog)

    def create(self, log: AuditLog) -> AuditLog:
        self.db.add(log)
        self.db.flush()
        return log
