from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.exit import ExitClearance
from app.repositories.extended_repository import (
    AnnouncementRepository,
    AssetAssignmentRepository,
    AssetRepository,
    CommunicationLogRepository,
    CommunicationTemplateRepository,
    ExitClearanceRepository,
    ExitInterviewRepository,
    ExpenseAdvanceRepository,
    ExpenseClaimRepository,
    ExpensePolicyRepository,
    ResignationRepository,
    TravelPolicyRepository,
    TravelRequestRepository,
)
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.assets import (
    AssetAssignmentCreate,
    AssetAssignmentResponse,
    AssetAssignmentUpdate,
    AssetCreate,
    AssetResponse,
    AssetUpdate,
)
from app.schemas.communication import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
    CommunicationLogCreate,
    CommunicationLogResponse,
    CommunicationLogUpdate,
    CommunicationTemplateCreate,
    CommunicationTemplateResponse,
    CommunicationTemplateUpdate,
)
from app.schemas.exit import (
    ExitClearanceResponse,
    ExitClearanceUpdate,
    ExitInterviewCreate,
    ExitInterviewResponse,
    ExitInterviewUpdate,
    ResignationCreate,
    ResignationResponse,
    ResignationUpdate,
)
from app.schemas.expenses import (
    ExpenseAdvanceCreate,
    ExpenseAdvanceResponse,
    ExpenseAdvanceUpdate,
    ExpenseClaimCreate,
    ExpenseClaimResponse,
    ExpenseClaimUpdate,
    ExpensePolicyCreate,
    ExpensePolicyResponse,
    ExpensePolicyUpdate,
)
from app.schemas.travel import (
    TravelPolicyCreate,
    TravelPolicyResponse,
    TravelPolicyUpdate,
    TravelRequestCreate,
    TravelRequestResponse,
    TravelRequestUpdate,
)
from app.services.audit_service import AuditService
from app.services.company_setup.base import TenantScopedCRUDService, _coerce_payload


class ExpensesService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.employee_repo = EmployeeRepository(db)
        self.audit = AuditService(db)
        self.policies = TenantScopedCRUDService(
            db, ExpensePolicyRepository(db), response_schema=ExpensePolicyResponse, resource_type="expense_policy"
        )
        self.claims = TenantScopedCRUDService(
            db, ExpenseClaimRepository(db), response_schema=ExpenseClaimResponse, resource_type="expense_claim"
        )
        self.advances = TenantScopedCRUDService(
            db, ExpenseAdvanceRepository(db), response_schema=ExpenseAdvanceResponse, resource_type="expense_advance"
        )

    def create_claim(self, tenant_id: UUID, payload: ExpenseClaimCreate, *, actor_id: UUID, meta: Optional[dict] = None) -> ExpenseClaimResponse:
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        return self.claims.create(tenant_id, payload, actor_id=actor_id, meta=meta)

    def update_claim(self, tenant_id: UUID, claim_id: UUID, payload: ExpenseClaimUpdate, *, actor_id: UUID, meta: Optional[dict] = None) -> ExpenseClaimResponse:
        return self.claims.update(tenant_id, claim_id, payload, actor_id=actor_id, meta=meta)

    def create_advance(self, tenant_id: UUID, payload: ExpenseAdvanceCreate, *, actor_id: UUID, meta: Optional[dict] = None) -> ExpenseAdvanceResponse:
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        return self.advances.create(tenant_id, payload, actor_id=actor_id, meta=meta)

    def update_advance(self, tenant_id: UUID, advance_id: UUID, payload: ExpenseAdvanceUpdate, *, actor_id: UUID, meta: Optional[dict] = None) -> ExpenseAdvanceResponse:
        return self.advances.update(tenant_id, advance_id, payload, actor_id=actor_id, meta=meta)


class TravelService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.employee_repo = EmployeeRepository(db)
        self.policies = TenantScopedCRUDService(
            db, TravelPolicyRepository(db), response_schema=TravelPolicyResponse, resource_type="travel_policy"
        )
        self.requests = TenantScopedCRUDService(
            db, TravelRequestRepository(db), response_schema=TravelRequestResponse, resource_type="travel_request"
        )

    def create_request(self, tenant_id: UUID, payload: TravelRequestCreate, *, actor_id: UUID, meta: Optional[dict] = None) -> TravelRequestResponse:
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        return self.requests.create(tenant_id, payload, actor_id=actor_id, meta=meta)

    def update_request(self, tenant_id: UUID, request_id: UUID, payload: TravelRequestUpdate, *, actor_id: UUID, meta: Optional[dict] = None) -> TravelRequestResponse:
        return self.requests.update(tenant_id, request_id, payload, actor_id=actor_id, meta=meta)


class AssetsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.employee_repo = EmployeeRepository(db)
        self.asset_repo = AssetRepository(db)
        self.assignment_repo = AssetAssignmentRepository(db)
        self.audit = AuditService(db)
        self.assets = TenantScopedCRUDService(
            db, self.asset_repo, response_schema=AssetResponse, resource_type="asset"
        )
        self.assignments = TenantScopedCRUDService(
            db, self.assignment_repo, response_schema=AssetAssignmentResponse, resource_type="asset_assignment"
        )

    def create_assignment(self, tenant_id: UUID, payload: AssetAssignmentCreate, *, actor_id: UUID, meta: Optional[dict] = None) -> AssetAssignmentResponse:
        if not self.asset_repo.get_by_id(payload.asset_id, tenant_id):
            raise NotFoundError("Asset not found")
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        return self.assignments.create(tenant_id, payload, actor_id=actor_id, meta=meta)

    def update_assignment(self, tenant_id: UUID, assignment_id: UUID, payload: AssetAssignmentUpdate, *, actor_id: UUID, meta: Optional[dict] = None) -> AssetAssignmentResponse:
        return self.assignments.update(tenant_id, assignment_id, payload, actor_id=actor_id, meta=meta)


class CommunicationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.announcement_repo = AnnouncementRepository(db)
        self.announcements = TenantScopedCRUDService(
            db, self.announcement_repo, response_schema=AnnouncementResponse, resource_type="announcement"
        )
        self.templates = TenantScopedCRUDService(
            db,
            CommunicationTemplateRepository(db),
            response_schema=CommunicationTemplateResponse,
            resource_type="communication_template",
        )
        self.logs = TenantScopedCRUDService(
            db, CommunicationLogRepository(db), response_schema=CommunicationLogResponse, resource_type="communication_log"
        )
        self.audit = AuditService(db)

    def send_announcement(
        self,
        tenant_id: UUID,
        announcement_id: UUID,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
        channels: Optional[list[str]] = None,
    ) -> AnnouncementResponse:
        from app.models.communication import CommunicationLog
        from app.models.employee import Employee
        from app.services.notification_service import notify_channels

        announcement = self.announcement_repo.get_by_id(announcement_id, tenant_id)
        if not announcement:
            raise NotFoundError("Announcement not found")

        selected_channels = channels or ["email", "sms", "whatsapp", "in_app"]

        employees = list(
            self.db.scalars(
                select(Employee).where(
                    Employee.tenant_id == str(tenant_id),
                    Employee.deleted_at.is_(None),
                    Employee.status == "active",
                )
            ).all()
        )

        sent_count = 0
        for employee in employees:
            results = notify_channels(
                email=employee.email,
                mobile=employee.mobile,
                subject=announcement.title,
                body=announcement.body,
                channels=selected_channels,
            )
            for channel, ok in results.items():
                log = CommunicationLog(
                    tenant_id=str(tenant_id),
                    recipient_email=employee.email,
                    channel=channel,
                    subject=announcement.title,
                    body=announcement.body,
                    status="sent" if ok else "failed",
                    sent_at=datetime.now(timezone.utc) if ok else None,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                )
                self.db.add(log)
                if ok:
                    sent_count += 1

        announcement.status = "published"
        announcement.published_at = datetime.now(timezone.utc)
        announcement.updated_by = str(actor_id)

        self.audit.log(
            "communication.announcement.send",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="announcement",
            resource_id=str(announcement.id),
            details={"recipients": sent_count},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(announcement)
        return AnnouncementResponse.model_validate(announcement)


class ExitService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.employee_repo = EmployeeRepository(db)
        self.resignation_repo = ResignationRepository(db)
        self.clearance_repo = ExitClearanceRepository(db)
        self.interview_repo = ExitInterviewRepository(db)
        self.audit = AuditService(db)
        self.resignations = TenantScopedCRUDService(
            db, self.resignation_repo, response_schema=ResignationResponse, resource_type="resignation"
        )
        self.interviews = TenantScopedCRUDService(
            db, self.interview_repo, response_schema=ExitInterviewResponse, resource_type="exit_interview"
        )

    def create_resignation(self, tenant_id: UUID, payload: ResignationCreate, *, actor_id: UUID, meta: Optional[dict] = None) -> ResignationResponse:
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        return self.resignations.create(tenant_id, payload, actor_id=actor_id, meta=meta)

    def update_resignation(self, tenant_id: UUID, resignation_id: UUID, payload: ResignationUpdate, *, actor_id: UUID, meta: Optional[dict] = None) -> ResignationResponse:
        return self.resignations.update(tenant_id, resignation_id, payload, actor_id=actor_id, meta=meta)

    def get_clearance(self, tenant_id: UUID, resignation_id: UUID) -> ExitClearanceResponse:
        if not self.resignation_repo.get_by_id(resignation_id, tenant_id):
            raise NotFoundError("Resignation not found")
        clearance = self.clearance_repo.get_by_resignation(tenant_id, resignation_id)
        if not clearance:
            return ExitClearanceResponse(
                id=resignation_id,
                tenant_id=tenant_id,
                resignation_id=resignation_id,
                checklist=[],
                status="pending",
                cleared_at=None,
                created_at=datetime.now(timezone.utc),
            )
        return self._clearance_response(clearance)

    def update_clearance(
        self,
        tenant_id: UUID,
        resignation_id: UUID,
        payload: ExitClearanceUpdate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> ExitClearanceResponse:
        if not self.resignation_repo.get_by_id(resignation_id, tenant_id):
            raise NotFoundError("Resignation not found")

        clearance = self.clearance_repo.get_by_resignation(tenant_id, resignation_id)
        data = payload.model_dump(exclude_unset=True)
        checklist = data.pop("checklist", None)

        if clearance:
            if checklist is not None:
                clearance.checklist_json = json.dumps(checklist)
            for key, value in data.items():
                setattr(clearance, key, value)
            if data.get("status") == "cleared":
                clearance.cleared_at = datetime.now(timezone.utc)
            clearance.updated_by = str(actor_id)
            entity = clearance
        else:
            entity = ExitClearance(
                tenant_id=str(tenant_id),
                resignation_id=str(resignation_id),
                checklist_json=json.dumps(checklist or []),
                status=data.get("status", "pending"),
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            if entity.status == "cleared":
                entity.cleared_at = datetime.now(timezone.utc)
            self.clearance_repo.add(entity)

        self.audit.log(
            "exit.clearance.update",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="exit_clearance",
            resource_id=str(entity.id),
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(entity)
        return self._clearance_response(entity)

    def create_interview(self, tenant_id: UUID, payload: ExitInterviewCreate, *, actor_id: UUID, meta: Optional[dict] = None) -> ExitInterviewResponse:
        if not self.resignation_repo.get_by_id(payload.resignation_id, tenant_id):
            raise NotFoundError("Resignation not found")
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        return self.interviews.create(tenant_id, payload, actor_id=actor_id, meta=meta)

    def update_interview(self, tenant_id: UUID, interview_id: UUID, payload: ExitInterviewUpdate, *, actor_id: UUID, meta: Optional[dict] = None) -> ExitInterviewResponse:
        return self.interviews.update(tenant_id, interview_id, payload, actor_id=actor_id, meta=meta)

    def _clearance_response(self, entity: ExitClearance) -> ExitClearanceResponse:
        return ExitClearanceResponse(
            id=UUID(entity.id),
            tenant_id=UUID(entity.tenant_id),
            resignation_id=UUID(entity.resignation_id),
            checklist=json.loads(entity.checklist_json or "[]"),
            status=entity.status,
            cleared_at=entity.cleared_at,
            created_at=entity.created_at,
        )
