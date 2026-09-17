from __future__ import annotations

import logging
import time
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import BalanceSnapshot, BankAccount, IngestionRun, Transaction
from app.ingestion.base import CanonicalTransaction, IngestionResult
from app.ingestion.dedupe import compute_txn_hash
from app.services.categorizer import classify

logger = logging.getLogger(__name__)


async def _upsert_accounts(
    db: AsyncSession, user_id: int, result: IngestionResult
) -> dict[str, int]:
    """Match on (user_id, linked_acc_ref) and update in place. Never delete."""
    refs = [a.linked_acc_ref for a in result.accounts]
    existing: dict[str, BankAccount] = {}
    if refs:
        rows = await db.execute(
            select(BankAccount).where(
                BankAccount.user_id == user_id, BankAccount.linked_acc_ref.in_(refs)
            )
        )
        existing = {r.linked_acc_ref: r for r in rows.scalars()}

    account_map: dict[str, int] = {}
    for acc in result.accounts:
        row = existing.get(acc.linked_acc_ref)
        if row is None:
            row = BankAccount(user_id=user_id, linked_acc_ref=acc.linked_acc_ref, source=result.source)
            db.add(row)
        row.masked_acc_number = acc.masked_acc_number or row.masked_acc_number or "****"
        row.account_type = acc.account_type or row.account_type
        row.fi_type = acc.fi_type or row.fi_type
        row.current_balance = acc.current_balance
        row.currency = acc.currency or "INR"
        row.fip_id = acc.fip_id or row.fip_id
        row.bank_name = acc.bank_name or row.bank_name
        row.holder_name = acc.holder_name or row.holder_name
        if acc.holdings:
            row.holdings = acc.holdings
        row.is_active = True
        row.last_synced_at = datetime.utcnow()
        await db.flush()
        account_map[acc.linked_acc_ref] = row.id

        if acc.current_balance:
            today = datetime.utcnow().date()
            snap = await db.execute(
                select(BalanceSnapshot).where(
                    BalanceSnapshot.account_id == row.id, BalanceSnapshot.snapshot_date == today
                )
            )
            snapshot = snap.scalar_one_or_none()
            if snapshot is None:
                db.add(
                    BalanceSnapshot(
                        user_id=user_id,
                        account_id=row.id,
                        snapshot_date=today,
                        balance=acc.current_balance,
                    )
                )
            else:
                snapshot.balance = acc.current_balance
    return account_map


async def ingest(
    db: AsyncSession,
    user_id: int,
    result: IngestionResult,
    trigger: str = "manual",
) -> IngestionRun:
    """Merge a source's output into the user's data without ever destroying history.

    Deduplication is by (user_id, txn_hash), so the same transaction arriving from a
    statement upload and later from AA collapses into a single row.
    """
    started = time.perf_counter()
    run = IngestionRun(user_id=user_id, source=result.source, trigger=trigger, status="running")
    db.add(run)
    await db.flush()

    try:
        account_map = await _upsert_accounts(db, user_id, result)

        # Any account referenced only by transactions still needs a row.
        missing_refs = {
            t.linked_acc_ref for t in result.transactions if t.linked_acc_ref not in account_map
        }
        for ref in missing_refs:
            row = BankAccount(
                user_id=user_id,
                linked_acc_ref=ref,
                masked_acc_number="****",
                source=result.source,
            )
            db.add(row)
            await db.flush()
            account_map[ref] = row.id

        hashed: dict[str, CanonicalTransaction] = {}
        for txn in result.transactions:
            txn_hash = compute_txn_hash(
                user_id,
                txn.linked_acc_ref,
                txn.transaction_timestamp,
                txn.amount,
                txn.txn_type,
                txn.narration,
            )
            # Collapse duplicates inside the same batch before touching the database.
            hashed[txn_hash] = txn

        known: set[str] = set()
        if hashed:
            rows = await db.execute(
                select(Transaction.txn_hash).where(
                    Transaction.user_id == user_id, Transaction.txn_hash.in_(list(hashed))
                )
            )
            known = set(rows.scalars())

        new_count = 0
        for txn_hash, txn in hashed.items():
            if txn_hash in known:
                continue
            db.add(
                Transaction(
                    user_id=user_id,
                    account_id=account_map[txn.linked_acc_ref],
                    txn_id=txn.txn_id or txn_hash[:32],
                    txn_hash=txn_hash,
                    amount=abs(float(txn.amount)),
                    txn_type=txn.txn_type.upper(),
                    narration=txn.narration,
                    raw_narration=txn.narration,
                    mode=txn.mode or "",
                    category=classify(txn.narration, txn.txn_type),
                    source=result.source,
                    transaction_timestamp=txn.transaction_timestamp,
                    balance_after=txn.balance_after,
                )
            )
            new_count += 1

        run.accounts_seen = len(account_map)
        run.rows_in = len(result.transactions)
        run.rows_new = new_count
        run.rows_duplicate = len(result.transactions) - new_count
        run.status = "completed"
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:1000]
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        logger.exception("Ingestion failed for user %s from %s", user_id, result.source)
        raise
    finally:
        run.duration_ms = int((time.perf_counter() - started) * 1000)

    await db.commit()
    return run
