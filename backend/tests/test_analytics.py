from datetime import date, datetime, timedelta

import pytest

from app.analytics.forecast import forecast_cashflow, upcoming_charges
from app.analytics.monthly_close import (
    classify_spend,
    close_month,
    detect_income_sources,
    month_bounds,
    previous_month,
    spendable,
)
from app.analytics.robust import mad, robust_z
from app.domain.models import Budget, RecurringSeries, Transaction


def _txn(
    amount: float,
    txn_type: str,
    when: datetime,
    category: str = "Other",
    merchant: str | None = None,
    is_transfer: bool = False,
    is_recurring: bool = False,
) -> Transaction:
    return Transaction(
        id=abs(hash((amount, when, category, merchant))) % 10**8,
        user_id=1,
        account_id=1,
        txn_id=f"t-{when.isoformat()}-{amount}",
        txn_hash="h",
        amount=amount,
        txn_type=txn_type,
        narration=merchant or category,
        raw_narration=merchant or category,
        category=category,
        merchant_name=merchant,
        transaction_timestamp=when,
        is_transfer=is_transfer,
        is_recurring=is_recurring,
    )


def _series(merchant: str, amount: float, cadence: str = "monthly", direction: str = "DEBIT"):
    return RecurringSeries(
        user_id=1,
        merchant_name=merchant,
        category="Subscriptions",
        cadence=cadence,
        interval_days=30.4,
        expected_amount=amount,
        occurrences=6,
        confidence=0.9,
        direction=direction,
        first_seen=date(2026, 1, 1),
        last_seen=date(2026, 3, 1),
        next_due=date.today() + timedelta(days=5),
        is_active=True,
    )


# --- helpers -------------------------------------------------------------


def test_month_bounds_handles_december_rollover():
    start, end = month_bounds("2026-12")
    assert start == datetime(2026, 12, 1)
    assert end == datetime(2027, 1, 1)


def test_previous_month_handles_january():
    assert previous_month("2026-01") == "2025-12"


# --- transfers excluded from spend --------------------------------------


def test_self_transfers_do_not_count_as_spending():
    """The single biggest source of wrong numbers in a multi-account PFM."""
    when = datetime(2026, 3, 5)
    transactions = [
        _txn(50000.0, "CREDIT", when, "Salary & Income", "Acme"),
        _txn(2000.0, "DEBIT", when, "Food & Dining", "Swiggy"),
        _txn(25000.0, "DEBIT", when, "Internal Transfer", is_transfer=True),
        _txn(25000.0, "CREDIT", when, "Internal Transfer", is_transfer=True),
    ]
    close = close_month("2026-03", transactions)

    assert close.expense == 2000.0
    assert close.income == 50000.0
    assert close.transfers_excluded == 25000.0
    assert close.net == 48000.0


def test_investments_are_not_counted_as_expense():
    when = datetime(2026, 3, 5)
    transactions = [
        _txn(100000.0, "CREDIT", when, "Salary & Income", "Acme"),
        _txn(10000.0, "DEBIT", when, "Investments", "Zerodha"),
        _txn(3000.0, "DEBIT", when, "Food & Dining", "Swiggy"),
    ]
    close = close_month("2026-03", transactions)

    assert close.expense == 3000.0
    assert close.investments == 10000.0


def test_spendable_predicate():
    when = datetime(2026, 3, 1)
    assert spendable(_txn(100, "DEBIT", when, "Food & Dining"))
    assert not spendable(_txn(100, "CREDIT", when, "Food & Dining"))
    assert not spendable(_txn(100, "DEBIT", when, "Food & Dining", is_transfer=True))
    assert not spendable(_txn(100, "DEBIT", when, "Investments"))


# --- savings rate and spend mix -----------------------------------------


def test_savings_rate():
    when = datetime(2026, 3, 5)
    transactions = [
        _txn(100000.0, "CREDIT", when, "Salary & Income", "Acme"),
        _txn(40000.0, "DEBIT", when, "Rent & Housing", "Landlord"),
    ]
    close = close_month("2026-03", transactions)
    assert close.savings_rate == 60.0


def test_zero_income_does_not_divide_by_zero():
    close = close_month("2026-03", [_txn(500.0, "DEBIT", datetime(2026, 3, 1), "Food & Dining")])
    assert close.savings_rate == 0.0


def test_spend_is_split_into_fixed_variable_and_discretionary():
    when = datetime(2026, 3, 5)
    transactions = [
        _txn(30000.0, "DEBIT", when, "Rent & Housing", "Landlord"),
        _txn(8000.0, "DEBIT", when, "Groceries", "DMart"),
        _txn(2500.0, "DEBIT", when, "Entertainment", "BookMyShow"),
    ]
    close = close_month("2026-03", transactions)

    assert close.fixed == 30000.0
    assert close.variable == 8000.0
    assert close.discretionary == 2500.0


def test_a_recurring_charge_counts_as_fixed():
    txn = _txn(649.0, "DEBIT", datetime(2026, 3, 1), "Entertainment", "Netflix", is_recurring=True)
    assert classify_spend(txn, set()) == "fixed"
    assert classify_spend(_txn(649.0, "DEBIT", datetime(2026, 3, 1), "Entertainment", "Netflix"), {"Netflix"}) == "fixed"


# --- month-over-month ----------------------------------------------------


def test_category_deltas_compare_against_the_previous_month():
    transactions = [
        _txn(5000.0, "DEBIT", datetime(2026, 2, 10), "Food & Dining", "Swiggy"),
        _txn(9000.0, "DEBIT", datetime(2026, 3, 10), "Food & Dining", "Swiggy"),
    ]
    close = close_month("2026-03", transactions)
    food = next(c for c in close.categories if c["category"] == "Food & Dining")

    assert food["amount"] == 9000.0
    assert food["previous"] == 5000.0
    assert food["delta"] == 4000.0
    assert food["delta_pct"] == 80.0
    assert food["significant"] is True


def test_small_movements_are_not_flagged_significant():
    transactions = [
        _txn(1000.0, "DEBIT", datetime(2026, 2, 10), "Food & Dining", "Swiggy"),
        _txn(1100.0, "DEBIT", datetime(2026, 3, 10), "Food & Dining", "Swiggy"),
    ]
    close = close_month("2026-03", transactions)
    food = next(c for c in close.categories if c["category"] == "Food & Dining")
    assert food["significant"] is False


# --- robust anomalies ----------------------------------------------------


def test_mad_is_not_inflated_by_an_outlier():
    values = [100.0, 102.0, 98.0, 101.0, 99.0, 5000.0]
    assert mad(values) < 5.0


def test_robust_z_flags_a_genuine_outlier():
    baseline = [100.0, 102.0, 98.0, 101.0, 99.0]
    assert robust_z(5000.0, baseline) > 3.5
    assert robust_z(103.0, baseline) < 3.5


def test_robust_z_needs_a_real_sample():
    assert robust_z(1000.0, [100.0, 200.0]) == 0.0


def test_rent_is_not_flagged_as_an_anomaly_every_month():
    """The previous global 2-sigma rule flagged rent and EMI by construction."""
    transactions = []
    for month in range(1, 7):
        transactions.append(
            _txn(45000.0, "DEBIT", datetime(2026, month, 1), "Rent & Housing", "Landlord")
        )
        for day in (5, 10, 15, 20):
            transactions.append(
                _txn(400.0, "DEBIT", datetime(2026, month, day), "Food & Dining", "Swiggy")
            )

    close = close_month("2026-06", transactions)
    assert all(a["merchant"] != "Landlord" for a in close.anomalies)


def test_an_unusually_large_charge_at_a_familiar_merchant_is_flagged():
    transactions = [
        _txn(400.0, "DEBIT", datetime(2026, m, d), "Food & Dining", "Swiggy")
        for m in range(1, 6)
        for d in (5, 12, 19, 26)
    ]
    transactions.append(_txn(18000.0, "DEBIT", datetime(2026, 6, 5), "Food & Dining", "Swiggy"))

    close = close_month("2026-06", transactions)
    assert any(a["merchant"] == "Swiggy" and a["amount"] == 18000.0 for a in close.anomalies)


# --- income detection ----------------------------------------------------


def test_regular_monthly_credits_are_identified_as_salary():
    transactions = [
        _txn(125000.0, "CREDIT", datetime(2026, m, 1), "Salary & Income", "Acme Private Limited")
        for m in range(1, 7)
    ]
    sources = detect_income_sources(transactions)
    assert sources[0].is_salary is True
    assert sources[0].stability > 0.9


def test_irregular_credits_are_not_salary():
    transactions = [
        _txn(amount, "CREDIT", datetime(2026, 1, day), "Other", "Freelance")
        for amount, day in [(15000.0, 3), (48000.0, 11), (7000.0, 25)]
    ]
    sources = detect_income_sources(transactions)
    assert all(not s.is_salary for s in sources)


def test_transfers_in_are_not_income():
    transactions = [
        _txn(25000.0, "CREDIT", datetime(2026, m, 1), "Internal Transfer", "Self", is_transfer=True)
        for m in range(1, 7)
    ]
    assert detect_income_sources(transactions) == []


# --- budgets -------------------------------------------------------------


def test_budget_tracks_spend_and_projects_overrun():
    transactions = [_txn(9000.0, "DEBIT", datetime(2026, 3, 10), "Food & Dining", "Swiggy")]
    budget = Budget(user_id=1, category="Food & Dining", monthly_limit=8000.0, alert_threshold=0.8)

    close = close_month("2026-03", transactions, budgets=[budget])
    row = close.budgets[0]

    assert row["spent"] == 9000.0
    assert row["remaining"] == -1000.0
    assert row["on_track"] is False
    assert row["alert"] is True


def test_budget_under_limit_is_on_track():
    transactions = [_txn(2000.0, "DEBIT", datetime(2026, 3, 10), "Food & Dining", "Swiggy")]
    budget = Budget(user_id=1, category="Food & Dining", monthly_limit=8000.0, alert_threshold=0.8)
    row = close_month("2026-03", transactions, budgets=[budget]).budgets[0]

    assert row["on_track"] is True
    assert row["alert"] is False


# --- forecast ------------------------------------------------------------


def test_forecast_is_seeded_from_recurring_series():
    transactions = [
        _txn(100000.0, "CREDIT", datetime(2026, m, 1), "Salary & Income", "Acme")
        for m in range(1, 7)
    ] + [
        _txn(40000.0, "DEBIT", datetime(2026, m, 5), "Rent & Housing", "Landlord")
        for m in range(1, 7)
    ]
    recurring = [_series("Landlord", 40000.0)]

    forecast = forecast_cashflow(transactions, recurring, total_balance=200000.0)

    assert forecast["basis"] == "recurring_series"
    assert forecast["monthly_committed"] == 40000.0
    assert len(forecast["points"]) == 6
    assert forecast["net_monthly"] > 0


def test_runway_is_reported_when_burning_cash():
    transactions = [
        _txn(60000.0, "DEBIT", datetime(2026, m, 5), "Rent & Housing", "Landlord")
        for m in range(1, 7)
    ]
    forecast = forecast_cashflow(transactions, [], total_balance=180000.0)
    assert forecast["runway_months"] == pytest.approx(3.0, abs=0.1)


def test_no_runway_when_income_exceeds_spend():
    transactions = [
        _txn(100000.0, "CREDIT", datetime(2026, m, 1), "Salary & Income", "Acme")
        for m in range(1, 7)
    ] + [
        _txn(20000.0, "DEBIT", datetime(2026, m, 5), "Food & Dining", "Swiggy")
        for m in range(1, 7)
    ]
    assert forecast_cashflow(transactions, [], total_balance=100000.0)["runway_months"] is None


def test_forecast_survives_an_empty_history():
    forecast = forecast_cashflow([], [], total_balance=0.0)
    assert len(forecast["points"]) == 6


def test_upcoming_charges_lists_only_the_near_horizon():
    soon = _series("Netflix", 649.0)
    far = _series("Domain", 1499.0)
    far.next_due = date.today() + timedelta(days=200)

    upcoming = upcoming_charges([soon, far], days=30)
    assert [u["merchant"] for u in upcoming] == ["Netflix"]
