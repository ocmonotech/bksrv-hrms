from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.constants.india import INDIA_DEFAULTS
from app.core.exceptions import NotFoundError, ValidationError
from app.models.company_setup import (
    ApprovalStep,
    ApprovalWorkflow,
    Branch,
    CompanyProfile,
    CostCenter,
    Department,
    Designation,
    Grade,
    Holiday,
    Policy,
)
from app.repositories.tenant_scoped_repository import TenantScopedRepository
from app.schemas.company_setup import (
    ApprovalWorkflowCreate,
    ApprovalWorkflowResponse,
    ApprovalWorkflowSummary,
    ApprovalWorkflowUpdate,
    BranchCreate,
    BranchResponse,
    BranchUpdate,
    CompanyProfileCreate,
    CompanyProfileResponse,
    CompanyProfileUpdate,
    CostCenterCreate,
    CostCenterResponse,
    CostCenterUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
    GradeCreate,
    GradeResponse,
    GradeUpdate,
    HolidayCreate,
    HolidayResponse,
    HolidayUpdate,
    PolicyCreate,
    PolicyResponse,
    PolicyUpdate,
)
from app.services.audit_service import AuditService
from app.services.company_setup.base import TenantScopedCRUDService
from app.schemas.common import PaginatedResponse
from app.utils.pagination import total_pages


class CompanyProfileService:
    resource_type = "company_profile"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def get_profile(self, tenant_id: UUID) -> CompanyProfileResponse:
        stmt = select(CompanyProfile).where(
            CompanyProfile.tenant_id == str(tenant_id),
            CompanyProfile.deleted_at.is_(None),
        )
        profile = self.db.scalar(stmt)
        if not profile:
            raise NotFoundError("Company profile not found for this tenant")
        return CompanyProfileResponse.model_validate(profile)

    def upsert_profile(
        self,
        tenant_id: UUID,
        payload: CompanyProfileUpdate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> CompanyProfileResponse:
        stmt = select(CompanyProfile).where(
            CompanyProfile.tenant_id == str(tenant_id),
            CompanyProfile.deleted_at.is_(None),
        )
        profile = self.db.scalar(stmt)
        data = payload.model_dump(exclude_unset=True)

        if profile:
            for key, value in data.items():
                setattr(profile, key, value)
            profile.updated_by = str(actor_id)
            action = "update"
        else:
            if "display_name" not in data:
                raise ValidationError("display_name is required when creating a new profile")
            for key, value in INDIA_DEFAULTS.items():
                data.setdefault(key, value)
            profile = CompanyProfile(
                tenant_id=str(tenant_id),
                created_by=str(actor_id),
                updated_by=str(actor_id),
                **data,
            )
            self.db.add(profile)
            action = "create"

        self.db.flush()
        self.audit.log(
            f"company_setup.{self.resource_type}.{action}",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type=self.resource_type,
            resource_id=str(profile.id),
            details=data,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(profile)
        return CompanyProfileResponse.model_validate(profile)


class ApprovalWorkflowService(TenantScopedCRUDService[ApprovalWorkflow, ApprovalWorkflowCreate, ApprovalWorkflowUpdate, ApprovalWorkflowResponse]):
    def __init__(self, db: Session) -> None:
        super().__init__(
            db,
            TenantScopedRepository(db, ApprovalWorkflow, search_fields=("name", "code", "entity_type")),
            response_schema=ApprovalWorkflowResponse,
            resource_type="approval_workflow",
        )

    def list(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[ApprovalWorkflowSummary]:
        items, total = self.repo.list_paginated(
            tenant_id, page=page, page_size=page_size, search=search, is_active=is_active
        )
        return PaginatedResponse(
            data=[ApprovalWorkflowSummary.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def get(self, tenant_id: UUID, entity_id: UUID) -> ApprovalWorkflowResponse:
        stmt = (
            select(ApprovalWorkflow)
            .options(joinedload(ApprovalWorkflow.steps))
            .where(
                ApprovalWorkflow.id == str(entity_id),
                ApprovalWorkflow.tenant_id == str(tenant_id),
                ApprovalWorkflow.deleted_at.is_(None),
            )
        )
        entity = self.db.scalar(stmt)
        if not entity:
            raise NotFoundError("approval_workflow not found")
        return ApprovalWorkflowResponse.model_validate(entity)

    def create(
        self,
        tenant_id: UUID,
        payload: ApprovalWorkflowCreate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
        before_save=None,
    ) -> ApprovalWorkflowResponse:
        data = payload.model_dump(exclude={"steps"})
        steps_data = payload.steps
        if self.repo.get_by_code(tenant_id, data["code"].upper()):
            from app.core.exceptions import ConflictError
            raise ConflictError(f"approval_workflow with code '{data['code']}' already exists")

        workflow = ApprovalWorkflow(
            tenant_id=str(tenant_id),
            created_by=str(actor_id),
            updated_by=str(actor_id),
            name=data["name"],
            code=data["code"].upper(),
            entity_type=data["entity_type"],
            description=data.get("description"),
            is_active=data.get("is_active", True),
        )
        self.repo.add(workflow)
        self._sync_steps(workflow, tenant_id, steps_data, actor_id)
        self._audit("create", tenant_id, actor_id, workflow.id, meta)
        self.db.commit()
        return self.get(tenant_id, workflow.id)

    def update(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        payload: ApprovalWorkflowUpdate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> ApprovalWorkflowResponse:
        workflow = self.repo.get_by_id(entity_id, tenant_id)
        if not workflow:
            raise NotFoundError("approval_workflow not found")

        data = payload.model_dump(exclude={"steps"}, exclude_unset=True)
        if "code" in data:
            data["code"] = data["code"].upper()
            existing = self.repo.get_by_code(tenant_id, data["code"])
            if existing and str(existing.id) != str(entity_id):
                from app.core.exceptions import ConflictError
                raise ConflictError(f"approval_workflow with code '{data['code']}' already exists")

        for key, value in data.items():
            setattr(workflow, key, value)
        workflow.updated_by = str(actor_id)

        if payload.steps is not None:
            for step in list(workflow.steps):
                self.repo.soft_delete(step, updated_by=actor_id)
            self._sync_steps(workflow, tenant_id, payload.steps, actor_id)

        self._audit("update", tenant_id, actor_id, workflow.id, meta, details=data)
        self.db.commit()
        return self.get(tenant_id, entity_id)

    def _sync_steps(self, workflow: ApprovalWorkflow, tenant_id: UUID, steps_data, actor_id: UUID) -> None:
        for step_payload in steps_data:
            step = ApprovalStep(
                tenant_id=str(tenant_id),
                workflow_id=workflow.id,
                created_by=str(actor_id),
                updated_by=str(actor_id),
                **step_payload.model_dump(),
            )
            self.db.add(step)


def build_company_setup_services(db: Session) -> dict:
    """Factory for all company setup CRUD services."""
    return {
        "profile": CompanyProfileService(db),
        "branch": TenantScopedCRUDService(
            db,
            TenantScopedRepository(db, Branch),
            response_schema=BranchResponse,
            resource_type="branch",
        ),
        "department": TenantScopedCRUDService(
            db,
            TenantScopedRepository(db, Department),
            response_schema=DepartmentResponse,
            resource_type="department",
        ),
        "designation": TenantScopedCRUDService(
            db,
            TenantScopedRepository(db, Designation),
            response_schema=DesignationResponse,
            resource_type="designation",
        ),
        "grade": TenantScopedCRUDService(
            db,
            TenantScopedRepository(db, Grade),
            response_schema=GradeResponse,
            resource_type="grade",
        ),
        "cost_center": TenantScopedCRUDService(
            db,
            TenantScopedRepository(db, CostCenter),
            response_schema=CostCenterResponse,
            resource_type="cost_center",
        ),
        "holiday": TenantScopedCRUDService(
            db,
            TenantScopedRepository(db, Holiday, search_fields=("name",)),
            response_schema=HolidayResponse,
            resource_type="holiday",
        ),
        "policy": TenantScopedCRUDService(
            db,
            TenantScopedRepository(db, Policy, search_fields=("title", "code", "category")),
            response_schema=PolicyResponse,
            resource_type="policy",
        ),
        "approval_workflow": ApprovalWorkflowService(db),
    }

# Type aliases for route dependency injection
BranchService = TenantScopedCRUDService
DepartmentService = TenantScopedCRUDService
