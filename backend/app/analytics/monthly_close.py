from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any

from app.analytics.robust import ROBUST_Z_THRESHOLD, coefficient_of_variation, robust_z
from app.domain.models import Budget, RecurringSeries, Transaction

# Categories whose amount is committed before the month starts.
FIXED_CATEGORIES = {
    "Rent & Housing", "Insurance", "Loan & EMI", "Bills & Utilities", "Education",
}
# Categories that are necessary but vary with usage.
VARIABLE_CATEGORIES = {
    "Groceries", "Transport", "Healthcare", "Bills & Utilities",
}
NON_SPEND_CATEGORIES = {"Internal Transfer", "Investments", "Salary & Income"}

SALARY_CV_THRESHOLD = 0.12
SALARY_MIN_OCCURRENCES = 2


def month_key(value: datetime | date) -> str:
    return value.strftime("%Y-%m")


def month_bounds(key: str) -> tuple[datetime, datetime]:
    year, month = (int(p) for p in key.split("-"))
    start = datetime(year, month, 1)
    end = datetime(year + (month == 12), (month % 12) + 1, 1)
    return start, end


def previous_month(key: str) -> str:
    start, _ = month_bounds(key)
    return month_key(start - timedelta(days=1))


def spendable(txn: Transaction) -> bool:
    """A debit that represents real consumption.

    Self-transfers and investments move money rather than spend it; counting them
    as expenses is what makes naive multi-account dashboards wrong.
    """
    return (
        txn.txn_type.upper() == "DEBIT"
        and not txn.is_transfer
        and txn.category not in NON_SPEND_CATEGORIES
    )


def real_income(txn: Transaction) -> bool:
    return txn.txn_type.upper() == "CREDIT" and not txn.is_transfer


@dataclass(slots=True)
class IncomeSource:
    name: str
    category: str
    monthly_amount: float
    occurrences: int
    is_salary: bool
    stability: float
    last_received: date


def detect_income_sources(transactions: list[Transaction]) -> list[IncomeSource]:
    """Group credits by counterparty and mark the low-variance recurring ones as salary."""
    grouped: dict[str, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        if real_income(txn):
            grouped[txn.merchant_name or txn.narration[:40] or "Unknown"].append(txn)

    sources: list[IncomeSource] = []
    for name, txns in grouped.items():
        amounts = [abs(float(t.amount)) for t in txns]
        txns.sort(key=lambda t: t.transaction_timestamp)
        dates = [t.transaction_timestamp.date() for t in txns]
        cv = coefficient_of_variation(amounts)

        intervals = [(b - a).days for a, b in zip(dates, dates[1:], strict=False)]
        monthly_cadence = bool(intervals) and 25 <= median(intervals) <= 35
        is_salary = (
            len(txns) >= SALARY_MIN_OCCURRENCES
            and cv <= SALARY_CV_THRESHOLD
            and monthly_cadence
            and median(amounts) >= 10000
        )

        months = len({month_key(d) for d in dates}) or 1
        sources.append(
            IncomeSource(
                name=name,
                category=txns[-1].category,
                monthly_amount=round(sum(amounts) / months, 2),
                occurrences=len(txns),
                is_salary=is_salary,
                stability=round(max(0.0, 1 - cv), 2),
                last_received=dates[-1],
            )
        )
    return sorted(sources, key=lambda s: s.monthly_amount, reverse=True)


def classify_spend(txn: Transaction, recurring_names: set[str]) -> str:
    """fixed | variable | discretionary."""
    if txn.category in FIXED_CATEGORIES:
        return "fixed"
    if txn.is_recurring or (txn.merchant_name or "") in recurring_names:
        return "fixed"
    if txn.category in VARIABLE_CATEGORIES:
        return "variable"
    return "discretionary"


@dataclass(slots=True)
class MonthlyClose:
    month: str
    income: float
    expense: float
    net: float
    savings_rate: float
    fixed: float
    variable: float
    discretionary: float
    transfers_excluded: float
    investments: float
    transaction_count: int
    income_sources: list[dict[str, Any]] = field(default_factory=list)
    categories: list[dict[str, Any]] = field(default_factory=list)
    top_merchants: list[dict[str, Any]] = field(default_factory=list)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    budgets: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "month": self.month,
            "income": self.income,
            "expense": self.expense,
            "net": self.net,
            "savings_rate": self.savings_rate,
            "spend_mix": {
                "fixed": self.fixed,
                "variable": self.variable,
                "discretionary": self.discretionary,
            },
            "transfers_excluded": self.transfers_excluded,
            "investments": self.investments,
            "transaction_count": self.transaction_count,
            "income_sources": self.income_sources,
            "categories": self.categories,
            "top_merchants": self.top_merchants,
            "anomalies": self.anomalies,
            "budgets": self.budgets,
        }


def _category_deltas(
    current: dict[str, float], previous: dict[str, float]
) -> list[dict[str, Any]]:
    """MoM movement per category, filtered so noise does not crowd out signal."""
    rows: list[dict[str, Any]] = []
    total = sum(current.values()) or 1.0
    for category in set(current) | set(previous):
        now = round(current.get(category, 0.0), 2)
        before = round(previous.get(category, 0.0), 2)
        delta = round(now - before, 2)
        pct = round(delta / before * 100, 1) if before else None
        # Significant means both a meaningful rupee move and a meaningful share.
        significant = abs(delta) >= 1000 and (pct is None or abs(pct) >= 15)
        rows.append(
            {
                "category": category,
                "amount": now,
                "previous": before,
                "delta": delta,
                "delta_pct": pct,
                "share": round(now / total * 100, 1),
                "significant": significant,
            }
        )
    return sorted(rows, key=lambda r: r["amount"], reverse=True)


def _detect_anomalies(
    month_txns: list[Transaction], history: list[Transaction]
) -> list[dict[str, Any]]:
    """Per-merchant then per-category median + MAD.

    The previous global 2σ rule flagged rent and EMI every single month because
    they are large by nature, not unusual.
    """
    by_merchant: dict[str, list[float]] = defaultdict(list)
    by_category: dict[str, list[float]] = defaultdict(list)
    for txn in history:
        if not spendable(txn):
            continue
        amount = abs(float(txn.amount))
        if txn.merchant_name:
            by_merchant[txn.merchant_name].append(amount)
        by_category[txn.category].append(amount)

    anomalies: list[dict[str, Any]] = []
    for txn in month_txns:
        if not spendable(txn):
            continue
        amount = abs(float(txn.amount))
        baseline = by_merchant.get(txn.merchant_name or "", [])
        scope = "merchant"
        if len(baseline) < 4:
            baseline = by_category.get(txn.category, [])
            scope = "category"
        if len(baseline) < 4:
            continue

        score = robust_z(amount, baseline)
        if score < ROBUST_Z_THRESHOLD:
            continue
        typical = median(baseline)
        anomalies.append(
            {
                "txn_id": txn.txn_id,
                "date": txn.transaction_timestamp.strftime("%Y-%m-%d"),
                "merchant": txn.merchant_name or "Unknown",
                "category": txn.category,
                "amount": round(amount, 2),
                "typical_amount": round(typical, 2),
                "robust_z": round(score, 2) if score != float("inf") else None,
                "reason": (
                    f"₹{amount:,.0f} is far above the usual ₹{typical:,.0f} "
                    f"for this {scope}"
                ),
            }
        )
    return sorted(anomalies, key=lambda a: a["amount"], reverse=True)[:15]


def _budget_status(
    budgets: list[Budget], spend_by_category: dict[str, float], month: str
) -> list[dict[str, Any]]:
    start, end = month_bounds(month)
    days_in_month = (end - start).days
    today = datetime.utcnow()
    elapsed = days_in_month if today >= end else max(1, (today - start).days + 1)
    pace = elapsed / days_in_month

    rows = []
    for budget in budgets:
        spent = round(spend_by_category.get(budget.category, 0.0), 2)
        projected = round(spent / pace, 2) if pace > 0 else spent
        rows.append(
            {
                "category": budget.category,
                "limit": budget.monthly_limit,
                "spent": spent,
                "remaining": round(budget.monthly_limit - spent, 2),
                "used_pct": round(spent / budget.monthly_limit * 100, 1) if budget.monthly_limit else 0,
                "projected_spend": projected,
                "projected_overrun": round(max(0.0, projected - budget.monthly_limit), 2),
                "on_track": projected <= budget.monthly_limit,
                "alert": spent >= budget.monthly_limit * budget.alert_threshold,
            }
        )
    return sorted(rows, key=lambda r: r["used_pct"], reverse=True)


def close_month(
    month: str,
    transactions: list[Transaction],
    budgets: list[Budget] | None = None,
    recurring: list[RecurringSeries] | None = None,
) -> MonthlyClose:
    """Full close for one month, using all transactions as the comparison baseline."""
    start, end = month_bounds(month)
    month_txns = [t for t in transactions if start <= t.transaction_timestamp < end]
    prev_start, prev_end = month_bounds(previous_month(month))
    prev_txns = [t for t in transactions if prev_start <= t.transaction_timestamp < prev_end]

    recurring_names = {r.merchant_name for r in (recurring or [])}

    income = sum(abs(float(t.amount)) for t in month_txns if real_income(t))
    spend_by_category: dict[str, float] = defaultdict(float)
    merchant_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"amount": 0.0, "count": 0, "category": "Other"}
    )
    mix = {"fixed": 0.0, "variable": 0.0, "discretionary": 0.0}

    for txn in month_txns:
        if not spendable(txn):
            continue
        amount = abs(float(txn.amount))
        spend_by_category[txn.category] += amount
        mix[classify_spend(txn, recurring_names)] += amount
        name = txn.merchant_name or "Unknown"
        merchant_totals[name]["amount"] += amount
        merchant_totals[name]["count"] += 1
        merchant_totals[name]["category"] = txn.category

    expense = sum(spend_by_category.values())
    transfers = sum(abs(float(t.amount)) for t in month_txns if t.is_transfer and t.txn_type == "DEBIT")
    investments = sum(
        abs(float(t.amount))
        for t in month_txns
        if t.txn_type.upper() == "DEBIT" and t.category == "Investments" and not t.is_transfer
    )

    prev_by_category: dict[str, float] = defaultdict(float)
    for txn in prev_txns:
        if spendable(txn):
            prev_by_category[txn.category] += abs(float(txn.amount))

    net = income - expense
    return MonthlyClose(
        month=month,
        income=round(income, 2),
        expense=round(expense, 2),
        net=round(net, 2),
        savings_rate=round(net / income * 100, 1) if income > 0 else 0.0,
        fixed=round(mix["fixed"], 2),
        variable=round(mix["variable"], 2),
        discretionary=round(mix["discretionary"], 2),
        transfers_excluded=round(transfers, 2),
        investments=round(investments, 2),
        transaction_count=len(month_txns),
        income_sources=[
            {
                "name": s.name,
                "category": s.category,
                "monthly_amount": s.monthly_amount,
                "is_salary": s.is_salary,
                "stability": s.stability,
                "last_received": s.last_received.isoformat(),
            }
            for s in detect_income_sources(month_txns)
        ],
        categories=_category_deltas(dict(spend_by_category), dict(prev_by_category)),
        top_merchants=[
            {"merchant": name, "amount": round(v["amount"], 2), "count": v["count"], "category": v["category"]}
            for name, v in sorted(merchant_totals.items(), key=lambda kv: kv[1]["amount"], reverse=True)[:15]
        ],
        anomalies=_detect_anomalies(month_txns, transactions),
        budgets=_budget_status(budgets or [], dict(spend_by_category), month),
    )
