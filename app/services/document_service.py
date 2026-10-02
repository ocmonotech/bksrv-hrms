from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.documents import (
    CompanyDocument,
    DocumentCategory,
    GeneratedLetter,
    LetterTemplate,
    LibraryEmployeeDocument,
)
from app.repositories.document_repository import (
    CompanyDocumentRepository,
    DocumentCategoryRepository,
    EmployeeDocumentRepository,
    GeneratedLetterRepository,
    LetterTemplateRepository,
)
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.common import PaginatedResponse
from app.schemas.documents import (
    CompanyDocumentCreate,
    CompanyDocumentResponse,
    DocumentCategoryCreate,
    DocumentCategoryResponse,
    DocumentCategoryUpdate,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    GeneratedLetterCreate,
    GeneratedLetterResponse,
    LetterTemplateCreate,
    LetterTemplateResponse,
    LetterTemplateUpdate,
)
from app.services.audit_service import AuditService
from app.services.company_setup.base import _coerce_payload
from app.utils.file_storage import company_document_relative_path, employee_library_relative_path, save_upload_file
from app.utils.pagination import total_pages


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.category_repo = DocumentCategoryRepository(db)
        self.employee_doc_repo = EmployeeDocumentRepository(db)
        self.company_doc_repo = CompanyDocumentRepository(db)
        self.template_repo = LetterTemplateRepository(db)
        self.generated_repo = GeneratedLetterRepository(db)
        self.employee_repo = EmployeeRepository(db)
        self.audit = AuditService(db)

    def _log(self, action: str, tenant_id: UUID, actor_id: UUID, resource_id: str, meta: Optional[dict]) -> None:
        self.audit.log(
            action,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="documents",
            resource_id=resource_id,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )

    # --- Categories ---

    def create_category(
        self, tenant_id: UUID, payload: DocumentCategoryCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> DocumentCategoryResponse:
        code = payload.code.upper()
        if self.category_repo.get_by_code(tenant_id, code):
            raise ConflictError(f"Category '{code}' already exists")
        data = _coerce_payload(payload.model_dump())
        entity = DocumentCategory(
            tenant_id=str(tenant_id),
            code=code,
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **{k: v for k, v in data.items() if k != "code"},
        )
        self.category_repo.add(entity)
        self._log("documents.category.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return DocumentCategoryResponse.model_validate(entity)

    def list_categories(
        self, tenant_id: UUID, *, page: int = 1, page_size: int = 20, search: Optional[str] = None, is_active: Optional[bool] = None
    ) -> PaginatedResponse[DocumentCategoryResponse]:
        items, total = self.category_repo.list_paginated(tenant_id, page=page, page_size=page_size, search=search, is_active=is_active)
        return PaginatedResponse(
            data=[DocumentCategoryResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_category(
        self, tenant_id: UUID, category_id: UUID, payload: DocumentCategoryUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> DocumentCategoryResponse:
        entity = self.category_repo.get_by_id(category_id, tenant_id)
        if not entity:
            raise NotFoundError("Category not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("documents.category.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return DocumentCategoryResponse.model_validate(entity)

    def delete_category(self, tenant_id: UUID, category_id: UUID, *, actor_id: UUID, meta: Optional[dict] = None) -> None:
        entity = self.category_repo.get_by_id(category_id, tenant_id)
        if not entity:
            raise NotFoundError("Category not found")
        self.category_repo.soft_delete(entity, updated_by=actor_id)
        self._log("documents.category.delete", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()

    # --- Employee documents ---

    def upload_employee_document(
        self,
        tenant_id: UUID,
        payload: EmployeeDocumentCreate,
        *,
        file_name: str,
        content: bytes,
        mime_type: Optional[str],
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> EmployeeDocumentResponse:
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        rel_path = employee_library_relative_path(
            str(tenant_id), str(payload.employee_id), payload.title, file_name
        )
        save_upload_file(rel_path, content)
        data = _coerce_payload(payload.model_dump())
        entity = LibraryEmployeeDocument(
            tenant_id=str(tenant_id),
            file_path=rel_path,
            file_name=file_name,
            mime_type=mime_type,
            file_size=len(content),
            uploaded_by=str(actor_id),
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.employee_doc_repo.add(entity)
        self._log("documents.employee.upload", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return EmployeeDocumentResponse.model_validate(entity)

    def list_employee_documents(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        employee_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[EmployeeDocumentResponse]:
        items, total = self.employee_doc_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, search=search, employee_id=employee_id, category_id=category_id, status=status
        )
        return PaginatedResponse(
            data=[EmployeeDocumentResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    # --- Company documents ---

    def upload_company_document(
        self,
        tenant_id: UUID,
        payload: CompanyDocumentCreate,
        *,
        file_name: str,
        content: bytes,
        mime_type: Optional[str],
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> CompanyDocumentResponse:
        rel_path = company_document_relative_path(str(tenant_id), payload.title, file_name)
        save_upload_file(rel_path, content)
        data = _coerce_payload(payload.model_dump())
        entity = CompanyDocument(
            tenant_id=str(tenant_id),
            file_path=rel_path,
            file_name=file_name,
            mime_type=mime_type,
            file_size=len(content),
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.company_doc_repo.add(entity)
        self._log("documents.company.upload", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return CompanyDocumentResponse.model_validate(entity)

    def list_company_documents(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        category_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[CompanyDocumentResponse]:
        items, total = self.company_doc_repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            search=search,
            category_id=category_id,
            branch_id=branch_id,
            department_id=department_id,
            is_active=is_active,
        )
        return PaginatedResponse(
            data=[CompanyDocumentResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    # --- Letter templates ---

    def create_letter_template(
        self, tenant_id: UUID, payload: LetterTemplateCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> LetterTemplateResponse:
        code = payload.code.upper()
        if self.template_repo.get_by_code(tenant_id, code):
            raise ConflictError(f"Template '{code}' already exists")
        data = _coerce_payload(payload.model_dump())
        entity = LetterTemplate(
            tenant_id=str(tenant_id),
            code=code,
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **{k: v for k, v in data.items() if k != "code"},
        )
        self.template_repo.add(entity)
        self._log("documents.template.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return LetterTemplateResponse.model_validate(entity)

    def list_letter_templates(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        letter_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[LetterTemplateResponse]:
        items, total = self.template_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, search=search, letter_type=letter_type, is_active=is_active
        )
        return PaginatedResponse(
            data=[LetterTemplateResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_letter_template(
        self, tenant_id: UUID, template_id: UUID, payload: LetterTemplateUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> LetterTemplateResponse:
        entity = self.template_repo.get_by_id(template_id, tenant_id)
        if not entity:
            raise NotFoundError("Letter template not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("documents.template.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return LetterTemplateResponse.model_validate(entity)

    # --- Generated letters ---

    def create_generated_letter(
        self, tenant_id: UUID, payload: GeneratedLetterCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> GeneratedLetterResponse:
        if payload.employee_id and not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        if payload.template_id and not self.template_repo.get_by_id(payload.template_id, tenant_id):
            raise NotFoundError("Letter template not found")
        data = _coerce_payload(payload.model_dump())
        entity = GeneratedLetter(
            tenant_id=str(tenant_id),
            generated_by=str(actor_id),
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.generated_repo.add(entity)
        self._log("documents.letter.generate", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return GeneratedLetterResponse.model_validate(entity)

    def sign_generated_letter(
        self,
        tenant_id: UUID,
        letter_id: UUID,
        *,
        signed_by: str,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> GeneratedLetterResponse:
        entity = self.generated_repo.get_by_id(letter_id, tenant_id)
        if not entity:
            raise NotFoundError("Generated letter not found")
        entity.status = "signed"
        entity.signed_at = datetime.now(timezone.utc)
        entity.signed_by = signed_by
        entity.updated_by = str(actor_id)
        self._log("documents.letter.sign", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return GeneratedLetterResponse.model_validate(entity)

    def list_generated_letters(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        employee_id: Optional[UUID] = None,
        template_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[GeneratedLetterResponse]:
        items, total = self.generated_repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            search=search,
            employee_id=employee_id,
            template_id=template_id,
            status=status,
        )
        return PaginatedResponse(
            data=[GeneratedLetterResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def generate_from_template(
        self,
        tenant_id: UUID,
        template_id: UUID,
        *,
        employee_id: Optional[UUID],
        placeholders: Optional[dict],
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> GeneratedLetterResponse:
        template = self.template_repo.get_by_id(template_id, tenant_id)
        if not template:
            raise NotFoundError("Letter template not found")
        content = template.body_template
        subject = template.subject
        if placeholders:
            for key, value in placeholders.items():
                content = content.replace(f"{{{{{key}}}}}", str(value))
                subject = subject.replace(f"{{{{{key}}}}}", str(value))
        payload = GeneratedLetterCreate(
            template_id=template_id,
            employee_id=employee_id,
            title=template.name,
            subject=subject,
            content=content,
            status="draft",
            metadata_json=json.dumps(placeholders) if placeholders else None,
        )
        return self.create_generated_letter(tenant_id, payload, actor_id=actor_id, meta=meta)
