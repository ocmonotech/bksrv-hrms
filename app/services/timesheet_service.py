from __future__ import annotations

from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.timesheets import TimesheetEntry, TimesheetProject
from app.repositories.timesheet_repository import TimesheetEntryRepository, TimesheetProjectRepository
from app.schemas.common import PaginatedResponse
from app.schemas.timesheets import (
    TimesheetDashboardStats,
    TimesheetEntryCreate,
    TimesheetEntryResponse,
    TimesheetEntryUpdate,
    TimesheetProjectCreate,
    TimesheetProjectResponse,
    TimesheetProjectUpdate,
)
from app.services.audit_service import AuditService
from app.services.company_setup.base import _coerce_payload
from app.utils.pagination import total_pages


class TimesheetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.project_repo = TimesheetProjectRepository(db)
        self.entry_repo = TimesheetEntryRepository(db)
        self.audit = AuditService(db)

    def _log(self, action: str, tenant_id: UUID, actor_id: UUID, resource_id: str, meta: Optional[dict]) -> None:
        self.audit.log(
            action,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="timesheet",
            resource_id=resource_id,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )

    def get_dashboard_stats(self, tenant_id: UUID, *, employee_id: Optional[UUID] = None) -> TimesheetDashboardStats:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        return TimesheetDashboardStats(
            total_hours_this_week=self.entry_repo.sum_hours(
                tenant_id, employee_id=employee_id, date_from=week_start, date_to=today
            ),
            pending_approval=self.entry_repo.count_by_status(tenant_id, "submitted", employee_id=employee_id),
            active_projects=len(
                self.project_repo.list_paginated(tenant_id, page=1, page_size=1000, is_active=True)[0]
            ),
            submitted_this_month=self.entry_repo.count_by_status(tenant_id, "submitted", employee_id=employee_id)
            + self.entry_repo.count_by_status(tenant_id, "approved", employee_id=employee_id),
        )

    def create_project(
        self, tenant_id: UUID, payload: TimesheetProjectCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TimesheetProjectResponse:
        code = payload.code.upper()
        if self.project_repo.get_by_code(tenant_id, code):
            raise ConflictError(f"Project '{code}' already exists")
        data = _coerce_payload(payload.model_dump())
        entity = TimesheetProject(
            tenant_id=str(tenant_id),
            code=code,
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **{k: v for k, v in data.items() if k != "code"},
        )
        self.project_repo.add(entity)
        self._log("timesheet.project.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TimesheetProjectResponse.model_validate(entity)

    def list_projects(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20, search: Optional[str] = None, is_active: Optional[bool] = None
    ) -> PaginatedResponse[TimesheetProjectResponse]:
        items, total = self.project_repo.list_paginated(tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)
        return PaginatedResponse(
            data=[TimesheetProjectResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_project(
        self, tenant_id: UUID, project_id: UUID, payload: TimesheetProjectUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TimesheetProjectResponse:
        entity = self.project_repo.get_by_id(project_id, tenant_id)
        if not entity:
            raise NotFoundError("Project not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("timesheet.project.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TimesheetProjectResponse.model_validate(entity)

    def create_entry(
        self, tenant_id: UUID, payload: TimesheetEntryCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TimesheetEntryResponse:
        if not self.project_repo.get_by_id(payload.project_id, tenant_id):
            raise NotFoundError("Project not found")
        data = _coerce_payload(payload.model_dump())
        entity = TimesheetEntry(
            tenant_id=str(tenant_id),
            status="draft",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.entry_repo.add(entity)
        self._log("timesheet.entry.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TimesheetEntryResponse.model_validate(entity)

    def list_entries(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> PaginatedResponse[TimesheetEntryResponse]:
        items, total = self.entry_repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            employee_id=employee_id,
            project_id=project_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        return PaginatedResponse(
            data=[TimesheetEntryResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_entry(
        self, tenant_id: UUID, entry_id: UUID, payload: TimesheetEntryUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> TimesheetEntryResponse:
        entity = self.entry_repo.get_by_id(entry_id, tenant_id)
        if not entity:
            raise NotFoundError("Timesheet entry not found")
        if payload.project_id and not self.project_repo.get_by_id(payload.project_id, tenant_id):
            raise NotFoundError("Project not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("timesheet.entry.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TimesheetEntryResponse.model_validate(entity)

    def submit_entry(self, tenant_id: UUID, entry_id: UUID, *, actor_id: UUID, meta: Optional[dict] = None) -> TimesheetEntryResponse:
        entity = self.entry_repo.get_by_id(entry_id, tenant_id)
        if not entity:
            raise NotFoundError("Timesheet entry not found")
        if entity.status not in ("draft", "rejected"):
            raise ValidationError("Only draft or rejected entries can be submitted")
        entity.status = "submitted"
        entity.updated_by = str(actor_id)
        self._log("timesheet.entry.submit", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TimesheetEntryResponse.model_validate(entity)

    def approve_entry(self, tenant_id: UUID, entry_id: UUID, *, actor_id: UUID, meta: Optional[dict] = None) -> TimesheetEntryResponse:
        entity = self.entry_repo.get_by_id(entry_id, tenant_id)
        if not entity:
            raise NotFoundError("Timesheet entry not found")
        if entity.status != "submitted":
            raise ValidationError("Only submitted entries can be approved")
        entity.status = "approved"
        entity.updated_by = str(actor_id)
        self._log("timesheet.entry.approve", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TimesheetEntryResponse.model_validate(entity)

    def reject_entry(self, tenant_id: UUID, entry_id: UUID, *, actor_id: UUID, meta: Optional[dict] = None) -> TimesheetEntryResponse:
        entity = self.entry_repo.get_by_id(entry_id, tenant_id)
        if not entity:
            raise NotFoundError("Timesheet entry not found")
        if entity.status != "submitted":
            raise ValidationError("Only submitted entries can be rejected")
        entity.status = "rejected"
        entity.updated_by = str(actor_id)
        self._log("timesheet.entry.reject", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return TimesheetEntryResponse.model_validate(entity)
