from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any

from app.analytics.monthly_close import month_key, real_income, spendable
from app.domain.models import RecurringSeries, Transaction

CADENCE_PER_MONTH = {
    "weekly": 30.4 / 7,
    "fortnightly": 30.4 / 14,
    "monthly": 1.0,
    "quarterly": 1 / 3,
    "annual": 1 / 12,
}
MIN_SERIES_CONFIDENCE = 0.5


def _committed_monthly(recurring: list[RecurringSeries], direction: str) -> float:
    """Spend or income already locked in by known recurring series."""
    total = 0.0
    for series in recurring:
        if series.direction.upper() != direction or not series.is_active:
            continue
        if series.confidence < MIN_SERIES_CONFIDENCE:
            continue
        total += series.expected_amount * CADENCE_PER_MONTH.get(series.cadence, 1.0)
    return total


def _monthly_totals(transactions: list[Transaction]) -> tuple[dict[str, float], dict[str, float]]:
    income: dict[str, float] = defaultdict(float)
    expense: dict[str, float] = defaultdict(float)
    for txn in transactions:
        key = month_key(txn.transaction_timestamp)
        if real_income(txn):
            income[key] += abs(float(txn.amount))
        elif spendable(txn):
            expense[key] += abs(float(txn.amount))
    return dict(income), dict(expense)


def forecast_cashflow(
    transactions: list[Transaction],
    recurring: list[RecurringSeries],
    total_balance: float,
    horizon_months: int = 6,
) -> dict[str, Any]:
    """Project forward from committed recurring flows plus variable spend.

    The previous version extrapolated a flat three-month average, which ignored both
    known subscriptions and the fact that one unusual month skews a mean.
    """
    income_by_month, expense_by_month = _monthly_totals(transactions)
    # Exclude the current partial month so it does not drag the baseline down.
    current = month_key(datetime.utcnow())
    complete_expense = [v for k, v in sorted(expense_by_month.items()) if k != current][-6:]
    complete_income = [v for k, v in sorted(income_by_month.items()) if k != current][-6:]

    committed_spend = _committed_monthly(recurring, "DEBIT")
    committed_income = _committed_monthly(recurring, "CREDIT")

    # Median resists the one-off big month that a mean would bake into every forecast.
    baseline_expense = median(complete_expense) if complete_expense else committed_spend
    baseline_income = median(complete_income) if complete_income else committed_income
    variable_spend = max(0.0, baseline_expense - committed_spend)
    projected_expense = committed_spend + variable_spend
    projected_income = max(baseline_income, committed_income)

    net_burn = projected_expense - projected_income
    runway_months = round(total_balance / net_burn, 1) if net_burn > 0 else None

    points: list[dict[str, Any]] = []
    balance = total_balance
    cursor = datetime.utcnow().replace(day=1)
    for _ in range(horizon_months):
        cursor = (cursor + timedelta(days=32)).replace(day=1)
        balance += projected_income - projected_expense
        points.append(
            {
                "month": cursor.strftime("%Y-%m"),
                "projected_income": round(projected_income, 2),
                "projected_expense": round(projected_expense, 2),
                "committed_expense": round(committed_spend, 2),
                "variable_expense": round(variable_spend, 2),
                "projected_balance": round(balance, 2),
            }
        )

    return {
        "points": points,
        "runway_months": runway_months,
        "monthly_committed": round(committed_spend, 2),
        "monthly_variable": round(variable_spend, 2),
        "monthly_income": round(projected_income, 2),
        "net_monthly": round(projected_income - projected_expense, 2),
        "basis": "recurring_series" if recurring else "historical_median",
    }


def upcoming_charges(recurring: list[RecurringSeries], days: int = 30) -> list[dict[str, Any]]:
    """Subscriptions and EMIs due in the near term, so the runway is not a surprise."""
    horizon = date.today() + timedelta(days=days)
    rows = [
        {
            "merchant": s.merchant_name,
            "category": s.category,
            "amount": s.expected_amount,
            "cadence": s.cadence,
            "next_due": s.next_due.isoformat() if s.next_due else None,
            "confidence": s.confidence,
            "direction": s.direction,
        }
        for s in recurring
        if s.is_active and s.next_due and date.today() <= s.next_due <= horizon
    ]
    return sorted(rows, key=lambda r: r["next_due"] or "")
