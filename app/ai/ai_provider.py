from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import Settings, get_settings


@dataclass
class AICompletionResult:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    provider_name: str = "mock"
    model: Optional[str] = None
    is_fallback: bool = False

    @property
    def token_usage(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class AIProvider(ABC):
    """Pluggable AI backend — implement for OpenAI, Azure OpenAI, Anthropic, etc."""

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        prompt_type: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> AICompletionResult:
        ...


class MockAIProvider(AIProvider):
    """Deterministic mock responses for local development and tests."""

    name = "mock"

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        prompt_type: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> AICompletionResult:
        previews = {
            "hr_chatbot": "I'm your HR assistant. Based on your question, I recommend reviewing the company policy or contacting HR for account-specific details.",
            "policy_generator": "# Generated HR Policy\n\n## Purpose\nThis policy outlines standards for the organization.\n\n## Scope\nAll employees.\n\n## Guidelines\n- Follow company code of conduct\n- Report violations to HR",
            "letter_generator": "Dear Employee,\n\nThis letter is issued regarding your employment matter. Please contact HR for any clarifications.\n\nSincerely,\nHR Department",
            "employee_summary": "## Employee Summary\n- Active employee with satisfactory performance\n- Attendance: Regular\n- Leave balance: Within policy limits\n- No pending disciplinary actions noted",
            "attendance_analysis": "## Attendance Analysis\n- Overall attendance rate: 94%\n- Late arrivals: 2 instances this month\n- No significant anomalies detected\n- Recommendation: Monitor Monday late patterns",
            "leave_pattern_analysis": "## Leave Pattern Analysis\n- Predominantly planned leave around long weekends\n- No sandwich leave abuse detected\n- LOP days: Within normal range",
            "payroll_error_check": "## Payroll Review\n- No critical errors detected\n- PF/ESI calculations appear consistent\n- Verify one employee with partial month LOP",
            "resume_screening": "## Resume Score: 78/100\n**Strengths:** Relevant experience, stable tenure\n**Gaps:** Limited domain certifications\n**Recommendation:** Proceed to technical interview",
            "job_description_generator": "## Job Description\n\n### Role Overview\nWe are hiring for this position to strengthen our team.\n\n### Responsibilities\n- Deliver on team objectives\n- Collaborate cross-functionally\n\n### Requirements\n- Relevant degree or experience\n- Strong communication skills",
            "performance_summary": "## Performance Summary\n- Meets expectations on core goals\n- Demonstrates ownership and collaboration\n- Recommended for standard increment band",
        }
        content = previews.get(
            prompt_type,
            f"Mock AI response for `{prompt_type}`. Provider is in development mode.",
        )
        prompt_len = len(system_prompt) + len(user_prompt)
        prompt_tokens = max(prompt_len // 4, 50)
        completion_tokens = max(len(content) // 4, 30)
        return AICompletionResult(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            provider_name=self.name,
            model="mock-dev",
            is_fallback=False,
        )


class OpenAIProvider(AIProvider):
    """OpenAI-compatible chat completions API."""

    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.openai_model
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        prompt_type: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> AICompletionResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return AICompletionResult(
            content=choice,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
            provider_name=self.name,
            model=self.model,
            is_fallback=False,
        )


FALLBACK_MESSAGE = (
    "AI assistance is temporarily unavailable. "
    "Please try again later or contact your HR administrator."
)


def get_ai_provider(settings: Optional[Settings] = None) -> AIProvider:
    settings = settings or get_settings()
    provider = settings.ai_provider.lower().strip()

    if provider in ("auto", "openai"):
        if settings.openai_api_key:
            try:
                return OpenAIProvider(settings)
            except ValueError:
                pass
        if provider == "openai":
            return MockAIProvider()

    return MockAIProvider()


def safe_complete(
    provider: AIProvider,
    *,
    system_prompt: str,
    user_prompt: str,
    prompt_type: str,
    temperature: float = 0.3,
    max_tokens: int = 1500,
) -> AICompletionResult:
    """Call provider with safe fallback on any failure."""
    try:
        return provider.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_type=prompt_type,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception:
        mock = MockAIProvider()
        result = mock.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_type=prompt_type,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return AICompletionResult(
            content=FALLBACK_MESSAGE + "\n\n---\n\n" + result.content,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            provider_name=provider.name,
            model=result.model,
            is_fallback=True,
        )
