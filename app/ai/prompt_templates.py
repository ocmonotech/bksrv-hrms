from __future__ import annotations

import json
from enum import Enum
from typing import Any, Optional


class PromptType(str, Enum):
    HR_CHATBOT = "hr_chatbot"
    POLICY_GENERATOR = "policy_generator"
    LETTER_GENERATOR = "letter_generator"
    EMPLOYEE_SUMMARY = "employee_summary"
    ATTENDANCE_ANALYSIS = "attendance_analysis"
    LEAVE_PATTERN_ANALYSIS = "leave_pattern_analysis"
    PAYROLL_ERROR_CHECK = "payroll_error_check"
    RESUME_SCREENING = "resume_screening"
    JOB_DESCRIPTION_GENERATOR = "job_description_generator"
    PERFORMANCE_SUMMARY = "performance_summary"
    MODULE_INSIGHTS = "module_insights"


SYSTEM_PROMPTS = {
    PromptType.HR_CHATBOT: (
        "You are an HR assistant for an Indian HRMS platform. "
        "Answer clearly, professionally, and only using provided context. "
        "Do not invent employee-specific data. Suggest HR policy review when unsure."
    ),
    PromptType.POLICY_GENERATOR: (
        "You are an HR policy writer for Indian companies. "
        "Generate structured, compliant HR policy drafts in markdown."
    ),
    PromptType.LETTER_GENERATOR: (
        "You are an HR letter writer. Generate formal employment letters suitable for Indian organizations."
    ),
    PromptType.EMPLOYEE_SUMMARY: (
        "Summarize employee HR data concisely for managers. Highlight attendance, leave, and employment status."
    ),
    PromptType.ATTENDANCE_ANALYSIS: (
        "Analyze attendance data and flag anomalies, late patterns, and LOP risks."
    ),
    PromptType.LEAVE_PATTERN_ANALYSIS: (
        "Analyze leave patterns for abuse, sandwich leave risk, and team coverage impact."
    ),
    PromptType.PAYROLL_ERROR_CHECK: (
        "Review payroll data for calculation errors, statutory mismatches, and anomalies."
    ),
    PromptType.RESUME_SCREENING: (
        "Score and summarize a candidate resume against a job opening. Provide structured hiring recommendation."
    ),
    PromptType.JOB_DESCRIPTION_GENERATOR: (
        "Write professional job descriptions for Indian hiring contexts."
    ),
    PromptType.PERFORMANCE_SUMMARY: (
        "Summarize employee performance based on goals, reviews, and appraisal data."
    ),
    PromptType.MODULE_INSIGHTS: (
        "Provide actionable HR insights for the requested module. "
        "Return JSON array with objects: title, summary, severity (info|warning|critical), recommendation."
    ),
}


def build_chat_prompt(message: str, context: Optional[dict[str, Any]] = None) -> str:
    parts = [f"User question:\n{message}"]
    if context:
        parts.append(f"\nContext:\n{json.dumps(context, default=str, indent=2)}")
    return "\n".join(parts)


def build_policy_prompt(policy_type: str, requirements: str, context: Optional[dict] = None) -> str:
    return (
        f"Policy type: {policy_type}\n"
        f"Requirements:\n{requirements}\n"
        f"Additional context:\n{json.dumps(context or {}, default=str, indent=2)}"
    )


def build_letter_prompt(letter_type: str, details: str, context: Optional[dict] = None) -> str:
    return (
        f"Letter type: {letter_type}\n"
        f"Details:\n{details}\n"
        f"Employee/context:\n{json.dumps(context or {}, default=str, indent=2)}"
    )


def build_context_prompt(prompt_type: PromptType, context: dict[str, Any]) -> str:
    return (
        f"Analyze the following {prompt_type.value.replace('_', ' ')} data:\n"
        f"{json.dumps(context, default=str, indent=2)}"
    )


def get_system_prompt(prompt_type: PromptType) -> str:
    return SYSTEM_PROMPTS.get(prompt_type, "You are a helpful HR assistant.")
