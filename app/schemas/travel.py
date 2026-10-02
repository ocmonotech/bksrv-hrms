from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TravelPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    max_budget: Optional[Decimal] = Field(default=None, ge=0)
    requires_approval: bool = True
    is_active: bool = True


class TravelPolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    max_budget: Optional[Decimal] = Field(default=None, ge=0)
    requires_approval: Optional[bool] = None
    is_active: Optional[bool] = None


class TravelPolicyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    max_budget: Optional[Decimal] = None
    requires_approval: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TravelRequestCreate(BaseModel):
    employee_id: UUID
    destination: str = Field(..., min_length=1, max_length=255)
    purpose: str = Field(..., min_length=3)
    start_date: date
    end_date: date
    estimated_cost: Decimal = Field(default=Decimal("0"), ge=0)


class TravelRequestUpdate(BaseModel):
    destination: Optional[str] = Field(default=None, max_length=255)
    purpose: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    estimated_cost: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, max_length=30)


class TravelRequestResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    destination: str
    purpose: str
    start_date: date
    end_date: date
    estimated_cost: Decimal
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
