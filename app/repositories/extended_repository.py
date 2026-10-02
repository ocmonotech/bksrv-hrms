from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.assets import Asset, AssetAssignment
from app.models.communication import Announcement, CommunicationLog, CommunicationTemplate
from app.models.exit import ExitClearance, ExitInterview, Resignation
from app.models.expenses import ExpenseAdvance, ExpenseClaim, ExpensePolicy
from app.models.travel import TravelPolicy, TravelRequest
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class ExpensePolicyRepository(TenantScopedRepository[ExpensePolicy]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ExpensePolicy)


class ExpenseClaimRepository(TenantScopedRepository[ExpenseClaim]):
    search_fields = ("title",)

    def __init__(self, db: Session) -> None:
        super().__init__(db, ExpenseClaim, search_fields=self.search_fields)


class ExpenseAdvanceRepository(TenantScopedRepository[ExpenseAdvance]):
    search_fields = ("purpose",)

    def __init__(self, db: Session) -> None:
        super().__init__(db, ExpenseAdvance, search_fields=self.search_fields)


class TravelPolicyRepository(TenantScopedRepository[TravelPolicy]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, TravelPolicy)


class TravelRequestRepository(TenantScopedRepository[TravelRequest]):
    search_fields = ("destination",)

    def __init__(self, db: Session) -> None:
        super().__init__(db, TravelRequest, search_fields=self.search_fields)


class AssetRepository(TenantScopedRepository[Asset]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Asset)


class AssetAssignmentRepository(TenantScopedRepository[AssetAssignment]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AssetAssignment)


class AnnouncementRepository(TenantScopedRepository[Announcement]):
    search_fields = ("title",)

    def __init__(self, db: Session) -> None:
        super().__init__(db, Announcement, search_fields=self.search_fields)


class CommunicationTemplateRepository(TenantScopedRepository[CommunicationTemplate]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, CommunicationTemplate)


class CommunicationLogRepository(TenantScopedRepository[CommunicationLog]):
    search_fields = ("recipient_email", "subject")

    def __init__(self, db: Session) -> None:
        super().__init__(db, CommunicationLog, search_fields=self.search_fields)


class ResignationRepository(TenantScopedRepository[Resignation]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Resignation)


class ExitClearanceRepository(TenantScopedRepository[ExitClearance]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ExitClearance)

    def get_by_resignation(self, tenant_id: UUID, resignation_id: UUID) -> Optional[ExitClearance]:
        from sqlalchemy import select

        stmt = select(ExitClearance).where(
            ExitClearance.tenant_id == str(tenant_id),
            ExitClearance.resignation_id == str(resignation_id),
            ExitClearance.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)


class ExitInterviewRepository(TenantScopedRepository[ExitInterview]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ExitInterview)
