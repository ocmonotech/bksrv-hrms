from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional, Union


MONEY = Decimal("0.01")


def money(value: Union[Decimal, float, int, str]) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def prorate_monthly(amount: Decimal, payable_days: Decimal, working_days: int) -> Decimal:
    if working_days <= 0:
        return Decimal("0")
    return money(amount * payable_days / Decimal(str(working_days)))


def calculate_lop_deduction(monthly_amount: Decimal, lop_days: Decimal, working_days: int) -> Decimal:
    if working_days <= 0 or lop_days <= 0:
        return Decimal("0")
    per_day = monthly_amount / Decimal(str(working_days))
    return money(per_day * lop_days)


def calculate_overtime_pay(
    basic_monthly: Decimal,
    overtime_minutes: int,
    *,
    working_days: int = 26,
    hours_per_day: int = 8,
    multiplier: Decimal = Decimal("2"),
) -> Decimal:
    if overtime_minutes <= 0 or working_days <= 0:
        return Decimal("0")
    hourly = basic_monthly / (Decimal(str(working_days)) * Decimal(str(hours_per_day)))
    hours = Decimal(str(overtime_minutes)) / Decimal("60")
    return money(hourly * hours * multiplier)


def calculate_pf(
    pf_wage: Decimal,
    *,
    employee_rate: Decimal = Decimal("0.12"),
    employer_rate: Decimal = Decimal("0.12"),
    wage_ceiling: Decimal = Decimal("15000"),
) -> tuple[Decimal, Decimal]:
    ceiling = wage_ceiling if wage_ceiling is not None else Decimal("15000")
    emp_rate = employee_rate if employee_rate is not None else Decimal("0.12")
    er_rate = employer_rate if employer_rate is not None else Decimal("0.12")
    base = min(pf_wage, ceiling)
    return money(base * emp_rate), money(base * er_rate)


def calculate_esi(
    gross: Decimal,
    *,
    employee_rate: Decimal = Decimal("0.0075"),
    employer_rate: Decimal = Decimal("0.0325"),
    threshold: Decimal = Decimal("21000"),
) -> tuple[Decimal, Decimal]:
    limit = threshold if threshold is not None else Decimal("21000")
    if gross > limit:
        return Decimal("0"), Decimal("0")
    emp_rate = employee_rate if employee_rate is not None else Decimal("0.0075")
    er_rate = employer_rate if employer_rate is not None else Decimal("0.0325")
    return money(gross * emp_rate), money(gross * er_rate)


def calculate_professional_tax(gross: Decimal, pt_slabs: list[dict[str, Any]]) -> Decimal:
    """Slab format: [{"min": 0, "max": 7500, "amount": 0}, {"min": 7501, "max": 10000, "amount": 175}, ...]"""
    for slab in sorted(pt_slabs, key=lambda s: s.get("min", 0)):
        min_val = Decimal(str(slab.get("min", 0)))
        max_val = slab.get("max")
        amount = Decimal(str(slab.get("amount", 0)))
        if max_val is None:
            if gross >= min_val:
                return money(amount)
        else:
            max_dec = Decimal(str(max_val))
            if min_val <= gross <= max_dec:
                return money(amount)
    return Decimal("0")


def calculate_tds_placeholder(taxable_gross: Decimal, tds_rate: Decimal = Decimal("0")) -> Decimal:
    if tds_rate <= 0:
        return Decimal("0")
    return money(taxable_gross * tds_rate)


def calculate_tds_india(annual_taxable: Decimal, regime: str = "old") -> Decimal:
    """Compute annual income tax for Indian old regime (basic slabs + 4% cess)."""
    if annual_taxable <= 0:
        return Decimal("0")

    taxable = money(annual_taxable)
    if regime != "old":
        return Decimal("0")

    tax = Decimal("0")
    if taxable > Decimal("1000000"):
        tax += (taxable - Decimal("1000000")) * Decimal("0.30")
        taxable = Decimal("1000000")
    if taxable > Decimal("500000"):
        tax += (taxable - Decimal("500000")) * Decimal("0.20")
        taxable = Decimal("500000")
    if taxable > Decimal("250000"):
        tax += (taxable - Decimal("250000")) * Decimal("0.05")

    tax = money(tax)
    cess = money(tax * Decimal("0.04"))
    return money(tax + cess)


def default_pt_slabs() -> list[dict[str, Any]]:
    return [
        {"min": 0, "max": 7500, "amount": 0},
        {"min": 7501, "max": 10000, "amount": 175},
        {"min": 10001, "max": None, "amount": 200},
    ]


def parse_json_list(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def parse_json_dict(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}
