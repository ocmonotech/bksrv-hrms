from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_log import AILog


class AILogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_monthly_requests(self, tenant_id: UUID) -> int:
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        if now.month == 12:
            month_end = datetime(now.year + 1, 1, 1)
        else:
            month_end = datetime(now.year, now.month + 1, 1)
        stmt = select(func.count()).select_from(AILog).where(
            AILog.tenant_id == str(tenant_id),
            AILog.created_at >= month_start,
            AILog.created_at < month_end,
        )
        return int(self.db.scalar(stmt) or 0)

    def create(
        self,
        *,
        tenant_id: UUID,
        user_id: Optional[UUID],
        module_name: str,
        prompt_type: str,
        provider: str,
        model: Optional[str],
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        is_fallback: bool,
        status: str = "success",
        error_message: Optional[str] = None,
        request_summary: Optional[str] = None,
        response_summary: Optional[str] = None,
    ) -> AILog:
        entry = AILog(
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
            module_name=module_name,
            prompt_type=prompt_type,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            is_fallback=is_fallback,
            status=status,
            error_message=error_message,
            request_summary=request_summary,
            response_summary=(response_summary or "")[:2000] if response_summary else None,
        )
        self.db.add(entry)
        self.db.flush()
        return entry
