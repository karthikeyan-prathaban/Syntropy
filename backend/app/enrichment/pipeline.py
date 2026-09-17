from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import new_session
from app.domain.models import Merchant, RecurringSeries, Transaction
from app.enrichment.merchants import normalize_merchant
from app.enrichment.recurring import detect_recurring
from app.enrichment.transfers import detect_transfers

logger = logging.getLogger(__name__)


async def _resolve_merchants(db: AsyncSession, user_id: int, transactions: list[Transaction]) -> int:
    rows = await db.execute(select(Merchant).where(Merchant.user_id == user_id))
    by_key: dict[str, Merchant] = {m.canonical_key: m for m in rows.scalars()}

    updated = 0
    for txn in transactions:
        match = normalize_merchant(txn.raw_narration or txn.narration, txn.mode, txn.txn_type)
        merchant = by_key.get(match.canonical_key)
        if merchant is None:
            merchant = Merchant(
                user_id=user_id,
                canonical_key=match.canonical_key,
                display_name=match.display_name,
                category=match.category or txn.category,
            )
            db.add(merchant)
            await db.flush()
            by_key[match.canonical_key] = merchant

        txn.merchant_id = merchant.id
        txn.merchant_name = match.display_name
        txn.counterparty_vpa = match.vpa
        # A confident alias hit knows the category better than the keyword rules do,
        # but a user's manual override always wins.
        if match.category and match.confidence >= 0.9 and not txn.category_overridden_by_user:
            txn.category = match.category
        updated += 1
    return updated


async def _rebuild_recurring(db: AsyncSession, user_id: int, transactions: list[Transaction]) -> int:
    detected = detect_recurring(transactions)

    await db.execute(delete(RecurringSeries).where(RecurringSeries.user_id == user_id))
    await db.flush()

    by_merchant: dict[tuple[str, str], int] = {}
    for item in detected:
        row = RecurringSeries(
            user_id=user_id,
            merchant_name=item.merchant_name,
            category=item.category,
            cadence=item.cadence,
            interval_days=item.interval_days,
            expected_amount=item.expected_amount,
            amount_variation=item.amount_variation,
            occurrences=item.occurrences,
            confidence=item.confidence,
            direction=item.direction,
            first_seen=item.first_seen,
            last_seen=item.last_seen,
            next_due=item.next_due,
        )
        db.add(row)
        await db.flush()
        by_merchant[(item.merchant_name, item.direction)] = row.id

    for txn in transactions:
        key = (txn.merchant_name or "", txn.txn_type.upper())
        series_id = by_merchant.get(key)
        txn.recurring_series_id = series_id
        txn.is_recurring = series_id is not None

    return len(detected)


async def run_enrichment(db: AsyncSession, user_id: int) -> dict[str, int]:
    """Re-derive merchants, transfers and recurring series for one user.

    Idempotent: safe to run after every ingestion.
    """
    rows = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_timestamp)
    )
    transactions = list(rows.scalars())
    if not transactions:
        return {"transactions": 0, "merchants": 0, "transfers": 0, "recurring": 0}

    merchants = await _resolve_merchants(db, user_id, transactions)
    transfers = detect_transfers(transactions)
    await db.flush()
    recurring = await _rebuild_recurring(db, user_id, transactions)
    await db.commit()

    return {
        "transactions": len(transactions),
        "merchants": merchants,
        "transfers": transfers,
        "recurring": recurring,
    }


async def enrich_user(user_id: int) -> dict[str, int]:
    """Entry point for background tasks, which own their own session."""
    async with new_session() as db:
        try:
            return await run_enrichment(db, user_id)
        except Exception:
            await db.rollback()
            logger.exception("Enrichment failed for user %s", user_id)
            return {"transactions": 0, "merchants": 0, "transfers": 0, "recurring": 0}
