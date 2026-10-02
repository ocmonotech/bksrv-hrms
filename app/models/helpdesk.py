from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class TicketCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "ticket_categories"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    default_sla_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_ticket_categories_tenant_code"),)


class Ticket(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "helpdesk_tickets"

    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("ticket_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ticket_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False, index=True)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "ticket_number", name="uq_helpdesk_tickets_tenant_number"),)


class TicketReply(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "ticket_replies"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("helpdesk_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TicketAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "ticket_assignments"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("helpdesk_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_to: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class TicketSLA(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "ticket_slas"

    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        CHAR(36), ForeignKey("ticket_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    priority: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    response_hours: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    resolution_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "category_id", "priority", name="uq_ticket_slas_tenant_category_priority"),
    )
