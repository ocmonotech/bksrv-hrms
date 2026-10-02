from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardStatsResponse(BaseModel):
    total_employees: int
    attendance_today: dict[str, Any]
    pending_leave_approvals: int
    payroll_run_status: Optional[dict[str, Any]] = None
