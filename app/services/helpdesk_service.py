from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.helpdesk import Ticket, TicketAssignment, TicketCategory, TicketReply, TicketSLA
from app.repositories.helpdesk_repository import (
    TicketAssignmentRepository,
    TicketCategoryRepository,
    TicketReplyRepository,
    TicketRepository,
    TicketSLARepository,
)
from app.schemas.common import PaginatedResponse
from app.schemas.helpdesk import (
    TicketAssignRequest,
    TicketCategoryCreate,
    TicketCategoryResponse,
    TicketCategoryUpdate,
    TicketCloseRequest,
    TicketCreate,
    TicketReplyCreate,
    TicketReplyResponse,
    TicketResponse,
)
from app.services.audit_service import AuditService
from app.services.company_setup.base import _coerce_payload
from app.utils.pagination import total_pages


class HelpdeskService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.category_repo = TicketCategoryRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.reply_repo = TicketReplyRepository(db)
        self.assignment_repo = TicketAssignmentRepository(db)
        self.sla_repo = TicketSLARepository(db)
        self.audit = AuditService(db)

    def _log(self, action: str, tenant_id: UUID, actor_id: UUID, resource_id: str, meta: Optional[dict]) -> None:
        self.audit.log(
            action,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="helpdesk",
            resource_id=resource_id,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )

    def create_category(
        self, tenant_id: UUID, payload: TicketCategoryCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TicketCategoryResponse:
        code = payload.code.upper()
        if self.category_repo.get_by_code(tenant_id, code):
            raise ConflictError(f"Category '{code}' already exists")
        data = _coerce_payload(payload.model_dump())
        entity = TicketCategory(
            tenant_id=str(tenant_id),
            code=code,
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **{k: v for k, v in data.items() if k != "code"},
        )
        self.category_repo.add(entity)
        self._seed_default_sla(tenant_id, entity.id, actor_id)
        self._log("helpdesk.category.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TicketCategoryResponse.model_validate(entity)

    def _seed_default_sla(self, tenant_id: UUID, category_id: UUID, actor_id: UUID) -> None:
        defaults = [
            ("low", 8, 48),
            ("medium", 4, 24),
            ("high", 2, 12),
            ("urgent", 1, 4),
        ]
        for priority, response_h, resolution_h in defaults:
            self.sla_repo.add(
                TicketSLA(
                    tenant_id=str(tenant_id),
                    category_id=str(category_id),
                    priority=priority,
                    response_hours=response_h,
                    resolution_hours=resolution_h,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                )
            )

    def list_categories(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20, search: Optional[str] = None, is_active: Optional[bool] = None
    ) -> PaginatedResponse[TicketCategoryResponse]:
        items, total = self.category_repo.list_paginated(tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)
        return PaginatedResponse(
            data=[TicketCategoryResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_category(
        self, tenant_id: UUID, category_id: UUID, payload: TicketCategoryUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TicketCategoryResponse:
        entity = self.category_repo.get_by_id(category_id, tenant_id)
        if not entity:
            raise NotFoundError("Category not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("helpdesk.category.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TicketCategoryResponse.model_validate(entity)

    def create_ticket(
        self, tenant_id: UUID, payload: TicketCreate, *, requester_id: UUID, actor_id: UUID, meta: Optional[dict] = None
    ) -> TicketResponse:
        if payload.category_id and not self.category_repo.get_by_id(payload.category_id, tenant_id):
            raise NotFoundError("Ticket category not found")
        data = _coerce_payload(payload.model_dump())
        entity = Ticket(
            tenant_id=str(tenant_id),
            ticket_number=self.ticket_repo.next_ticket_number(tenant_id),
            requester_id=str(requester_id),
            status="open",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.ticket_repo.add(entity)
        self._log("helpdesk.ticket.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TicketResponse.model_validate(entity)

    def list_tickets(
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
    ) -> PaginatedResponse[TicketResponse]:
        items, total = self.ticket_repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            priority=priority,
            category_id=category_id,
            assigned_to=assigned_to,
            requester_id=requester_id,
            employee_id=employee_id,
            department_id=department_id,
            branch_id=branch_id,
        )
        return PaginatedResponse(
            data=[TicketResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def get_ticket(self, tenant_id: UUID, ticket_id: UUID) -> TicketResponse:
        entity = self.ticket_repo.get_by_id(ticket_id, tenant_id)
        if not entity:
            raise NotFoundError("Ticket not found")
        return TicketResponse.model_validate(entity)

    def add_reply(
        self,
        tenant_id: UUID,
        ticket_id: UUID,
        payload: TicketReplyCreate,
        *,
        author_id: UUID,
        meta: Optional[dict] = None,
    ) -> TicketReplyResponse:
        ticket = self.ticket_repo.get_by_id(ticket_id, tenant_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        if ticket.status == "closed":
            raise ValidationError("Cannot reply to a closed ticket")
        reply = TicketReply(
            tenant_id=str(tenant_id),
            ticket_id=str(ticket_id),
            author_id=str(author_id),
            message=payload.message,
            is_internal=payload.is_internal,
            created_by=str(author_id),
            updated_by=str(author_id),
        )
        self.reply_repo.add(reply)
        if ticket.status == "open":
            ticket.status = "in_progress"
        ticket.updated_by = str(author_id)
        self._log("helpdesk.ticket.reply", tenant_id, author_id, str(ticket_id), meta)
        self.db.commit()
        self.db.refresh(reply)
        return TicketReplyResponse.model_validate(reply)

    def assign_ticket(
        self,
        tenant_id: UUID,
        ticket_id: UUID,
        payload: TicketAssignRequest,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> TicketResponse:
        ticket = self.ticket_repo.get_by_id(ticket_id, tenant_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        if ticket.status == "closed":
            raise ValidationError("Cannot assign a closed ticket")
        ticket.assigned_to = str(payload.assigned_to)
        ticket.status = "in_progress"
        ticket.updated_by = str(actor_id)
        assignment = TicketAssignment(
            tenant_id=str(tenant_id),
            ticket_id=str(ticket_id),
            assigned_to=str(payload.assigned_to),
            assigned_by=str(actor_id),
            notes=payload.notes,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.assignment_repo.add(assignment)
        self._log("helpdesk.ticket.assign", tenant_id, actor_id, str(ticket_id), meta)
        self.db.commit()
        self.db.refresh(ticket)
        return TicketResponse.model_validate(ticket)

    def close_ticket(
        self,
        tenant_id: UUID,
        ticket_id: UUID,
        payload: TicketCloseRequest,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> TicketResponse:
        ticket = self.ticket_repo.get_by_id(ticket_id, tenant_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        if ticket.status == "closed":
            raise ValidationError("Ticket is already closed")
        now = datetime.now(timezone.utc)
        ticket.status = "closed"
        ticket.closed_at = now
        ticket.resolved_at = now
        ticket.updated_by = str(actor_id)
        if payload.resolution_note:
            reply = TicketReply(
                tenant_id=str(tenant_id),
                ticket_id=str(ticket_id),
                author_id=str(actor_id),
                message=payload.resolution_note,
                is_internal=False,
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.reply_repo.add(reply)
        self._log("helpdesk.ticket.close", tenant_id, actor_id, str(ticket_id), meta)
        self.db.commit()
        self.db.refresh(ticket)
        return TicketResponse.model_validate(ticket)

    def list_replies(self, tenant_id: UUID, ticket_id: UUID) -> list[TicketReplyResponse]:
        if not self.ticket_repo.get_by_id(ticket_id, tenant_id):
            raise NotFoundError("Ticket not found")
        items = self.reply_repo.list_for_ticket(tenant_id, ticket_id)
        return [TicketReplyResponse.model_validate(i) for i in items]
