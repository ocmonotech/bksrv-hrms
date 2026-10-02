from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Optional

from app.models.shift import Shift


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def combine_date_time(d: date, t: time) -> datetime:
    return datetime.combine(d, t, tzinfo=timezone.utc)


def calculate_work_minutes(first_in: Optional[datetime], last_out: Optional[datetime], break_minutes: int = 0) -> int:
    first_in = ensure_utc(first_in)
    last_out = ensure_utc(last_out)
    if not first_in or not last_out or last_out <= first_in:
        return 0
    delta = last_out - first_in
    minutes = int(delta.total_seconds() // 60) - break_minutes
    return max(minutes, 0)


def calculate_late_minutes(
    first_in: Optional[datetime],
    shift: Optional[Shift],
    attendance_date: date,
    grace_minutes: int = 10,
) -> int:
    first_in = ensure_utc(first_in)
    if not first_in or not shift:
        return 0
    expected = combine_date_time(attendance_date, shift.start_time)
    if shift.is_night_shift and first_in.time() < shift.end_time:
        expected -= timedelta(days=1)
    diff = int((first_in - expected).total_seconds() // 60)
    return max(diff - grace_minutes, 0)


def calculate_early_leave_minutes(
    last_out: Optional[datetime],
    shift: Optional[Shift],
    attendance_date: date,
    threshold: int = 15,
) -> int:
    last_out = ensure_utc(last_out)
    if not last_out or not shift:
        return 0
    expected = combine_date_time(attendance_date, shift.end_time)
    if shift.is_night_shift and shift.end_time <= shift.start_time:
        expected += timedelta(days=1)
    diff = int((expected - last_out).total_seconds() // 60)
    return max(diff - threshold, 0)


def determine_day_status(
    work_minutes: int,
    late_minutes: int,
    *,
    full_day_minutes: int = 480,
    half_day_minutes: int = 240,
    on_leave: bool = False,
) -> tuple[str, Decimal, bool]:
    if on_leave:
        return "on_leave", Decimal("0"), False
    if work_minutes <= 0:
        return "absent", Decimal("1"), True
    if work_minutes < half_day_minutes:
        return "half_day", Decimal("0.5"), True
    if work_minutes < full_day_minutes:
        status = "late" if late_minutes > 0 else "half_day"
        lop = Decimal("0.5") if status == "half_day" else Decimal("0")
        return status, lop, lop > 0
    status = "late" if late_minutes > 0 else "present"
    return status, Decimal("0"), False


def payable_days_from_status(status: str, lop_days: Decimal) -> Decimal:
    mapping = {
        "present": Decimal("1"),
        "late": Decimal("1"),
        "half_day": Decimal("0.5"),
        "on_leave": Decimal("1"),
        "holiday": Decimal("1"),
        "week_off": Decimal("1"),
        "absent": Decimal("0"),
    }
    base = mapping.get(status, Decimal("0"))
    return max(base - lop_days, Decimal("0"))
