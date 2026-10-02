from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    context: Optional[dict[str, Any]] = None


class GeneratePolicyRequest(BaseModel):
    policy_type: str = Field(..., min_length=1, max_length=100)
    requirements: str = Field(..., min_length=10, max_length=5000)
    context: Optional[dict[str, Any]] = None


class GenerateLetterRequest(BaseModel):
    letter_type: str = Field(..., min_length=1, max_length=100)
    details: str = Field(..., min_length=10, max_length=5000)
    employee_id: Optional[UUID] = None


class SummarizeEmployeeRequest(BaseModel):
    employee_id: UUID


class AnalyzeAttendanceRequest(BaseModel):
    employee_id: UUID
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)


class AnalyzeLeavePatternRequest(BaseModel):
    employee_id: Optional[UUID] = None
    department_id: Optional[UUID] = None


class PayrollErrorCheckRequest(BaseModel):
    payroll_run_id: UUID


class ResumeScoreRequest(BaseModel):
    candidate_id: UUID


class GenerateJobDescriptionRequest(BaseModel):
    job_opening_id: Optional[UUID] = None
    title: Optional[str] = Field(default=None, max_length=255)
    requirements: Optional[str] = Field(default=None, max_length=5000)


class PerformanceSummaryRequest(BaseModel):
    employee_id: UUID
    review_cycle_id: Optional[UUID] = None


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AIResponse(BaseModel):
    content: str
    prompt_type: str
    module: str
    provider: str
    model: Optional[str] = None
    is_fallback: bool = False
    token_usage: TokenUsage
    log_id: str


class AIUsageResponse(BaseModel):
    used_this_month: int
    monthly_limit: int
    remaining: int
    provider: str


class AIInsightItem(BaseModel):
    title: str
    summary: str
    severity: str = "info"
    recommendation: Optional[str] = None


class AIInsightsResponse(BaseModel):
    module: str
    insights: list[AIInsightItem]
    generated_at: datetime
    provider: str
    log_id: Optional[str] = None
