from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.ai_logs import AILogRepository
from app.ai.ai_provider import get_ai_provider, safe_complete
from app.ai.prompt_templates import (
    PromptType,
    build_chat_prompt,
    build_context_prompt,
    build_letter_prompt,
    build_policy_prompt,
    get_system_prompt,
)
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.enums import PermissionModule
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.payroll_repository import PayrollRunRepository
from app.repositories.recruitment_repository import CandidateRepository, JobOpeningRepository
from app.schemas.ai import AIInsightItem
from app.services.audit_service import AuditService

MODULE_INSIGHT_PROMPTS = {
    "leave": "Analyze leave utilization, pending approvals, and balance risks for this tenant.",
    "attendance": "Analyze attendance compliance, late arrivals, absenteeism, and regularization backlog.",
    "payroll": "Analyze payroll readiness, statutory deductions, and processing risks.",
    "recruitment": "Analyze hiring pipeline health, open roles, and candidate flow.",
    "performance": "Analyze goal completion, review cycles, and appraisal readiness.",
    "employees": "Analyze workforce composition, headcount trends, and attrition signals.",
    "dashboard": "Provide a concise cross-module HR risk and opportunity summary for leadership.",
    "company": "Analyze company structure, policy gaps, and organizational setup risks.",
    "settings": "Analyze roles, permissions, and access-control risk signals.",
    "helpdesk": "Analyze ticket backlog, SLA risk, and recurring employee issues.",
    "documents": "Analyze document compliance gaps and expiring records.",
    "expenses": "Analyze expense claim patterns, approval delays, and policy violations.",
    "assets": "Analyze asset allocation, return delays, and inventory risk.",
    "travel": "Analyze travel request volume, approval delays, and policy exceptions.",
    "onboarding": "Analyze onboarding progress, pending tasks, and new-hire bottlenecks.",
    "exit": "Analyze resignations, exit checklist completion, and attrition signals.",
    "communication": "Analyze announcement reach and employee communication engagement.",
    "shiftroster": "Analyze shift coverage gaps, overtime risk, and roster conflicts.",
}


class AIService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.log_repo = AILogRepository(db)
        self.employee_repo = EmployeeRepository(db)
        self.candidate_repo = CandidateRepository(db)
        self.job_repo = JobOpeningRepository(db)
        self.payroll_run_repo = PayrollRunRepository(db)
        self.audit = AuditService(db)
        self.provider = get_ai_provider(self.settings)

    def _check_usage_limit(self, tenant_id: UUID) -> None:
        used = self.log_repo.count_monthly_requests(tenant_id)
        limit = self.settings.ai_monthly_limit_per_tenant
        if used >= limit:
            raise ForbiddenError(
                f"Monthly AI usage limit reached ({limit} requests). Contact your administrator."
            )

    def _run(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        module_name: str,
        prompt_type: PromptType,
        user_prompt: str,
        request_summary: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        self._check_usage_limit(tenant_id)
        system_prompt = get_system_prompt(prompt_type)

        result = safe_complete(
            self.provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_type=prompt_type.value,
            temperature=self.settings.ai_temperature,
            max_tokens=self.settings.ai_max_tokens,
        )

        log = self.log_repo.create(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=module_name,
            prompt_type=prompt_type.value,
            provider=result.provider_name,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            is_fallback=result.is_fallback,
            request_summary=request_summary,
            response_summary=result.content,
        )

        self.audit.log(
            "ai.request",
            actor_id=user_id,
            tenant_id=tenant_id,
            resource_type="ai",
            resource_id=str(log.id),
            details={"prompt_type": prompt_type.value, "module": module_name},
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
        self.db.commit()

        return {
            "content": result.content,
            "prompt_type": prompt_type.value,
            "module": module_name,
            "provider": result.provider_name,
            "model": result.model,
            "is_fallback": result.is_fallback,
            "token_usage": result.token_usage,
            "log_id": str(log.id),
        }

    def chat(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        message: str,
        context: Optional[dict] = None,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        if not message.strip():
            raise ValidationError("Message is required")
        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=PermissionModule.AI.value,
            prompt_type=PromptType.HR_CHATBOT,
            user_prompt=build_chat_prompt(message, context),
            request_summary=message[:500],
            meta=meta,
        )

    def generate_policy(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        policy_type: str,
        requirements: str,
        context: Optional[dict] = None,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name="policy",
            prompt_type=PromptType.POLICY_GENERATOR,
            user_prompt=build_policy_prompt(policy_type, requirements, context),
            request_summary=f"policy_type={policy_type}",
            meta=meta,
        )

    def generate_letter(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        letter_type: str,
        details: str,
        employee_id: Optional[UUID] = None,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if employee_id:
            employee = self.employee_repo.get_by_id(employee_id, tenant_id)
            if not employee:
                raise NotFoundError("Employee not found")
            context = {
                "employee_code": employee.employee_code,
                "name": f"{employee.first_name} {employee.last_name}",
                "email": employee.email,
                "department_id": str(employee.department_id) if employee.department_id else None,
            }
        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name="letter",
            prompt_type=PromptType.LETTER_GENERATOR,
            user_prompt=build_letter_prompt(letter_type, details, context),
            request_summary=f"letter_type={letter_type}",
            meta=meta,
        )

    def summarize_employee(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        employee_id: UUID,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        employee = self.employee_repo.get_profile(employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")
        context = {
            "employee_code": employee.employee_code,
            "name": f"{employee.first_name} {employee.last_name}",
            "email": employee.email,
            "status": employee.status,
            "employment_type": employee.employment_type,
            "joining_date": str(employee.joining_date) if employee.joining_date else None,
            "department_id": str(employee.department_id) if employee.department_id else None,
            "designation_id": str(employee.designation_id) if employee.designation_id else None,
        }
        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=PermissionModule.EMPLOYEES.value,
            prompt_type=PromptType.EMPLOYEE_SUMMARY,
            user_prompt=build_context_prompt(PromptType.EMPLOYEE_SUMMARY, context),
            request_summary=f"employee_id={employee_id}",
            meta=meta,
        )

    def analyze_attendance(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        employee_id: UUID,
        month: int,
        year: int,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        from app.repositories.payroll_repository import AttendanceSummaryRepository

        if not self.employee_repo.get_by_id(employee_id, tenant_id):
            raise NotFoundError("Employee not found")
        payable, lop, overtime = AttendanceSummaryRepository(self.db).aggregate_for_month(
            tenant_id, employee_id, month, year
        )
        context = {
            "employee_id": str(employee_id),
            "month": month,
            "year": year,
            "payable_days": payable,
            "lop_days": lop,
            "overtime_minutes": overtime,
        }
        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=PermissionModule.ATTENDANCE.value,
            prompt_type=PromptType.ATTENDANCE_ANALYSIS,
            user_prompt=build_context_prompt(PromptType.ATTENDANCE_ANALYSIS, context),
            request_summary=f"attendance employee_id={employee_id} {year}-{month}",
            meta=meta,
        )

    def analyze_leave_pattern(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        employee_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        from app.repositories.leave_repository import LeaveRequestRepository

        if not employee_id and not department_id:
            raise ValidationError("employee_id or department_id is required")

        items, total = LeaveRequestRepository(self.db).list_filtered(
            tenant_id, page=1, page_size=50, employee_id=employee_id, status="approved"
        )
        context = {
            "employee_id": str(employee_id) if employee_id else None,
            "department_id": str(department_id) if department_id else None,
            "approved_leave_count": total,
            "recent_leaves": [
                {
                    "start_date": str(r.start_date),
                    "end_date": str(r.end_date),
                    "total_days": str(r.total_days),
                    "sandwich_days": str(r.sandwich_days),
                    "lop_days": str(r.lop_days),
                }
                for r in items[:10]
            ],
        }
        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=PermissionModule.LEAVE.value,
            prompt_type=PromptType.LEAVE_PATTERN_ANALYSIS,
            user_prompt=build_context_prompt(PromptType.LEAVE_PATTERN_ANALYSIS, context),
            request_summary="leave_pattern_analysis",
            meta=meta,
        )

    def payroll_error_check(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        payroll_run_id: UUID,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        from app.repositories.payroll_repository import PayrollEmployeeRepository

        run = self.payroll_run_repo.get_scoped(payroll_run_id, tenant_id)
        if not run:
            raise NotFoundError("Payroll run not found")
        employees = PayrollEmployeeRepository(self.db).list_for_run(payroll_run_id)
        context = {
            "payroll_run_id": str(payroll_run_id),
            "month": run.month,
            "year": run.year,
            "status": run.status,
            "total_gross": str(run.total_gross),
            "total_deductions": str(run.total_deductions),
            "total_net": str(run.total_net),
            "employee_count": run.employee_count,
            "employees": [
                {
                    "employee_id": str(pe.employee_id),
                    "gross": str(pe.gross_earnings),
                    "deductions": str(pe.total_deductions),
                    "net": str(pe.net_pay),
                    "lop_days": str(pe.lop_days),
                    "pf": str(pe.pf_employee),
                    "esi": str(pe.esi_employee),
                }
                for pe in employees[:20]
            ],
        }
        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=PermissionModule.PAYROLL.value,
            prompt_type=PromptType.PAYROLL_ERROR_CHECK,
            user_prompt=build_context_prompt(PromptType.PAYROLL_ERROR_CHECK, context),
            request_summary=f"payroll_run_id={payroll_run_id}",
            meta=meta,
        )

    def resume_score(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        candidate_id: UUID,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        candidate = self.candidate_repo.get_by_id(candidate_id, tenant_id)
        if not candidate:
            raise NotFoundError("Candidate not found")
        job = self.job_repo.get_by_id(candidate.job_opening_id, tenant_id)
        context = {
            "candidate": {
                "name": f"{candidate.first_name} {candidate.last_name}",
                "email": candidate.email,
                "experience_years": str(candidate.experience_years) if candidate.experience_years else None,
                "current_company": candidate.current_company,
                "current_stage": candidate.current_stage,
                "resume_path": candidate.resume_path,
            },
            "job": {
                "title": job.title if job else None,
                "requirements": job.requirements if job else None,
            },
        }
        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=PermissionModule.RECRUITMENT.value,
            prompt_type=PromptType.RESUME_SCREENING,
            user_prompt=build_context_prompt(PromptType.RESUME_SCREENING, context),
            request_summary=f"candidate_id={candidate_id}",
            meta=meta,
        )

    def generate_job_description(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        job_opening_id: Optional[UUID] = None,
        title: Optional[str] = None,
        requirements: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if job_opening_id:
            job = self.job_repo.get_by_id(job_opening_id, tenant_id)
            if not job:
                raise NotFoundError("Job opening not found")
            context = {
                "title": job.title,
                "code": job.code,
                "description": job.description,
                "requirements": job.requirements,
                "salary_min": str(job.salary_min) if job.salary_min else None,
                "salary_max": str(job.salary_max) if job.salary_max else None,
            }
        else:
            if not title:
                raise ValidationError("title or job_opening_id is required")
            context = {"title": title, "requirements": requirements or ""}

        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=PermissionModule.RECRUITMENT.value,
            prompt_type=PromptType.JOB_DESCRIPTION_GENERATOR,
            user_prompt=build_context_prompt(PromptType.JOB_DESCRIPTION_GENERATOR, context),
            request_summary=f"job_description title={context.get('title')}",
            meta=meta,
        )

    def performance_summary(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        employee_id: UUID,
        review_cycle_id: Optional[UUID] = None,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        from app.repositories.performance_repository import AppraisalRepository, GoalRepository

        employee = self.employee_repo.get_by_id(employee_id, tenant_id)
        if not employee:
            raise NotFoundError("Employee not found")

        goals, _ = GoalRepository(self.db).list_filtered(tenant_id, page=1, page_size=20, employee_id=employee_id)
        appraisals, _ = AppraisalRepository(self.db).list_filtered(
            tenant_id, page=1, page_size=5, employee_id=employee_id, review_cycle_id=review_cycle_id
        )
        context = {
            "employee": {
                "name": f"{employee.first_name} {employee.last_name}",
                "employee_code": employee.employee_code,
            },
            "goals": [{"title": g.title, "progress": str(g.progress), "status": g.status} for g in goals],
            "appraisals": [
                {
                    "final_rating": str(a.final_rating) if a.final_rating else None,
                    "increment_percent": str(a.increment_percent) if a.increment_percent else None,
                    "status": a.status,
                }
                for a in appraisals
            ],
        }
        return self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=PermissionModule.PERFORMANCE.value,
            prompt_type=PromptType.PERFORMANCE_SUMMARY,
            user_prompt=build_context_prompt(PromptType.PERFORMANCE_SUMMARY, context),
            request_summary=f"performance_summary employee_id={employee_id}",
            meta=meta,
        )

    def get_usage(self, tenant_id: UUID) -> dict[str, Any]:
        used = self.log_repo.count_monthly_requests(tenant_id)
        limit = self.settings.ai_monthly_limit_per_tenant
        return {
            "used_this_month": used,
            "monthly_limit": limit,
            "remaining": max(limit - used, 0),
            "provider": self.settings.ai_provider,
        }

    def module_insights(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        module: str,
        meta: Optional[dict] = None,
    ) -> dict[str, Any]:
        module_key = (module or "").strip().lower().replace("-", "").replace("_", "")
        # Normalize aliases like shiftRoster → shiftroster
        prompt_text = MODULE_INSIGHT_PROMPTS.get(module_key)
        if not prompt_text:
            prompt_text = (
                f"Analyze the '{module}' module for risks, anomalies, and actionable HR recommendations."
            )
        prompt = (
            f"{prompt_text}\n"
            "Respond ONLY with a JSON array of insight objects with keys: "
            "title, summary, severity, recommendation."
        )
        result = self._run(
            tenant_id=tenant_id,
            user_id=user_id,
            module_name=module_key or (module or "general").strip().lower(),
            prompt_type=PromptType.MODULE_INSIGHTS,
            user_prompt=prompt,
            request_summary=f"module_insights module={module_key or module}",
            meta=meta,
        )

        insights: list[AIInsightItem] = []
        try:
            parsed = json.loads(result["content"])
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        insights.append(
                            AIInsightItem(
                                title=str(item.get("title", "Insight")),
                                summary=str(item.get("summary", "")),
                                severity=str(item.get("severity", "info")),
                                recommendation=item.get("recommendation"),
                            )
                        )
        except json.JSONDecodeError:
            insights.append(
                AIInsightItem(
                    title=f"{module_key.title()} insight",
                    summary=result["content"],
                    severity="info",
                )
            )

        if not insights:
            insights.append(
                AIInsightItem(
                    title=f"{module_key.title()} overview",
                    summary=result["content"][:500],
                    severity="info",
                )
            )

        return {
            "module": module_key,
            "insights": [item.model_dump() for item in insights],
            "generated_at": datetime.now(timezone.utc),
            "provider": result["provider"],
            "log_id": result["log_id"],
        }
