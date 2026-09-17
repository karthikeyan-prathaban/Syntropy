from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import BankAccount, Transaction, User
from app.services.analytics_engine import (
    cashflow_series,
    category_slices,
    detect_anomalies,
    forecast_runway,
    merchant_leaderboard,
    recurring_subscriptions,
    spending_calendar,
    txn_dicts,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _get_txns(db: AsyncSession, user_id: int) -> list[dict]:
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.transaction_timestamp)
    )
    return txn_dicts(result.scalars().all())


async def _balance(db: AsyncSession, user_id: int) -> float:
    result = await db.execute(select(BankAccount).where(BankAccount.user_id == user_id))
    return sum(a.current_balance for a in result.scalars().all())


@router.get("/cashflow")
async def get_cashflow(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return cashflow_series(await _get_txns(db, user.id))


@router.get("/categories")
async def get_categories(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return category_slices(await _get_txns(db, user.id))


@router.get("/merchants")
async def get_merchants(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return merchant_leaderboard(await _get_txns(db, user.id))


@router.get("/recurring")
async def get_recurring(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return recurring_subscriptions(await _get_txns(db, user.id))


@router.get("/calendar")
async def get_calendar(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return spending_calendar(await _get_txns(db, user.id))


@router.get("/anomalies")
async def get_anomalies(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return detect_anomalies(await _get_txns(db, user.id))


@router.get("/forecast")
async def get_forecast(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    txns = await _get_txns(db, user.id)
    balance = await _balance(db, user.id)
    return forecast_runway(txns, balance)
