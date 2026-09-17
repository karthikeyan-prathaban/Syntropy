from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import close_month, forecast_cashflow, month_key, upcoming_charges
from app.analytics.monthly_close import real_income, spendable
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import (
    BalanceSnapshot,
    BankAccount,
    Budget,
    RecurringSeries,
    Transaction,
    User,
)
from app.schemas.analytics import BudgetCreate, BudgetResponse
from app.services.analytics_engine import (
    cashflow_series,
    category_slices,
    merchant_leaderboard,
    spending_calendar,
    txn_dicts,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _transactions(db: AsyncSession, user_id: int) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_timestamp)
    )
    return list(result.scalars())


async def _recurring(db: AsyncSession, user_id: int) -> list[RecurringSeries]:
    result = await db.execute(
        select(RecurringSeries).where(
            RecurringSeries.user_id == user_id, RecurringSeries.is_active.is_(True)
        )
    )
    return list(result.scalars())


async def _budgets(db: AsyncSession, user_id: int) -> list[Budget]:
    result = await db.execute(
        select(Budget).where(Budget.user_id == user_id, Budget.is_active.is_(True))
    )
    return list(result.scalars())


async def _balance(db: AsyncSession, user_id: int) -> float:
    result = await db.execute(
        select(BankAccount).where(BankAccount.user_id == user_id, BankAccount.is_active.is_(True))
    )
    return sum(a.current_balance for a in result.scalars())


def _validate_month(month: str) -> str:
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Month must be in YYYY-MM format") from exc
    return month


# --- monthly close -------------------------------------------------------


@router.get("/monthly/compare")
async def compare_months(
    months: int = Query(6, ge=2, le=24),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Side-by-side closes for the most recent months that actually have data."""
    transactions = await _transactions(db, user.id)
    if not transactions:
        return {"months": []}

    keys = sorted({month_key(t.transaction_timestamp) for t in transactions})[-months:]
    budgets = await _budgets(db, user.id)
    recurring = await _recurring(db, user.id)
    closes = [close_month(k, transactions, budgets, recurring) for k in keys]
    return {
        "months": [
            {
                "month": c.month,
                "income": c.income,
                "expense": c.expense,
                "net": c.net,
                "savings_rate": c.savings_rate,
                "fixed": c.fixed,
                "variable": c.variable,
                "discretionary": c.discretionary,
            }
            for c in closes
        ]
    }


@router.get("/monthly/{month}")
async def monthly_close(
    month: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_month(month)
    transactions = await _transactions(db, user.id)
    close = close_month(month, transactions, await _budgets(db, user.id), await _recurring(db, user.id))
    return close.as_dict()


@router.get("/income")
async def income_breakdown(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.analytics import detect_income_sources

    transactions = await _transactions(db, user.id)
    sources = detect_income_sources(transactions)
    salary = [s for s in sources if s.is_salary]
    return {
        "sources": [
            {
                "name": s.name,
                "category": s.category,
                "monthly_amount": s.monthly_amount,
                "occurrences": s.occurrences,
                "is_salary": s.is_salary,
                "stability": s.stability,
                "last_received": s.last_received.isoformat(),
            }
            for s in sources
        ],
        "primary_salary": salary[0].name if salary else None,
        "monthly_salary": round(sum(s.monthly_amount for s in salary), 2),
        "monthly_other": round(sum(s.monthly_amount for s in sources if not s.is_salary), 2),
    }


@router.get("/subscriptions")
async def subscriptions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    recurring = await _recurring(db, user.id)
    debits = [s for s in recurring if s.direction.upper() == "DEBIT"]
    monthly_cost = sum(
        s.expected_amount * {"weekly": 4.33, "fortnightly": 2.17, "monthly": 1, "quarterly": 1 / 3, "annual": 1 / 12}.get(s.cadence, 1)
        for s in debits
    )
    return {
        "series": [
            {
                "id": s.id,
                "merchant": s.merchant_name,
                "category": s.category,
                "amount": s.expected_amount,
                "cadence": s.cadence,
                "interval_days": s.interval_days,
                "occurrences": s.occurrences,
                "confidence": s.confidence,
                "direction": s.direction,
                "last_seen": s.last_seen.isoformat(),
                "next_due": s.next_due.isoformat() if s.next_due else None,
                "amount_variation": s.amount_variation,
            }
            for s in sorted(debits, key=lambda x: x.expected_amount, reverse=True)
        ],
        "monthly_cost": round(monthly_cost, 2),
        "annual_cost": round(monthly_cost * 12, 2),
        "upcoming": upcoming_charges(recurring),
    }


@router.get("/net-worth")
async def net_worth(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Real trajectory from daily balance snapshots, not a single current figure."""
    accounts = (
        await db.execute(select(BankAccount).where(BankAccount.user_id == user.id))
    ).scalars().all()
    snapshots = (
        await db.execute(
            select(BalanceSnapshot)
            .where(BalanceSnapshot.user_id == user.id)
            .order_by(BalanceSnapshot.snapshot_date)
        )
    ).scalars().all()

    by_date: dict[str, float] = defaultdict(float)
    for snapshot in snapshots:
        by_date[snapshot.snapshot_date.isoformat()] += snapshot.balance

    series = [{"date": d, "balance": round(v, 2)} for d, v in sorted(by_date.items())]
    total = sum(a.current_balance for a in accounts)
    first_balance = next(iter(sorted(by_date.items())), (None, 0.0))[1]
    change = round(total - first_balance, 2) if series else 0.0

    return {
        "total": round(total, 2),
        "change_since_first_snapshot": change,
        "series": series,
        "by_account": [
            {
                "id": a.id,
                "masked_acc_number": a.masked_acc_number,
                "bank_name": a.bank_name,
                "fi_type": a.fi_type,
                "balance": round(a.current_balance, 2),
                "holdings": a.holdings,
            }
            for a in accounts
        ],
    }


# --- budgets -------------------------------------------------------------


@router.get("/budgets", response_model=list[BudgetResponse])
async def list_budgets(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _budgets(db, user.id)


@router.put("/budgets", response_model=BudgetResponse)
async def upsert_budget(
    payload: BudgetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(
            select(Budget).where(Budget.user_id == user.id, Budget.category == payload.category)
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = Budget(user_id=user.id, category=payload.category)
        db.add(existing)
    existing.monthly_limit = payload.monthly_limit
    existing.alert_threshold = payload.alert_threshold
    existing.is_active = True
    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/budgets/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    budget = (
        await db.execute(select(Budget).where(Budget.id == budget_id, Budget.user_id == user.id))
    ).scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.delete(budget)
    await db.commit()


# --- existing chart endpoints -------------------------------------------


@router.get("/cashflow")
async def get_cashflow(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    txns = await _transactions(db, user.id)
    return cashflow_series(txn_dicts([t for t in txns if not t.is_transfer]))


@router.get("/categories")
async def get_categories(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    txns = await _transactions(db, user.id)
    return category_slices(txn_dicts([t for t in txns if spendable(t) or real_income(t)]))


@router.get("/merchants")
async def get_merchants(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    txns = await _transactions(db, user.id)
    return merchant_leaderboard(txn_dicts([t for t in txns if spendable(t)]))


@router.get("/recurring")
async def get_recurring(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Kept for the existing dashboard widget; backed by the real series table now."""
    recurring = await _recurring(db, user.id)
    return [
        {
            "merchant": s.merchant_name,
            "amount": s.expected_amount,
            "frequency": s.cadence,
            "category": s.category,
            "last_date": s.last_seen.isoformat(),
            "next_due": s.next_due.isoformat() if s.next_due else None,
            "confidence": s.confidence,
        }
        for s in sorted(recurring, key=lambda x: x.expected_amount, reverse=True)
        if s.direction.upper() == "DEBIT"
    ][:15]


@router.get("/calendar")
async def get_calendar(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    txns = await _transactions(db, user.id)
    return spending_calendar(txn_dicts([t for t in txns if spendable(t)]))


@router.get("/anomalies")
async def get_anomalies(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    transactions = await _transactions(db, user.id)
    if not transactions:
        return []
    latest = month_key(max(t.transaction_timestamp for t in transactions))
    return close_month(latest, transactions).anomalies


@router.get("/forecast")
async def get_forecast(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    transactions = await _transactions(db, user.id)
    return forecast_cashflow(
        transactions, await _recurring(db, user.id), await _balance(db, user.id)
    )
