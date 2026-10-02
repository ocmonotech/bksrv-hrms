from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    priority: str = Field(default="normal", max_length=20)
    status: str = Field(default="draft", max_length=30)
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    body: Optional[str] = None
    priority: Optional[str] = Field(default=None, max_length=20)
    status: Optional[str] = Field(default=None, max_length=30)
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AnnouncementResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    title: str
    body: str
    priority: str
    status: str
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommunicationTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    channel: str = Field(default="email", max_length=30)
    subject: str = Field(..., min_length=1, max_length=500)
    body_template: str = Field(..., min_length=1)
    is_active: bool = True


class CommunicationTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    channel: Optional[str] = Field(default=None, max_length=30)
    subject: Optional[str] = Field(default=None, max_length=500)
    body_template: Optional[str] = None
    is_active: Optional[bool] = None


class CommunicationTemplateResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    channel: str
    subject: str
    body_template: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CommunicationLogCreate(BaseModel):
    template_id: Optional[UUID] = None
    recipient_email: str = Field(..., min_length=3, max_length=255)
    channel: str = Field(default="email", max_length=30)
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)


class CommunicationLogUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=30)
    sent_at: Optional[datetime] = None


class CommunicationLogResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    template_id: Optional[UUID] = None
    recipient_email: str
    channel: str
    subject: str
    body: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
