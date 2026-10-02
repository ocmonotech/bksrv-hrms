from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.documents import (
    CompanyDocument,
    DocumentCategory,
    GeneratedLetter,
    LetterTemplate,
    LibraryEmployeeDocument,
)
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class DocumentCategoryRepository(TenantScopedRepository[DocumentCategory]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, DocumentCategory)


class EmployeeDocumentRepository(TenantScopedRepository[LibraryEmployeeDocument]):
    search_fields = ("title", "file_name")

    def __init__(self, db: Session) -> None:
        super().__init__(db, LibraryEmployeeDocument, search_fields=self.search_fields)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        employee_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if employee_id:
            extra.append(LibraryEmployeeDocument.employee_id == str(employee_id))
        if category_id:
            extra.append(LibraryEmployeeDocument.category_id == str(category_id))
        if status:
            extra.append(LibraryEmployeeDocument.status == status)
        return self.list_paginated(
            tenant_id, page=page, page_size=page_size, search=search, extra_filters=extra or None
        )


class CompanyDocumentRepository(TenantScopedRepository[CompanyDocument]):
    search_fields = ("title", "file_name")

    def __init__(self, db: Session) -> None:
        super().__init__(db, CompanyDocument, search_fields=self.search_fields)

    def list_filtered(
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
    ):
        extra = []
        if category_id:
            extra.append(CompanyDocument.category_id == str(category_id))
        if branch_id:
            extra.append(CompanyDocument.branch_id == str(branch_id))
        if department_id:
            extra.append(CompanyDocument.department_id == str(department_id))
        return self.list_paginated(
            tenant_id,
            page=page,
            page_size=page_size,
            search=search,
            is_active=is_active,
            extra_filters=extra or None,
        )


class LetterTemplateRepository(TenantScopedRepository[LetterTemplate]):
    search_fields = ("name", "code", "letter_type")

    def __init__(self, db: Session) -> None:
        super().__init__(db, LetterTemplate, search_fields=self.search_fields)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        letter_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        extra = [LetterTemplate.letter_type == letter_type] if letter_type else None
        return self.list_paginated(
            tenant_id, page=page, page_size=page_size, search=search, is_active=is_active, extra_filters=extra
        )


class GeneratedLetterRepository(TenantScopedRepository[GeneratedLetter]):
    search_fields = ("title", "subject")

    def __init__(self, db: Session) -> None:
        super().__init__(db, GeneratedLetter, search_fields=self.search_fields)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        employee_id: Optional[UUID] = None,
        template_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if employee_id:
            extra.append(GeneratedLetter.employee_id == str(employee_id))
        if template_id:
            extra.append(GeneratedLetter.template_id == str(template_id))
        if status:
            extra.append(GeneratedLetter.status == status)
        return self.list_paginated(
            tenant_id, page=page, page_size=page_size, search=search, extra_filters=extra or None
        )
