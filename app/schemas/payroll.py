from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SalaryComponentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    component_type: str = Field(..., pattern="^(earning|deduction)$")
    calculation_type: str = Field(default="fixed", max_length=30)
    is_taxable: bool = True
    is_statutory: bool = False
    pf_applicable: bool = False
    esi_applicable: bool = False
    pt_applicable: bool = False
    is_active: bool = True


class SalaryComponentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    component_type: Optional[str] = Field(default=None, pattern="^(earning|deduction)$")
    calculation_type: Optional[str] = Field(default=None, max_length=30)
    is_taxable: Optional[bool] = None
    is_statutory: Optional[bool] = None
    pf_applicable: Optional[bool] = None
    esi_applicable: Optional[bool] = None
    pt_applicable: Optional[bool] = None
    is_active: Optional[bool] = None


class SalaryComponentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    component_type: str
    calculation_type: str
    is_taxable: bool
    is_statutory: bool
    pf_applicable: bool
    esi_applicable: bool
    pt_applicable: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StructureComponentItem(BaseModel):
    component_id: UUID
    monthly_amount: Decimal = Field(default=Decimal("0"), ge=0)
    percentage: Optional[Decimal] = Field(default=None, ge=0, le=100)
    calculation_base: Optional[str] = None


class SalaryStructureCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    annual_ctc: Optional[Decimal] = Field(default=None, ge=0)
    components: List[StructureComponentItem] = Field(default_factory=list)
    is_active: bool = True


class SalaryStructureUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    annual_ctc: Optional[Decimal] = Field(default=None, ge=0)
    components: Optional[List[StructureComponentItem]] = None
    is_active: Optional[bool] = None


class SalaryStructureResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    annual_ctc: Optional[Decimal] = None
    components: List[StructureComponentItem]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AssignStructureRequest(BaseModel):
    employee_id: UUID
    structure_id: UUID
    effective_from: date
    effective_to: Optional[date] = None
    annual_ctc: Decimal = Field(..., ge=0)
    arrears_amount: Decimal = Field(default=Decimal("0"), ge=0)


class EmployeeSalaryStructureResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    structure_id: UUID
    effective_from: date
    effective_to: Optional[date] = None
    annual_ctc: Decimal
    arrears_amount: Decimal
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PayrollRunRequest(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)
    working_days: int = Field(default=26, ge=1, le=31)
    employee_ids: Optional[List[UUID]] = None
    reimbursement_overrides: Optional[dict[str, Decimal]] = None


class PayrollRunResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    month: int
    year: int
    status: str
    working_days: int
    total_gross: Decimal
    total_deductions: Decimal
    total_net: Decimal
    employee_count: int
    run_date: Optional[date] = None
    approved_at: Optional[datetime] = None
    locked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PayrollLineItem(BaseModel):
    code: str
    name: str
    amount: Decimal
    item_type: str


class PayrollEmployeePreview(BaseModel):
    employee_id: UUID
    employee_code: str
    employee_name: str
    payable_days: Decimal
    lop_days: Decimal
    overtime_minutes: int
    gross_earnings: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    earnings: List[PayrollLineItem]
    deductions: List[PayrollLineItem]


class PayrollPreviewResponse(BaseModel):
    run: PayrollRunResponse
    employees: List[PayrollEmployeePreview]
    bank_transfer: List[dict[str, Any]]


class PayslipResponse(BaseModel):
    id: UUID
    employee_id: UUID
    month: int
    year: int
    gross_earnings: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    line_items: dict[str, Any]
    generated_at: datetime

    model_config = {"from_attributes": True}


class PayrollReportResponse(BaseModel):
    runs: List[PayrollRunResponse]
    summary: dict[str, Any]


class FnFCreateRequest(BaseModel):
    employee_id: UUID
    last_working_date: date
    pending_salary: Decimal = Field(default=Decimal("0"), ge=0)
    leave_encashment: Decimal = Field(default=Decimal("0"), ge=0)
    gratuity: Decimal = Field(default=Decimal("0"), ge=0)
    other_earnings: Decimal = Field(default=Decimal("0"), ge=0)
    loan_recovery: Decimal = Field(default=Decimal("0"), ge=0)
    notice_recovery: Decimal = Field(default=Decimal("0"), ge=0)
    other_deductions: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = None


class FnFResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    last_working_date: date
    gross_amount: Decimal
    total_deductions: Decimal
    net_payable: Decimal
    settlement: dict[str, Any]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaxDeclarationCreate(BaseModel):
    employee_id: UUID
    financial_year: str = Field(..., min_length=4, max_length=10)
    regime: str = Field(default="new", pattern="^(old|new)$")
    section: str = Field(..., min_length=1, max_length=50)
    declared_amount: Decimal = Field(default=Decimal("0"), ge=0)


class TaxDeclarationUpdate(BaseModel):
    regime: Optional[str] = Field(default=None, pattern="^(old|new)$")
    section: Optional[str] = Field(default=None, min_length=1, max_length=50)
    declared_amount: Optional[Decimal] = Field(default=None, ge=0)
    approved_amount: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, max_length=30)


class TaxDeclarationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    employee_id: UUID
    financial_year: str
    regime: str
    section: str
    declared_amount: Decimal
    approved_amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StatutorySettingUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    pf_employee_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    pf_employer_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    pf_wage_ceiling: Optional[Decimal] = Field(default=None, ge=0)
    esi_employee_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    esi_employer_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    esi_gross_threshold: Optional[Decimal] = Field(default=None, ge=0)
    pt_slabs: Optional[List[dict[str, Any]]] = None
    tds_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    overtime_multiplier: Optional[Decimal] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class StatutorySettingResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    code: str
    pf_employee_rate: Decimal
    pf_employer_rate: Decimal
    pf_wage_ceiling: Decimal
    esi_employee_rate: Decimal
    esi_employer_rate: Decimal
    esi_gross_threshold: Decimal
    pt_slabs: List[dict[str, Any]]
    tds_rate: Decimal
    overtime_multiplier: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PayrollBatchResponse(BaseModel):
    id: str
    name: str
    month: int
    year: int
    employee_count: int
    created_at: datetime
    status: str
    gross_wages: Decimal
    deductions: Decimal
    payout: Decimal
    salary_slip_status: str
    locked: bool
    locked_at: Optional[datetime] = None
    unlock_scheduled_at: Optional[datetime] = None


class PayrollRegisterOption(BaseModel):
    id: str
    name: str
    type: str
    month: int
    year: int


class PayrollBatchLogEntry(BaseModel):
    id: str
    message: str
    created_at: datetime


class PayrollBatchDetailResponse(PayrollBatchResponse):
    registers: List[PayrollRegisterOption] = Field(default_factory=list)
    selected_salary_slip_id: Optional[str] = None
    logs: List[PayrollBatchLogEntry] = Field(default_factory=list)


class PayrollMonthSummary(BaseModel):
    gross_wages: Decimal
    deductions: Decimal
    net_wages: Decimal
    leave_encashment: Decimal = Decimal("0")
    gratuity: Decimal = Decimal("0")
    payout: Decimal
    payout_change_percent: Optional[float] = None


class PayrollMonthComparison(BaseModel):
    previous_label: str
    current_label: str
    employee_count: dict[str, int]
    new_starters: dict[str, int]
    leavers: dict[str, int]


class PayrollOverviewResponse(BaseModel):
    financial_year: str
    month: int
    year: int
    month_label: str
    date_range: str
    locked: bool
    total_employee_count: int
    processed_count: int
    pending_count: int
    summary: PayrollMonthSummary
    comparison: PayrollMonthComparison
    batches: List[PayrollBatchResponse]


class CreatePayrollBatchRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)
    batch_type: Optional[str] = Field(default="custom", pattern="^(staff|labour|custom)$")
