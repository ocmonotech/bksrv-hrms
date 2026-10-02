from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import EmployeeStatus, TimelineEventType
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.employee import (
    Employee,
    EmployeeBankDetail,
    EmployeeDocument,
    EmployeeEducation,
    EmployeeExperience,
    EmployeeFamilyDetail,
    EmployeeJobDetail,
    EmployeePersonalDetail,
    EmployeeProfileUpdateRequest,
    EmployeeSalaryDetail,
    EmployeeStatutoryDetail,
    EmployeeTimeline,
)
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.common import PaginatedResponse
from app.schemas.employee import (
    DocumentResponse,
    EmployeeCreate,
    EmployeeListItem,
    EmployeeProfileResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
    TimelineResponse,
)
from app.services.audit_service import AuditService
from app.utils.file_storage import employee_document_relative_path, save_upload_file
from app.utils.pagination import total_pages


SENSITIVE_PERSONAL_FIELDS = {"pan_number", "aadhaar_number", "bank_detail", "salary_detail", "statutory_detail"}


class EmployeeService:
    resource_type = "employee"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EmployeeRepository(db)
        self.audit = AuditService(db)

    def list_employees(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        status: Optional[str] = None,
        employment_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[EmployeeListItem]:
        items, total = self.repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            search=search,
            branch_id=branch_id,
            department_id=department_id,
            status=status,
            employment_type=employment_type,
            is_active=is_active,
        )
        return PaginatedResponse(
            data=[EmployeeListItem.model_validate(e) for e in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def get_employee(self, tenant_id: UUID, employee_id: UUID) -> EmployeeProfileResponse:
        employee = self.repo.get_profile(employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")
        return self._to_profile(employee)

    def create_employee(
        self,
        tenant_id: UUID,
        payload: EmployeeCreate,
        *,
        actor_id: UUID,
        company_id: Optional[UUID] = None,
        meta: Optional[dict] = None,
    ) -> EmployeeProfileResponse:
        email = payload.email.lower()
        if self.repo.get_by_email(tenant_id, email):
            raise ConflictError(f"Employee with email '{email}' already exists")

        code = payload.employee_code.upper() if payload.employee_code else self.repo.next_employee_code(tenant_id)
        if self.repo.get_by_code(tenant_id, code):
            raise ConflictError(f"Employee code '{code}' already exists")

        if payload.reporting_manager_id:
            self._ensure_manager(tenant_id, payload.reporting_manager_id)

        core = payload.model_dump(
            exclude={
                "employee_code",
                "email",
                "company_id",
                "personal_detail",
                "job_detail",
                "bank_detail",
                "salary_detail",
                "statutory_detail",
                "family_members",
                "education",
                "experience",
            }
        )
        for fk in (
            "company_id",
            "branch_id",
            "department_id",
            "designation_id",
            "grade_id",
            "reporting_manager_id",
        ):
            if core.get(fk):
                core[fk] = str(core[fk])

        resolved_company = company_id or payload.company_id
        employee = Employee(
            tenant_id=str(tenant_id),
            employee_code=code,
            email=email,
            created_by=str(actor_id),
            updated_by=str(actor_id),
            company_id=str(resolved_company) if resolved_company else None,
            **core,
        )

        self.repo.add(employee)
        self._apply_nested_create(employee, payload, actor_id)
        self._add_timeline(
            employee,
            TimelineEventType.CREATED.value,
            "Employee created",
            f"Employee {code} onboarded",
            actor_id,
        )
        self._audit("create", tenant_id, actor_id, employee.id, meta)
        self.db.commit()
        return self.get_employee(tenant_id, employee.id)

    def update_employee(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        payload: EmployeeUpdate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> EmployeeProfileResponse:
        employee = self.repo.get_profile(employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")

        data = payload.model_dump(
            exclude={
                "personal_detail",
                "job_detail",
                "bank_detail",
                "salary_detail",
                "statutory_detail",
                "submit_profile_update_request",
            },
            exclude_unset=True,
        )

        if payload.submit_profile_update_request and self._has_sensitive_changes(payload):
            self._create_profile_update_request(employee, payload, actor_id)
            self.db.commit()
            return self.get_employee(tenant_id, employee_id)

        if "email" in data and data["email"]:
            existing = self.repo.get_by_email(tenant_id, data["email"])
            if existing and str(existing.id) != str(employee_id):
                raise ConflictError("Email already in use by another employee")
            data["email"] = data["email"].lower()

        if payload.reporting_manager_id:
            if str(payload.reporting_manager_id) == str(employee_id):
                raise ValidationError("Employee cannot be their own reporting manager")
            self._ensure_manager(tenant_id, payload.reporting_manager_id)

        for fk in (
            "branch_id",
            "department_id",
            "designation_id",
            "grade_id",
            "reporting_manager_id",
        ):
            if fk in data and data[fk]:
                data[fk] = str(data[fk])

        for key, value in data.items():
            setattr(employee, key, value)
        employee.updated_by = str(actor_id)

        if payload.personal_detail:
            self._upsert_personal(employee, payload.personal_detail.model_dump(), actor_id)
        if payload.job_detail:
            self._upsert_job(employee, payload.job_detail.model_dump(), actor_id)
        if payload.bank_detail:
            self._upsert_bank(employee, payload.bank_detail.model_dump(), actor_id)
        if payload.salary_detail:
            self._upsert_salary(employee, payload.salary_detail.model_dump(), actor_id)
        if payload.statutory_detail:
            self._upsert_statutory(employee, payload.statutory_detail.model_dump(), actor_id)

        self._add_timeline(
            employee,
            TimelineEventType.UPDATED.value,
            "Employee updated",
            "Profile information updated",
            actor_id,
        )
        self._audit("update", tenant_id, actor_id, employee.id, meta, details=data)
        self.db.commit()
        return self.get_employee(tenant_id, employee_id)

    def delete_employee(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> None:
        employee = self.repo.get_by_id(employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")
        self.repo.soft_delete(employee, updated_by=actor_id)
        employee.is_active = False
        employee.status = EmployeeStatus.INACTIVE.value
        self._audit("delete", tenant_id, actor_id, employee.id, meta)
        self.db.commit()

    def update_status(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        payload: EmployeeStatusUpdate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> EmployeeProfileResponse:
        employee = self.repo.get_by_id(employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")

        old_status = employee.status
        employee.status = payload.status
        employee.updated_by = str(actor_id)
        if payload.exit_date:
            employee.exit_date = payload.exit_date
        employee.is_active = payload.status in (
            EmployeeStatus.ACTIVE.value,
            EmployeeStatus.PROBATION.value,
            EmployeeStatus.ON_NOTICE.value,
        )

        self._add_timeline(
            employee,
            TimelineEventType.STATUS_CHANGED.value,
            f"Status changed to {payload.status}",
            payload.reason or f"Changed from {old_status} to {payload.status}",
            actor_id,
            metadata={"old_status": old_status, "new_status": payload.status},
        )
        self._audit("status_change", tenant_id, actor_id, employee.id, meta, details=payload.model_dump())
        self.db.commit()
        return self.get_employee(tenant_id, employee_id)

    def upload_document(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        *,
        document_type: str,
        title: str,
        file_name: str,
        content: bytes,
        mime_type: Optional[str],
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> DocumentResponse:
        employee = self.repo.get_by_id(employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")

        relative_path = employee_document_relative_path(
            str(tenant_id), str(employee_id), document_type, file_name
        )
        save_upload_file(relative_path, content)

        doc = EmployeeDocument(
            tenant_id=str(tenant_id),
            employee_id=employee.id,
            document_type=document_type,
            title=title,
            file_path=relative_path,
            file_name=file_name,
            mime_type=mime_type,
            file_size=len(content),
            uploaded_by=str(actor_id),
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.db.add(doc)
        self._add_timeline(
            employee,
            TimelineEventType.DOCUMENT_UPLOADED.value,
            f"Document uploaded: {title}",
            document_type,
            actor_id,
            metadata={"document_type": document_type, "file_name": file_name},
        )
        self._audit("document_upload", tenant_id, actor_id, employee.id, meta, details={"title": title})
        self.db.commit()
        self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    def get_timeline(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[TimelineResponse]:
        employee = self.repo.get_by_id(employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")

        from sqlalchemy import select

        stmt = (
            select(EmployeeTimeline)
            .where(
                EmployeeTimeline.employee_id == str(employee_id),
                EmployeeTimeline.tenant_id == str(tenant_id),
            )
            .order_by(EmployeeTimeline.occurred_at.desc())
        )
        from app.utils.pagination import paginate_stmt

        items, total = paginate_stmt(self.db, stmt, page=page, page_size=page_size)
        return PaginatedResponse(
            data=[TimelineResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def _apply_nested_create(self, employee: Employee, payload: EmployeeCreate, actor_id: UUID) -> None:
        tid = employee.tenant_id
        if payload.personal_detail:
            self.db.add(
                EmployeePersonalDetail(
                    tenant_id=tid,
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **payload.personal_detail.model_dump(),
                )
            )
        if payload.job_detail:
            jd = payload.job_detail.model_dump()
            cc = jd.pop("cost_center_id", None)
            self.db.add(
                EmployeeJobDetail(
                    tenant_id=tid,
                    employee_id=employee.id,
                    cost_center_id=str(cc) if cc else None,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **jd,
                )
            )
        if payload.bank_detail:
            self.db.add(
                EmployeeBankDetail(
                    tenant_id=tid,
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **payload.bank_detail.model_dump(),
                )
            )
        if payload.salary_detail:
            self.db.add(
                EmployeeSalaryDetail(
                    tenant_id=tid,
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **payload.salary_detail.model_dump(),
                )
            )
        if payload.statutory_detail:
            self.db.add(
                EmployeeStatutoryDetail(
                    tenant_id=tid,
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **payload.statutory_detail.model_dump(),
                )
            )
        for fm in payload.family_members or []:
            fm_data = fm.model_dump()
            rel = fm_data.pop("relationship", fm_data.pop("relation_type", None))
            self.db.add(
                EmployeeFamilyDetail(
                    tenant_id=tid,
                    employee_id=employee.id,
                    relation_type=rel,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **fm_data,
                )
            )
        for edu in payload.education or []:
            self.db.add(
                EmployeeEducation(
                    tenant_id=tid,
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **edu.model_dump(),
                )
            )
        for exp in payload.experience or []:
            self.db.add(
                EmployeeExperience(
                    tenant_id=tid,
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **exp.model_dump(),
                )
            )

    def _upsert_personal(self, employee: Employee, data: dict, actor_id: UUID) -> None:
        if employee.personal_detail:
            for k, v in data.items():
                setattr(employee.personal_detail, k, v)
            employee.personal_detail.updated_by = str(actor_id)
        else:
            self.db.add(
                EmployeePersonalDetail(
                    tenant_id=str(employee.tenant_id),
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **data,
                )
            )

    def _upsert_job(self, employee: Employee, data: dict, actor_id: UUID) -> None:
        cc = data.pop("cost_center_id", None)
        if cc:
            data["cost_center_id"] = str(cc)
        if employee.job_detail:
            for k, v in data.items():
                setattr(employee.job_detail, k, v)
            employee.job_detail.updated_by = str(actor_id)
        else:
            self.db.add(
                EmployeeJobDetail(
                    tenant_id=str(employee.tenant_id),
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **data,
                )
            )

    def _upsert_bank(self, employee: Employee, data: dict, actor_id: UUID) -> None:
        if employee.bank_detail:
            for k, v in data.items():
                setattr(employee.bank_detail, k, v)
            employee.bank_detail.updated_by = str(actor_id)
        else:
            self.db.add(
                EmployeeBankDetail(
                    tenant_id=str(employee.tenant_id),
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **data,
                )
            )

    def _upsert_salary(self, employee: Employee, data: dict, actor_id: UUID) -> None:
        if employee.salary_detail:
            for k, v in data.items():
                setattr(employee.salary_detail, k, v)
            employee.salary_detail.updated_by = str(actor_id)
        else:
            self.db.add(
                EmployeeSalaryDetail(
                    tenant_id=str(employee.tenant_id),
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **data,
                )
            )
        self._add_timeline(
            employee,
            TimelineEventType.SALARY_UPDATED.value,
            "Salary details updated",
            None,
            UUID(str(actor_id)) if actor_id else None,
        )

    def _upsert_statutory(self, employee: Employee, data: dict, actor_id: UUID) -> None:
        if employee.statutory_detail:
            for k, v in data.items():
                setattr(employee.statutory_detail, k, v)
            employee.statutory_detail.updated_by = str(actor_id)
        else:
            self.db.add(
                EmployeeStatutoryDetail(
                    tenant_id=str(employee.tenant_id),
                    employee_id=employee.id,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                    **data,
                )
            )

    def _create_profile_update_request(
        self, employee: Employee, payload: EmployeeUpdate, actor_id: UUID
    ) -> None:
        changes = payload.model_dump(exclude_unset=True)
        req = EmployeeProfileUpdateRequest(
            tenant_id=str(employee.tenant_id),
            employee_id=employee.id,
            requested_by=str(actor_id),
            status="pending",
            changes_json=json.dumps(changes, default=str),
        )
        self.db.add(req)
        self._add_timeline(
            employee,
            TimelineEventType.PROFILE_UPDATE_REQUESTED.value,
            "Profile update requested",
            "Pending HR approval",
            actor_id,
        )

    def _has_sensitive_changes(self, payload: EmployeeUpdate) -> bool:
        data = payload.model_dump(exclude_unset=True)
        return bool(SENSITIVE_PERSONAL_FIELDS.intersection(data.keys()))

    def _ensure_manager(self, tenant_id: UUID, manager_id: UUID) -> None:
        manager = self.repo.get_by_id(manager_id, tenant_id)
        if not manager:
            raise ValidationError("Reporting manager not found in this tenant")

    def _add_timeline(
        self,
        employee: Employee,
        event_type: str,
        title: str,
        description: Optional[str],
        actor_id: UUID,
        metadata: Optional[dict] = None,
    ) -> None:
        self.db.add(
            EmployeeTimeline(
                tenant_id=str(employee.tenant_id),
                employee_id=employee.id,
                event_type=event_type,
                title=title,
                description=description,
                metadata_json=json.dumps(metadata) if metadata else None,
                actor_id=str(actor_id),
                occurred_at=datetime.now(timezone.utc),
            )
        )

    def _to_profile(self, employee: Employee) -> EmployeeProfileResponse:
        return EmployeeProfileResponse.model_validate(employee)

    def _audit(
        self,
        action: str,
        tenant_id: UUID,
        actor_id: UUID,
        entity_id: UUID,
        meta: Optional[dict],
        details: Optional[dict] = None,
    ) -> None:
        self.audit.log(
            f"employee.{action}",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type=self.resource_type,
            resource_id=str(entity_id),
            details=details,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
