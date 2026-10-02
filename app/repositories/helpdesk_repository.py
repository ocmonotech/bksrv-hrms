from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.helpdesk import Ticket, TicketAssignment, TicketCategory, TicketReply, TicketSLA
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class TicketCategoryRepository(TenantScopedRepository[TicketCategory]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, TicketCategory)


class TicketRepository(TenantScopedRepository[Ticket]):
    search_fields = ("ticket_number", "subject")

    def __init__(self, db: Session) -> None:
        super().__init__(db, Ticket, search_fields=self.search_fields)

    def next_ticket_number(self, tenant_id: UUID) -> str:
        stmt = select(func.count()).select_from(Ticket).where(Ticket.tenant_id == str(tenant_id))
        count = int(self.db.scalar(stmt) or 0) + 1
        return f"TKT-{count:06d}"

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category_id: Optional[UUID] = None,
        assigned_to: Optional[UUID] = None,
        requester_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
    ):
        extra = []
        if status:
            extra.append(Ticket.status == status)
        if priority:
            extra.append(Ticket.priority == priority)
        if category_id:
            extra.append(Ticket.category_id == str(category_id))
        if assigned_to:
            extra.append(Ticket.assigned_to == str(assigned_to))
        if requester_id:
            extra.append(Ticket.requester_id == str(requester_id))
        if employee_id:
            extra.append(Ticket.employee_id == str(employee_id))
        if department_id:
            extra.append(Ticket.department_id == str(department_id))
        if branch_id:
            extra.append(Ticket.branch_id == str(branch_id))
        return self.list_paginated(
            tenant_id, page=page, page_size=page_size, search=search, extra_filters=extra or None
        )


class TicketReplyRepository(TenantScopedRepository[TicketReply]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, TicketReply, search_fields=())

    def list_for_ticket(self, tenant_id: UUID, ticket_id: UUID) -> list[TicketReply]:
        stmt = (
            select(TicketReply)
            .where(
                TicketReply.tenant_id == str(tenant_id),
                TicketReply.ticket_id == str(ticket_id),
            )
            .order_by(TicketReply.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())


class TicketAssignmentRepository(TenantScopedRepository[TicketAssignment]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, TicketAssignment, search_fields=())


class TicketSLARepository(TenantScopedRepository[TicketSLA]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, TicketSLA)

    def get_for_ticket(self, tenant_id: UUID, category_id: Optional[UUID], priority: str) -> Optional[TicketSLA]:
        stmt = select(TicketSLA).where(
            TicketSLA.tenant_id == str(tenant_id),
            TicketSLA.priority == priority,
            TicketSLA.is_active.is_(True),
            TicketSLA.deleted_at.is_(None),
        )
        if category_id:
            stmt = stmt.where(TicketSLA.category_id == str(category_id))
        return self.db.scalar(stmt)
