from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.attendance import (
    AttendanceDailySummary,
    AttendanceLog,
    AttendancePolicy,
    AttendanceRegularization,
    BiometricDevice,
    FieldVisit,
)
from app.repositories.attendance_repository import (
    AttendanceDailySummaryRepository,
    AttendanceLogRepository,
    AttendancePolicyRepository,
    AttendanceRegularizationRepository,
    BiometricDeviceRepository,
    EmployeeShiftAssignmentRepository,
    FieldVisitRepository,
    RosterRepository,
    ShiftRepository,
)
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.attendance import (
    AttendanceDashboardStats,
    AttendancePolicyResponse,
    AttendancePolicyUpdate,
    BiometricDeviceCreate,
    BiometricDeviceResponse,
    BiometricSyncResponse,
    DailySummaryResponse,
    FieldVisitCreate,
    FieldVisitResponse,
    MonthlyAttendanceSummary,
    PunchRequest,
    PunchResponse,
    RegularizationCreate,
    RegularizationResponse,
)
from app.services.audit_service import AuditService
from app.utils.attendance_calc import (
    calculate_early_leave_minutes,
    calculate_late_minutes,
    calculate_work_minutes,
    determine_day_status,
    payable_days_from_status,
)


class AttendanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.log_repo = AttendanceLogRepository(db)
        self.summary_repo = AttendanceDailySummaryRepository(db)
        self.reg_repo = AttendanceRegularizationRepository(db)
        self.policy_repo = AttendancePolicyRepository(db)
        self.biometric_repo = BiometricDeviceRepository(db)
        self.field_visit_repo = FieldVisitRepository(db)
        self.shift_repo = ShiftRepository(db)
        self.roster_repo = RosterRepository(db)
        self.assignment_repo = EmployeeShiftAssignmentRepository(db)
        self.employee_repo = EmployeeRepository(db)
        self.audit = AuditService(db)

    def _get_employee(self, tenant_id: UUID, employee_id: UUID) -> Employee:
        employee = self.employee_repo.get_by_id(employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")
        return employee

    def _resolve_shift(self, tenant_id: UUID, employee_id: UUID, on_date: date):
        roster = self.roster_repo.get_for_day(tenant_id, employee_id, on_date)
        if roster:
            return self.shift_repo.get_by_id(roster.shift_id, tenant_id)
        assignment = self.assignment_repo.get_active_for_date(tenant_id, employee_id, on_date)
        if assignment:
            return self.shift_repo.get_by_id(assignment.shift_id, tenant_id)
        return None

    def punch(
        self,
        tenant_id: UUID,
        payload: PunchRequest,
        *,
        actor_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> PunchResponse:
        self._get_employee(tenant_id, payload.employee_id)
        punch_time = payload.punch_time or datetime.now(timezone.utc)
        attendance_date = punch_time.date()

        if payload.source == "mobile":
            if payload.latitude is None or payload.longitude is None:
                raise ValidationError("GPS coordinates are required for mobile punch")

        log = AttendanceLog(
            tenant_id=str(tenant_id),
            employee_id=str(payload.employee_id),
            punch_type=payload.punch_type.lower(),
            punch_time=punch_time,
            source=payload.source,
            latitude=payload.latitude,
            longitude=payload.longitude,
            gps_accuracy=payload.gps_accuracy,
            selfie_path=payload.selfie_path,
            device_id=str(payload.device_id) if payload.device_id else None,
            device_log_id=payload.device_log_id,
            ip_address=ip_address,
            user_agent=user_agent,
            remarks=payload.remarks,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.log_repo.add(log)
        summary = self._recalculate_daily_summary(tenant_id, payload.employee_id, attendance_date, actor_id)

        self.audit.log(
            "attendance.punch",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="attendance_log",
            resource_id=str(log.id),
            details={"punch_type": payload.punch_type, "employee_id": str(payload.employee_id)},
            ip_address=meta.get("ip_address") if meta else ip_address,
            user_agent=meta.get("user_agent") if meta else user_agent,
        )
        self.db.commit()
        self.db.refresh(log)
        self.db.refresh(summary)
        return PunchResponse(
            log_id=log.id,
            employee_id=payload.employee_id,
            punch_type=log.punch_type,
            punch_time=log.punch_time,
            daily_summary=DailySummaryResponse.model_validate(summary),
        )

    def _recalculate_daily_summary(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        attendance_date: date,
        actor_id: UUID,
        *,
        override_in: Optional[datetime] = None,
        override_out: Optional[datetime] = None,
    ) -> AttendanceDailySummary:
        logs = self.log_repo.list_for_day(tenant_id, employee_id, attendance_date)
        first_in = override_in
        last_out = override_out
        if not override_in or not override_out:
            for log in logs:
                if log.punch_type == "in" and (first_in is None or log.punch_time < first_in):
                    first_in = log.punch_time
                if log.punch_type == "out" and (last_out is None or log.punch_time > last_out):
                    last_out = log.punch_time

        shift = self._resolve_shift(tenant_id, employee_id, attendance_date)
        break_minutes = shift.break_minutes if shift else 0
        grace = shift.grace_minutes if shift else 10

        work_minutes = calculate_work_minutes(first_in, last_out, break_minutes)
        late_minutes = calculate_late_minutes(first_in, shift, attendance_date, grace)
        early_minutes = calculate_early_leave_minutes(last_out, shift, attendance_date)
        full_day = int((shift and 8 or 8) * 60)
        half_day = full_day // 2

        status, lop_days, is_lop = determine_day_status(
            work_minutes, late_minutes, full_day_minutes=full_day, half_day_minutes=half_day
        )
        payable = payable_days_from_status(status, lop_days)

        summary = self.summary_repo.get_for_day(tenant_id, employee_id, attendance_date)
        if not summary:
            summary = AttendanceDailySummary(
                tenant_id=str(tenant_id),
                employee_id=str(employee_id),
                attendance_date=attendance_date,
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.summary_repo.add(summary)

        summary.shift_id = str(shift.id) if shift else None
        summary.first_in = first_in
        summary.last_out = last_out
        summary.total_work_minutes = work_minutes
        summary.break_minutes = break_minutes
        summary.status = status
        summary.late_minutes = late_minutes
        summary.early_leave_minutes = early_minutes
        summary.is_lop = is_lop
        summary.lop_days = lop_days
        summary.payable_days = payable
        summary.updated_by = str(actor_id)
        self.db.flush()
        return summary

    def list_daily(
        self,
        tenant_id: UUID,
        *,
        attendance_date: Optional[date] = None,
        employee_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> list[DailySummaryResponse]:
        target = attendance_date or date.today()
        if employee_id:
            summary = self.summary_repo.get_for_day(tenant_id, employee_id, target)
            return [DailySummaryResponse.model_validate(summary)] if summary else []

        rows = self.summary_repo.list_for_month(
            tenant_id,
            year=target.year,
            month=target.month,
            branch_id=branch_id,
            department_id=department_id,
            status=status,
        )
        return [DailySummaryResponse.model_validate(r) for r in rows if r.attendance_date == target]

    def monthly_summary(
        self,
        tenant_id: UUID,
        *,
        year: int,
        month: int,
        employee_id: UUID,
    ) -> MonthlyAttendanceSummary:
        rows = self.summary_repo.list_for_month(
            tenant_id, year=year, month=month, employee_id=employee_id
        )
        present = Decimal("0")
        absent = Decimal("0")
        half = Decimal("0")
        late_days = 0
        lop = Decimal("0")
        payable = Decimal("0")
        total_minutes = 0
        for row in rows:
            total_minutes += row.total_work_minutes
            payable += row.payable_days
            lop += row.lop_days
            if row.status == "present":
                present += Decimal("1")
            elif row.status == "late":
                present += Decimal("1")
                late_days += 1
            elif row.status == "half_day":
                half += Decimal("1")
            elif row.status == "absent":
                absent += Decimal("1")
        return MonthlyAttendanceSummary(
            employee_id=employee_id,
            month=month,
            year=year,
            present_days=present,
            absent_days=absent,
            half_days=half,
            late_days=late_days,
            lop_days=lop,
            payable_days=payable,
            total_work_minutes=total_minutes,
        )

    def create_regularization(
        self,
        tenant_id: UUID,
        payload: RegularizationCreate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> RegularizationResponse:
        employee = self._get_employee(tenant_id, payload.employee_id)
        if not payload.requested_in and not payload.requested_out:
            raise ValidationError("At least one of requested_in or requested_out is required")

        reg = AttendanceRegularization(
            tenant_id=str(tenant_id),
            employee_id=str(payload.employee_id),
            attendance_date=payload.attendance_date,
            requested_in=payload.requested_in,
            requested_out=payload.requested_out,
            reason=payload.reason,
            status="pending",
            manager_id=str(employee.reporting_manager_id) if employee.reporting_manager_id else None,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.reg_repo.add(reg)

        summary = self.summary_repo.get_for_day(tenant_id, payload.employee_id, payload.attendance_date)
        if summary:
            summary.regularization_status = "pending"
        else:
            summary = AttendanceDailySummary(
                tenant_id=str(tenant_id),
                employee_id=str(payload.employee_id),
                attendance_date=payload.attendance_date,
                regularization_status="pending",
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.summary_repo.add(summary)

        self.audit.log(
            "attendance.regularization.create",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="attendance_regularization",
            resource_id=str(reg.id),
            details={"employee_id": str(payload.employee_id), "date": str(payload.attendance_date)},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(reg)
        return RegularizationResponse.model_validate(reg)

    def approve_regularization(
        self,
        tenant_id: UUID,
        reg_id: UUID,
        *,
        actor_id: UUID,
        hr_override: bool = False,
        rejection_reason: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> RegularizationResponse:
        reg = self.reg_repo.get_by_id(reg_id, tenant_id)
        if not reg:
            raise NotFoundError("Regularization request not found")
        if reg.status != "pending":
            raise ValidationError("Regularization request is not pending")

        if rejection_reason:
            reg.status = "rejected"
            reg.rejection_reason = rejection_reason
            reg.approver_id = str(actor_id)
            reg.approved_at = datetime.now(timezone.utc)
            summary = self.summary_repo.get_for_day(tenant_id, UUID(reg.employee_id), reg.attendance_date)
            if summary:
                summary.regularization_status = "rejected"
        else:
            reg.status = "approved"
            reg.approver_id = str(actor_id)
            reg.approved_at = datetime.now(timezone.utc)
            reg.hr_override = hr_override
            summary = self._recalculate_daily_summary(
                tenant_id,
                UUID(reg.employee_id),
                reg.attendance_date,
                actor_id,
                override_in=reg.requested_in,
                override_out=reg.requested_out,
            )
            summary.regularization_status = "approved"

        reg.updated_by = str(actor_id)
        self.audit.log(
            f"attendance.regularization.{reg.status}",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="attendance_regularization",
            resource_id=str(reg.id),
            details={"hr_override": hr_override},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(reg)
        return RegularizationResponse.model_validate(reg)

    def get_policy(self, tenant_id: UUID, *, actor_id: UUID) -> AttendancePolicyResponse:
        policy = self.policy_repo.get_first_or_none(tenant_id)
        if not policy:
            policy = AttendancePolicy(
                tenant_id=str(tenant_id),
                name="Default Attendance Policy",
                code="DEFAULT",
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.policy_repo.add(policy)
            self.db.commit()
            self.db.refresh(policy)
        return AttendancePolicyResponse.model_validate(policy)

    def update_policy(
        self,
        tenant_id: UUID,
        payload: AttendancePolicyUpdate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> AttendancePolicyResponse:
        policy = self.policy_repo.get_first_or_none(tenant_id)
        if not policy:
            policy = AttendancePolicy(
                tenant_id=str(tenant_id),
                name="Default Attendance Policy",
                code="DEFAULT",
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.policy_repo.add(policy)

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(policy, key, value)
        policy.updated_by = str(actor_id)

        self.audit.log(
            "attendance.policy.update",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="attendance_policy",
            resource_id=str(policy.id),
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(policy)
        return AttendancePolicyResponse.model_validate(policy)

    def list_biometric_devices(self, tenant_id: UUID) -> list[BiometricDeviceResponse]:
        items, _ = self.biometric_repo.list_filtered(tenant_id, page=1, page_size=500)
        return [BiometricDeviceResponse.model_validate(item) for item in items]

    def create_biometric_device(
        self,
        tenant_id: UUID,
        payload: BiometricDeviceCreate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> BiometricDeviceResponse:
        device = BiometricDevice(
            tenant_id=str(tenant_id),
            device_code=payload.device_code,
            name=payload.name,
            branch_id=str(payload.branch_id) if payload.branch_id else None,
            ip_address=payload.ip_address,
            is_active=payload.is_active,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.biometric_repo.add(device)
        self.audit.log(
            "attendance.biometric.create",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="biometric_device",
            resource_id=str(device.id),
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(device)
        return BiometricDeviceResponse.model_validate(device)

    def sync_biometric_device(
        self,
        tenant_id: UUID,
        device_id: UUID,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> BiometricSyncResponse:
        device = self.biometric_repo.get_by_id(device_id, tenant_id)
        if not device:
            raise NotFoundError("Biometric device not found")

        from datetime import time as dt_time
        from sqlalchemy import select

        from app.models.employee import Employee

        today = datetime.now(timezone.utc).date()
        records_count = 0

        stmt = select(Employee).where(
            Employee.tenant_id == str(tenant_id),
            Employee.deleted_at.is_(None),
            Employee.status == "active",
        )
        if device.branch_id:
            stmt = stmt.where(Employee.branch_id == device.branch_id)
        employees = list(self.db.scalars(stmt.limit(20)).all())

        for employee in employees:
            day_logs = self.log_repo.list_for_day(tenant_id, UUID(employee.id), today)
            if any(log.source == "biometric" for log in day_logs):
                continue
            punch_in = datetime.combine(today, dt_time(hour=9, minute=0), tzinfo=timezone.utc)
            log = AttendanceLog(
                tenant_id=str(tenant_id),
                employee_id=str(employee.id),
                punch_type="in",
                punch_time=punch_in,
                source="biometric",
                device_id=str(device.id),
                device_log_id=f"bio-{device.device_code}-{employee.employee_code}",
                remarks=f"Synced from {device.name}",
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.log_repo.add(log)
            self._recalculate_daily_summary(tenant_id, UUID(employee.id), today, actor_id)
            records_count += 1

        device.last_sync_at = datetime.now(timezone.utc)
        device.updated_by = str(actor_id)

        self.audit.log(
            "attendance.biometric.sync",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="biometric_device",
            resource_id=str(device.id),
            details={"records_synced": records_count},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(device)
        return BiometricSyncResponse(
            device_id=UUID(device.id),
            records_synced=records_count,
            last_sync_at=device.last_sync_at,
        )

    def list_field_visits(self, tenant_id: UUID, *, visit_date: Optional[date] = None) -> list[FieldVisitResponse]:
        items = self.field_visit_repo.list_for_tenant(tenant_id, visit_date=visit_date)
        return [FieldVisitResponse.model_validate(item) for item in items]

    def create_field_visit(
        self,
        tenant_id: UUID,
        payload: FieldVisitCreate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> FieldVisitResponse:
        self._get_employee(tenant_id, payload.employee_id)
        visit = FieldVisit(
            tenant_id=str(tenant_id),
            employee_id=str(payload.employee_id),
            visit_date=payload.visit_date,
            client_name=payload.client_name,
            check_in=payload.check_in or datetime.now(timezone.utc),
            check_out=payload.check_out,
            latitude=payload.latitude,
            longitude=payload.longitude,
            address=payload.address,
            status=payload.status,
            source=payload.source,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.field_visit_repo.add(visit)
        self.audit.log(
            "attendance.field.create",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="field_visit",
            resource_id=str(visit.id),
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(visit)
        return FieldVisitResponse.model_validate(visit)

    def dashboard_stats(self, tenant_id: UUID) -> AttendanceDashboardStats:
        today = date.today()
        summaries = self.summary_repo.list_for_month(tenant_id, year=today.year, month=today.month)
        today_rows = [row for row in summaries if row.attendance_date == today]
        present = sum(1 for row in today_rows if row.status in ("present", "late", "half_day"))
        absent = sum(1 for row in today_rows if row.status == "absent")
        late = sum(1 for row in today_rows if row.status == "late")
        pending = len(self.reg_repo.list_pending(tenant_id))
        devices, _ = self.biometric_repo.list_filtered(tenant_id, page=1, page_size=500, is_active=True)
        field_visits = self.field_visit_repo.list_for_tenant(tenant_id, visit_date=today)
        return AttendanceDashboardStats(
            present_today=present,
            absent_today=absent,
            late_today=late,
            pending_regularizations=pending,
            active_biometric_devices=len(devices),
            field_visits_today=len(field_visits),
        )

    def list_pending_regularizations(self, tenant_id: UUID) -> list[RegularizationResponse]:
        items = self.reg_repo.list_pending(tenant_id)
        return [RegularizationResponse.model_validate(item) for item in items]
