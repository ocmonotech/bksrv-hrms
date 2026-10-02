from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Expenses ---


class ExpensePolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    max_amount: Optional[Decimal] = Field(default=None, ge=0)
    requires_receipt: bool = True
    is_active: bool = True


class ExpensePolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    max_amount: Optional[Decimal] = Field(default=None, ge=0)
    requires_receipt: Optional[bool] = None
    is_active: Optional[bool] = None


class ExpensePolicyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    max_amount: Optional[Decimal] = None
    requires_receipt: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseClaimCreate(BaseModel):
    employee_id: UUID
    policy_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., ge=0)
    expense_date: date
    description: Optional[str] = None


class ExpenseClaimUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    amount: Optional[Decimal] = Field(default=None, ge=0)
    expense_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=30)


class ExpenseClaimResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    policy_id: Optional[UUID] = None
    title: str
    amount: Decimal
    expense_date: date
    description: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseAdvanceCreate(BaseModel):
    employee_id: UUID
    amount: Decimal = Field(..., ge=0)
    purpose: str = Field(..., min_length=3, max_length=500)
    requested_date: date


class ExpenseAdvanceUpdate(BaseModel):
    amount: Optional[Decimal] = Field(default=None, ge=0)
    purpose: Optional[str] = Field(default=None, max_length=500)
    requested_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=30)


class ExpenseAdvanceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    amount: Decimal
    purpose: str
    requested_date: date
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
