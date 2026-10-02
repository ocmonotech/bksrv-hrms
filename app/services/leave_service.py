from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.leave import CompOffRequest, LeaveBalance, LeaveRequest, LeaveTransaction
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.leave_repository import (
    CompOffRequestRepository,
    HolidayRepository,
    LeaveBalanceRepository,
    LeavePolicyRepository,
    LeaveRequestRepository,
    LeaveTypeRepository,
)
from app.schemas.leave import (
    CompOffCreate,
    CompOffResponse,
    GenerateBalanceRequest,
    LeaveApplyRequest,
    LeaveBalanceResponse,
    LeaveCalendarEntry,
    LeaveRequestResponse,
)
from app.services.audit_service import AuditService
from app.utils.leave_calc import calculate_leave_days
from app.utils.pagination import total_pages
from app.schemas.common import PaginatedResponse


class LeaveService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.type_repo = LeaveTypeRepository(db)
        self.policy_repo = LeavePolicyRepository(db)
        self.balance_repo = LeaveBalanceRepository(db)
        self.request_repo = LeaveRequestRepository(db)
        self.comp_off_repo = CompOffRequestRepository(db)
        self.holiday_repo = HolidayRepository(db)
        self.employee_repo = EmployeeRepository(db)
        self.audit = AuditService(db)

    def apply_leave(
        self,
        tenant_id: UUID,
        payload: LeaveApplyRequest,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> LeaveRequestResponse:
        employee = self.employee_repo.get_by_id(payload.employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")

        leave_type = self.type_repo.get_by_id(payload.leave_type_id, tenant_id)
        if not leave_type or not leave_type.is_active:
            raise NotFoundError("Leave type not found")

        if payload.is_half_day and not leave_type.allow_half_day:
            raise ValidationError("Half-day leave is not allowed for this leave type")

        if self.request_repo.overlapping(
            tenant_id, payload.employee_id, payload.start_date, payload.end_date
        ):
            raise ConflictError("Overlapping leave request exists")

        policy = self.policy_repo.get_active_for_type(tenant_id, payload.leave_type_id)
        holidays = self.holiday_repo.dates_in_range(tenant_id, payload.start_date, payload.end_date)
        total_days, sandwich_days, _ = calculate_leave_days(
            payload.start_date,
            payload.end_date,
            is_half_day=payload.is_half_day,
            sandwich_enabled=bool(policy and policy.sandwich_rule_enabled),
            holiday_dates=holidays,
        )

        if policy and policy.min_days_notice:
            notice = (payload.start_date - date.today()).days
            if notice < policy.min_days_notice:
                raise ValidationError(
                    f"Minimum {policy.min_days_notice} day(s) notice required for this leave type"
                )

        year = payload.start_date.year
        balance = self.balance_repo.get_balance(tenant_id, payload.employee_id, payload.leave_type_id, year)
        lop_days = Decimal("0")
        if leave_type.is_paid and balance:
            available = balance.closing_balance
            if total_days > available:
                if not policy or not policy.allow_lop:
                    raise ValidationError("Insufficient leave balance")
                lop_days = total_days - available
        elif leave_type.is_paid and not balance:
            lop_days = total_days

        req = LeaveRequest(
            tenant_id=str(tenant_id),
            employee_id=str(payload.employee_id),
            leave_type_id=str(payload.leave_type_id),
            start_date=payload.start_date,
            end_date=payload.end_date,
            total_days=total_days,
            is_half_day=payload.is_half_day,
            half_day_period=payload.half_day_period,
            reason=payload.reason,
            status="pending" if leave_type.requires_approval else "approved",
            sandwich_days=sandwich_days,
            lop_days=lop_days,
            manager_id=str(employee.reporting_manager_id) if employee.reporting_manager_id else None,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.request_repo.add(req)

        if req.status == "approved":
            self._debit_balance(tenant_id, req, actor_id)

        self.audit.log(
            "leave.apply",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="leave_request",
            resource_id=str(req.id),
            details={"total_days": str(total_days), "lop_days": str(lop_days)},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(req)
        return LeaveRequestResponse.model_validate(req)

    def list_requests(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> PaginatedResponse[LeaveRequestResponse]:
        items, total = self.request_repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            employee_id=employee_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )
        return PaginatedResponse(
            data=[LeaveRequestResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def approve_leave(
        self,
        tenant_id: UUID,
        request_id: UUID,
        *,
        actor_id: UUID,
        hr_override: bool = False,
        notes: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> LeaveRequestResponse:
        req = self.request_repo.get_by_id(request_id, tenant_id)
        if not req:
            raise NotFoundError("Leave request not found")
        if req.status != "pending":
            raise ValidationError("Leave request is not pending")

        req.status = "approved"
        req.approver_id = str(actor_id)
        req.approved_at = datetime.now(timezone.utc)
        req.hr_override = hr_override
        req.updated_by = str(actor_id)
        self._debit_balance(tenant_id, req, actor_id, notes=notes)

        self.audit.log(
            "leave.approve",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="leave_request",
            resource_id=str(req.id),
            details={"hr_override": hr_override},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(req)
        return LeaveRequestResponse.model_validate(req)

    def reject_leave(
        self,
        tenant_id: UUID,
        request_id: UUID,
        *,
        actor_id: UUID,
        rejection_reason: str,
        hr_override: bool = False,
        meta: Optional[dict] = None,
    ) -> LeaveRequestResponse:
        req = self.request_repo.get_by_id(request_id, tenant_id)
        if not req:
            raise NotFoundError("Leave request not found")
        if req.status != "pending":
            raise ValidationError("Leave request is not pending")

        req.status = "rejected"
        req.rejection_reason = rejection_reason
        req.approver_id = str(actor_id)
        req.approved_at = datetime.now(timezone.utc)
        req.hr_override = hr_override
        req.updated_by = str(actor_id)

        self.audit.log(
            "leave.reject",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="leave_request",
            resource_id=str(req.id),
            details={"reason": rejection_reason},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(req)
        return LeaveRequestResponse.model_validate(req)

    def cancel_leave(
        self,
        tenant_id: UUID,
        request_id: UUID,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> LeaveRequestResponse:
        req = self.request_repo.get_by_id(request_id, tenant_id)
        if not req:
            raise NotFoundError("Leave request not found")
        if req.status not in ("pending", "approved"):
            raise ValidationError("Leave request cannot be cancelled")

        was_approved = req.status == "approved"
        req.status = "cancelled"
        req.updated_by = str(actor_id)

        if was_approved:
            self._credit_balance(tenant_id, req, actor_id, notes="Leave cancelled")

        self.audit.log(
            "leave.cancel",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="leave_request",
            resource_id=str(req.id),
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(req)
        return LeaveRequestResponse.model_validate(req)

    def get_balance(self, tenant_id: UUID, employee_id: UUID, year: Optional[int] = None) -> list[LeaveBalanceResponse]:
        target_year = year or date.today().year
        if not self.employee_repo.get_by_id(employee_id, tenant_id):
            raise NotFoundError("Employee not found")

        balances = self.balance_repo.list_for_employee(tenant_id, employee_id, target_year)
        result = []
        for bal in balances:
            leave_type = self.type_repo.get_by_id(UUID(bal.leave_type_id), tenant_id)
            if not leave_type:
                continue
            result.append(
                LeaveBalanceResponse(
                    employee_id=employee_id,
                    leave_type_id=UUID(bal.leave_type_id),
                    leave_type_code=leave_type.code,
                    leave_type_name=leave_type.name,
                    year=bal.year,
                    opening_balance=bal.opening_balance,
                    accrued=bal.accrued,
                    used=bal.used,
                    adjusted=bal.adjusted,
                    closing_balance=bal.closing_balance,
                )
            )
        return result

    def calendar(
        self,
        tenant_id: UUID,
        *,
        start_date: date,
        end_date: date,
        employee_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
    ) -> list[LeaveCalendarEntry]:
        rows = self.request_repo.calendar_entries(
            tenant_id,
            start_date=start_date,
            end_date=end_date,
            employee_id=employee_id,
            branch_id=branch_id,
            department_id=department_id,
        )
        entries: list[LeaveCalendarEntry] = []
        for req, leave_type in rows:
            current = req.start_date
            while current <= req.end_date:
                if start_date <= current <= end_date:
                    entries.append(
                        LeaveCalendarEntry(
                            date=current,
                            employee_id=UUID(req.employee_id),
                            leave_request_id=UUID(req.id),
                            leave_type_code=leave_type.code,
                            leave_type_name=leave_type.name,
                            status=req.status,
                            is_half_day=req.is_half_day,
                        )
                    )
                current = date.fromordinal(current.toordinal() + 1)
        return entries

    def generate_balances(
        self,
        tenant_id: UUID,
        payload: GenerateBalanceRequest,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> int:
        leave_types = self.type_repo.list_paginated(tenant_id, page=1, page_size=500, is_active=True)[0]
        if payload.employee_ids:
            employee_ids = payload.employee_ids
        else:
            employees, _ = self.employee_repo.list_paginated(tenant_id, page=1, page_size=5000, is_active=True)
            employee_ids = [UUID(e.id) for e in employees]

        created = 0
        for emp_id in employee_ids:
            if not self.employee_repo.get_by_id(emp_id, tenant_id):
                continue
            for lt in leave_types:
                existing = self.balance_repo.get_balance(tenant_id, emp_id, UUID(lt.id), payload.year)
                if existing:
                    continue
                policy = self.policy_repo.get_active_for_type(tenant_id, UUID(lt.id))
                opening = lt.max_days_per_year or Decimal("0")
                accrued = policy.accrual_days * Decimal("12") if policy else Decimal("0")
                bal = LeaveBalance(
                    tenant_id=str(tenant_id),
                    employee_id=str(emp_id),
                    leave_type_id=str(lt.id),
                    year=payload.year,
                    opening_balance=opening,
                    accrued=accrued,
                    used=Decimal("0"),
                    adjusted=Decimal("0"),
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                )
                self.balance_repo.add(bal)
                created += 1

        self.audit.log(
            "leave.balance.generate",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="leave_balance",
            details={"year": payload.year, "created": created},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        return created

    def create_comp_off(
        self,
        tenant_id: UUID,
        payload: CompOffCreate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> CompOffResponse:
        if not self.employee_repo.get_by_id(payload.employee_id, tenant_id):
            raise NotFoundError("Employee not found")

        comp = CompOffRequest(
            tenant_id=str(tenant_id),
            employee_id=str(payload.employee_id),
            worked_date=payload.worked_date,
            comp_off_date=payload.comp_off_date,
            reason=payload.reason,
            status="pending",
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.comp_off_repo.add(comp)
        self.audit.log(
            "leave.comp_off.create",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="comp_off_request",
            resource_id=str(comp.id),
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(comp)
        return CompOffResponse.model_validate(comp)

    def list_comp_off(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[CompOffResponse]:
        items, total = self.comp_off_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, employee_id=employee_id, status=status
        )
        return PaginatedResponse(
            data=[CompOffResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def _debit_balance(
        self,
        tenant_id: UUID,
        req: LeaveRequest,
        actor_id: UUID,
        *,
        notes: Optional[str] = None,
    ) -> None:
        year = req.start_date.year
        balance = self.balance_repo.get_balance(
            tenant_id, UUID(req.employee_id), UUID(req.leave_type_id), year
        )
        debit_days = req.total_days - req.lop_days
        if balance and debit_days > 0:
            balance.used += debit_days
            balance.updated_by = str(actor_id)
            balance_after = balance.closing_balance
        else:
            balance_after = Decimal("0")

        if req.lop_days > 0:
            txn = LeaveTransaction(
                tenant_id=str(tenant_id),
                employee_id=req.employee_id,
                leave_type_id=req.leave_type_id,
                leave_request_id=str(req.id),
                transaction_type="lop",
                days=req.lop_days,
                balance_after=balance_after,
                notes=notes or "LOP for insufficient balance",
                actor_id=str(actor_id),
            )
            self.db.add(txn)

        if debit_days > 0:
            txn = LeaveTransaction(
                tenant_id=str(tenant_id),
                employee_id=req.employee_id,
                leave_type_id=req.leave_type_id,
                leave_request_id=str(req.id),
                transaction_type="debit",
                days=debit_days,
                balance_after=balance_after,
                notes=notes,
                actor_id=str(actor_id),
            )
            self.db.add(txn)

    def _credit_balance(
        self,
        tenant_id: UUID,
        req: LeaveRequest,
        actor_id: UUID,
        *,
        notes: Optional[str] = None,
    ) -> None:
        year = req.start_date.year
        balance = self.balance_repo.get_balance(
            tenant_id, UUID(req.employee_id), UUID(req.leave_type_id), year
        )
        credit_days = req.total_days - req.lop_days
        if balance and credit_days > 0:
            balance.used = max(balance.used - credit_days, Decimal("0"))
            balance.updated_by = str(actor_id)
            txn = LeaveTransaction(
                tenant_id=str(tenant_id),
                employee_id=req.employee_id,
                leave_type_id=req.leave_type_id,
                leave_request_id=str(req.id),
                transaction_type="credit",
                days=credit_days,
                balance_after=balance.closing_balance,
                notes=notes,
                actor_id=str(actor_id),
            )
            self.db.add(txn)
