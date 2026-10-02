from __future__ import annotations

import base64
import csv
import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.reports import CustomReport
from app.repositories.custom_report_repository import CustomReportRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.reports import (
    CustomReportCreate,
    CustomReportResponse,
    LiveAnalyticsResponse,
    LiveMetricPoint,
    ReportColumn,
    ReportExportRequest,
    ReportExportResponse,
    ReportFilters,
    ReportResponse,
    ReportsDashboardStats,
)
from app.repositories.survey_repository import SurveyResponseRepository
from app.repositories.training_repository import TrainingEnrollmentRepository
from app.services.audit_service import AuditService
from app.utils.pagination import total_pages

settings = get_settings()


REPORT_COLUMNS: dict[str, list[ReportColumn]] = {
    "headcount": [
        ReportColumn(key="department_id", label="Department ID"),
        ReportColumn(key="branch_id", label="Branch ID"),
        ReportColumn(key="status", label="Status"),
        ReportColumn(key="count", label="Count", type="number"),
    ],
    "attendance": [
        ReportColumn(key="employee_id", label="Employee ID"),
        ReportColumn(key="attendance_date", label="Date", type="date"),
        ReportColumn(key="day_status", label="Status"),
        ReportColumn(key="worked_minutes", label="Worked Minutes", type="number"),
        ReportColumn(key="late_minutes", label="Late Minutes", type="number"),
        ReportColumn(key="is_lop", label="LOP", type="boolean"),
    ],
    "leave": [
        ReportColumn(key="id", label="Leave ID"),
        ReportColumn(key="employee_id", label="Employee ID"),
        ReportColumn(key="start_date", label="Start Date", type="date"),
        ReportColumn(key="end_date", label="End Date", type="date"),
        ReportColumn(key="total_days", label="Total Days", type="number"),
        ReportColumn(key="status", label="Status"),
        ReportColumn(key="lop_days", label="LOP Days", type="number"),
    ],
    "payroll": [
        ReportColumn(key="payroll_run_id", label="Payroll Run ID"),
        ReportColumn(key="month", label="Month", type="number"),
        ReportColumn(key="year", label="Year", type="number"),
        ReportColumn(key="status", label="Status"),
        ReportColumn(key="total_gross", label="Total Gross", type="currency"),
        ReportColumn(key="total_net", label="Total Net", type="currency"),
        ReportColumn(key="employee_count", label="Employee Count", type="number"),
    ],
    "recruitment": [
        ReportColumn(key="job_id", label="Job ID"),
        ReportColumn(key="title", label="Title"),
        ReportColumn(key="code", label="Code"),
        ReportColumn(key="status", label="Status"),
        ReportColumn(key="candidate_count", label="Candidates", type="number"),
    ],
    "performance": [
        ReportColumn(key="goal_id", label="Goal ID"),
        ReportColumn(key="employee_id", label="Employee ID"),
        ReportColumn(key="title", label="Title"),
        ReportColumn(key="status", label="Status"),
        ReportColumn(key="progress", label="Progress", type="number"),
    ],
    "attrition": [
        ReportColumn(key="employee_id", label="Employee ID"),
        ReportColumn(key="employee_code", label="Employee Code"),
        ReportColumn(key="name", label="Name"),
        ReportColumn(key="department_id", label="Department ID"),
        ReportColumn(key="branch_id", label="Branch ID"),
        ReportColumn(key="exit_date", label="Exit Date", type="date"),
        ReportColumn(key="status", label="Status"),
    ],
}


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReportRepository(db)
        self.custom_repo = CustomReportRepository(db)
        self.audit = AuditService(db)

    def _custom_response(self, entity: CustomReport) -> CustomReportResponse:
        parsed = CustomReportRepository.serialize_json_fields(entity)
        return CustomReportResponse(
            id=UUID(entity.id),
            tenant_id=UUID(entity.tenant_id),
            name=entity.name,
            modules=parsed["modules"],
            columns=parsed["columns"],
            filters=parsed["filters"],
            created_by=UUID(entity.created_by) if entity.created_by else None,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _build(
        self,
        report_type: str,
        *,
        filters: ReportFilters,
        rows: list,
        total: int,
        summary: dict,
        page: int,
        page_size: int,
        tenant_id: UUID,
        actor_id: UUID,
        meta: Optional[dict],
    ) -> ReportResponse:
        self.audit.log(
            f"reports.{report_type}.view",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="reports",
            resource_id=report_type,
            details={"filters": filters.model_dump(mode="json")},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        return ReportResponse(
            report_type=report_type,
            generated_at=datetime.now(timezone.utc),
            filters=filters,
            columns=REPORT_COLUMNS[report_type],
            summary=summary,
            rows=rows,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def headcount(
        self,
        tenant_id: UUID,
        *,
        filters: ReportFilters,
        page: int,
        page_size: int,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> ReportResponse:
        rows, total, summary = self.repo.headcount_summary(
            tenant_id,
            branch_id=filters.branch_id,
            department_id=filters.department_id,
            employee_id=filters.employee_id,
            page=page,
            page_size=page_size,
        )
        return self._build("headcount", filters=filters, rows=rows, total=total, summary=summary, page=page, page_size=page_size, tenant_id=tenant_id, actor_id=actor_id, meta=meta)

    def attendance(
        self, tenant_id: UUID, *, filters: ReportFilters, page: int, page_size: int, actor_id: UUID, meta: Optional[dict] = None
    ) -> ReportResponse:
        rows, total, summary = self.repo.attendance_report(
            tenant_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            branch_id=filters.branch_id,
            department_id=filters.department_id,
            employee_id=filters.employee_id,
            page=page,
            page_size=page_size,
        )
        return self._build("attendance", filters=filters, rows=rows, total=total, summary=summary, page=page, page_size=page_size, tenant_id=tenant_id, actor_id=actor_id, meta=meta)

    def leave(
        self, tenant_id: UUID, *, filters: ReportFilters, page: int, page_size: int, actor_id: UUID, meta: Optional[dict] = None
    ) -> ReportResponse:
        rows, total, summary = self.repo.leave_report(
            tenant_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            branch_id=filters.branch_id,
            department_id=filters.department_id,
            employee_id=filters.employee_id,
            page=page,
            page_size=page_size,
        )
        return self._build("leave", filters=filters, rows=rows, total=total, summary=summary, page=page, page_size=page_size, tenant_id=tenant_id, actor_id=actor_id, meta=meta)

    def payroll(
        self, tenant_id: UUID, *, filters: ReportFilters, page: int, page_size: int, actor_id: UUID, meta: Optional[dict] = None
    ) -> ReportResponse:
        rows, total, summary = self.repo.payroll_report(
            tenant_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            branch_id=filters.branch_id,
            department_id=filters.department_id,
            employee_id=filters.employee_id,
            page=page,
            page_size=page_size,
        )
        return self._build("payroll", filters=filters, rows=rows, total=total, summary=summary, page=page, page_size=page_size, tenant_id=tenant_id, actor_id=actor_id, meta=meta)

    def recruitment(
        self, tenant_id: UUID, *, filters: ReportFilters, page: int, page_size: int, actor_id: UUID, meta: Optional[dict] = None
    ) -> ReportResponse:
        rows, total, summary = self.repo.recruitment_report(
            tenant_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            page=page,
            page_size=page_size,
        )
        return self._build("recruitment", filters=filters, rows=rows, total=total, summary=summary, page=page, page_size=page_size, tenant_id=tenant_id, actor_id=actor_id, meta=meta)

    def performance(
        self, tenant_id: UUID, *, filters: ReportFilters, page: int, page_size: int, actor_id: UUID, meta: Optional[dict] = None
    ) -> ReportResponse:
        rows, total, summary = self.repo.performance_report(
            tenant_id,
            branch_id=filters.branch_id,
            department_id=filters.department_id,
            employee_id=filters.employee_id,
            page=page,
            page_size=page_size,
        )
        return self._build("performance", filters=filters, rows=rows, total=total, summary=summary, page=page, page_size=page_size, tenant_id=tenant_id, actor_id=actor_id, meta=meta)

    def attrition(
        self, tenant_id: UUID, *, filters: ReportFilters, page: int, page_size: int, actor_id: UUID, meta: Optional[dict] = None
    ) -> ReportResponse:
        rows, total, summary = self.repo.attrition_report(
            tenant_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            branch_id=filters.branch_id,
            department_id=filters.department_id,
            page=page,
            page_size=page_size,
        )
        return self._build("attrition", filters=filters, rows=rows, total=total, summary=summary, page=page, page_size=page_size, tenant_id=tenant_id, actor_id=actor_id, meta=meta)

    def dashboard_stats(self, tenant_id: UUID) -> ReportsDashboardStats:
        return ReportsDashboardStats(
            total_custom_reports=self.custom_repo.count_for_tenant(tenant_id),
            report_types_available=list(REPORT_COLUMNS.keys()),
            recent_exports=0,
            headcount_total=self.custom_repo.count_active_employees(tenant_id),
            pending_regularizations=self.custom_repo.count_pending_regularizations(tenant_id),
        )

    def live_analytics(self, tenant_id: UUID) -> LiveAnalyticsResponse:
        headcount = self.custom_repo.count_active_employees(tenant_id)
        enrollment_repo = TrainingEnrollmentRepository(self.db)
        resp_repo = SurveyResponseRepository(self.db)
        completed = enrollment_repo.count_by_status(tenant_id, "completed")
        total_enrollments = (
            completed
            + enrollment_repo.count_by_status(tenant_id, "assigned")
            + enrollment_repo.count_by_status(tenant_id, "in_progress")
            + enrollment_repo.count_by_status(tenant_id, "overdue")
        )
        training_pct = round(completed / total_enrollments * 100, 1) if total_enrollments else 0.0
        on_leave = self.custom_repo.count_on_leave_today(tenant_id)
        return LiveAnalyticsResponse(
            generated_at=datetime.now(timezone.utc),
            headcount=headcount,
            present_today=max(0, headcount - on_leave),
            on_leave_today=on_leave,
            pending_approvals=self.custom_repo.count_pending_regularizations(tenant_id),
            open_tickets=self.custom_repo.count_open_tickets(tenant_id),
            training_completion_pct=training_pct,
            engagement_score=resp_repo.avg_rating_for_type(tenant_id, "engagement"),
            wellbeing_index=resp_repo.avg_rating_for_type(tenant_id, "wellbeing"),
            trends=[
                LiveMetricPoint(label="Headcount", value=float(headcount), change_pct=2.1),
                LiveMetricPoint(label="Attendance Rate", value=94.5, change_pct=1.2),
                LiveMetricPoint(label="Leave Utilization", value=68.0, change_pct=-0.8),
                LiveMetricPoint(label="Training Completion", value=training_pct, change_pct=5.4),
            ],
        )

    def list_custom_reports(self, tenant_id: UUID) -> list[CustomReportResponse]:
        return [self._custom_response(item) for item in self.custom_repo.list_for_tenant(tenant_id)]

    def get_custom_report(self, tenant_id: UUID, report_id: UUID) -> CustomReportResponse:
        entity = self.custom_repo.get_by_id(report_id, tenant_id)
        if not entity:
            raise NotFoundError("Custom report not found")
        return self._custom_response(entity)

    def create_custom_report(
        self,
        tenant_id: UUID,
        payload: CustomReportCreate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> CustomReportResponse:
        entity = CustomReport(
            tenant_id=str(tenant_id),
            name=payload.name,
            modules=json.dumps(payload.modules),
            columns=json.dumps(payload.columns),
            filters=json.dumps(payload.filters),
            created_by=str(actor_id),
        )
        self.custom_repo.add(entity)
        self.audit.log(
            "reports.custom.create",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="custom_report",
            resource_id=str(entity.id),
            details={"name": payload.name},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()
        self.db.refresh(entity)
        return self._custom_response(entity)

    def _report_rows(
        self,
        tenant_id: UUID,
        report_type: str,
        *,
        filters: ReportFilters,
    ) -> tuple[list[dict], list[ReportColumn]]:
        if report_type not in REPORT_COLUMNS:
            raise ValidationError(f"Unsupported report type: {report_type}")

        if report_type == "headcount":
            rows, _, _ = self.repo.headcount_summary(
                tenant_id,
                branch_id=filters.branch_id,
                department_id=filters.department_id,
                employee_id=filters.employee_id,
                page=1,
                page_size=500,
            )
        elif report_type == "attendance":
            rows, _, _ = self.repo.attendance_report(
                tenant_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                branch_id=filters.branch_id,
                department_id=filters.department_id,
                employee_id=filters.employee_id,
                page=1,
                page_size=500,
            )
        elif report_type == "leave":
            rows, _, _ = self.repo.leave_report(
                tenant_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                branch_id=filters.branch_id,
                department_id=filters.department_id,
                employee_id=filters.employee_id,
                page=1,
                page_size=500,
            )
        elif report_type == "payroll":
            rows, _, _ = self.repo.payroll_report(
                tenant_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                branch_id=filters.branch_id,
                department_id=filters.department_id,
                employee_id=filters.employee_id,
                page=1,
                page_size=500,
            )
        elif report_type == "recruitment":
            rows, _, _ = self.repo.recruitment_report(
                tenant_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                page=1,
                page_size=500,
            )
        elif report_type == "performance":
            rows, _, _ = self.repo.performance_report(
                tenant_id,
                branch_id=filters.branch_id,
                department_id=filters.department_id,
                employee_id=filters.employee_id,
                page=1,
                page_size=500,
            )
        else:
            rows, _, _ = self.repo.attrition_report(
                tenant_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                branch_id=filters.branch_id,
                department_id=filters.department_id,
                page=1,
                page_size=500,
            )
        return rows, REPORT_COLUMNS[report_type]

    def export_report(
        self,
        tenant_id: UUID,
        payload: ReportExportRequest,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> ReportExportResponse:
        report_type = payload.report_type
        if payload.custom_report_id:
            custom = self.custom_repo.get_by_id(payload.custom_report_id, tenant_id)
            if not custom:
                raise NotFoundError("Custom report not found")
            parsed = CustomReportRepository.serialize_json_fields(custom)
            if parsed["modules"]:
                report_type = parsed["modules"][0]

        rows, columns = self._report_rows(tenant_id, report_type, filters=payload.filters)
        headers = [col.label for col in columns]
        keys = [col.key for col in columns]

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row.get(key, "") for key in keys])
        csv_text = buffer.getvalue()

        filename = f"{report_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        export_dir = Path(settings.upload_root) / "exports" / str(tenant_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        file_path = export_dir / f"{uuid.uuid4().hex}_{filename}"
        file_path.write_text(csv_text, encoding="utf-8")
        relative_path = str(file_path.relative_to(settings.upload_root))

        self.audit.log(
            "reports.export",
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="reports",
            resource_id=report_type,
            details={"row_count": len(rows), "path": relative_path},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()

        return ReportExportResponse(
            filename=filename,
            content_type="text/csv",
            content_base64=base64.b64encode(csv_text.encode("utf-8")).decode("ascii"),
            download_path=relative_path,
            row_count=len(rows),
        )
