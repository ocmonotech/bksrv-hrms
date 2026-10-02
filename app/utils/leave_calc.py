from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Optional


def count_working_days(start: date, end: date, exclude_weekends: bool = True) -> Decimal:
    if end < start:
        return Decimal("0")
    days = 0
    current = start
    while current <= end:
        if not exclude_weekends or current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return Decimal(str(days))


def apply_sandwich_rule(start: date, end: date, holiday_dates: Optional[Iterable[date]] = None) -> Decimal:
    """
    Count weekend/holiday days sandwiched between leave start and end as leave days.
    Example: Fri leave + Mon leave with Sat-Sun between → sandwich adds 2 days.
    """
    holiday_set = set(holiday_dates or [])
    sandwiched = 0
    current = start + timedelta(days=1)
    while current < end:
        is_weekend = current.weekday() >= 5
        is_holiday = current in holiday_set
        if is_weekend or is_holiday:
            sandwiched += 1
        current += timedelta(days=1)
    return Decimal(str(sandwiched))


def calculate_leave_days(
    start: date,
    end: date,
    *,
    is_half_day: bool = False,
    sandwich_enabled: bool = False,
    holiday_dates: Optional[Iterable[date]] = None,
) -> tuple[Decimal, Decimal, Decimal]:
    if is_half_day:
        return Decimal("0.5"), Decimal("0"), Decimal("0")

    base = count_working_days(start, end)
    sandwich = apply_sandwich_rule(start, end, holiday_dates) if sandwich_enabled else Decimal("0")
    total = base + sandwich
    return total, sandwich, Decimal("0")
