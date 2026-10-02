from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    parent_id: Optional[UUID] = None
    is_active: bool = True


class DocumentCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    parent_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class DocumentCategoryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeDocumentCreate(BaseModel):
    employee_id: UUID
    category_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = "active"
    expiry_date: Optional[date] = None
    is_confidential: bool = False


class EmployeeDocumentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    category_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    file_path: str
    file_name: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    status: str
    expiry_date: Optional[date] = None
    is_confidential: bool
    uploaded_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyDocumentCreate(BaseModel):
    category_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    branch_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    visibility: str = "all"
    version: Optional[str] = None
    is_active: bool = True


class CompanyDocumentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    category_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    file_path: str
    file_name: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    branch_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    visibility: str
    version: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LetterTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    letter_type: str = Field(..., min_length=1, max_length=100)
    subject: str = Field(..., min_length=1, max_length=500)
    body_template: str = Field(..., min_length=10)
    placeholders: Optional[str] = None
    is_active: bool = True


class LetterTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    letter_type: Optional[str] = Field(default=None, max_length=100)
    subject: Optional[str] = Field(default=None, max_length=500)
    body_template: Optional[str] = None
    placeholders: Optional[str] = None
    is_active: Optional[bool] = None


class LetterTemplateResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    letter_type: str
    subject: str
    body_template: str
    placeholders: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GeneratedLetterCreate(BaseModel):
    template_id: Optional[UUID] = None
    employee_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    subject: Optional[str] = Field(default=None, max_length=500)
    content: str = Field(..., min_length=10)
    status: str = "draft"
    metadata_json: Optional[str] = None


class GeneratedLetterResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    template_id: Optional[UUID] = None
    employee_id: Optional[UUID] = None
    title: str
    subject: Optional[str] = None
    content: str
    status: str
    generated_by: Optional[str] = None
    sent_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    signed_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GeneratedLetterSignRequest(BaseModel):
    signed_by: str = Field(..., min_length=2, max_length=255)
