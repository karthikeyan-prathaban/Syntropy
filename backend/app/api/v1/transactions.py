from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import BankAccount, Transaction, User
from app.schemas.common import TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, le=500),
    category: str | None = None,
    txn_type: str | None = None,
):
    query = (
        select(Transaction, BankAccount)
        .join(BankAccount, Transaction.account_id == BankAccount.id)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.transaction_timestamp.desc())
        .limit(limit)
    )
    if category:
        query = query.where(Transaction.category == category)
    if txn_type:
        query = query.where(Transaction.txn_type == txn_type.upper())

    result = await db.execute(query)
    return [
        TransactionResponse(
            id=txn.id,
            txn_id=txn.txn_id,
            amount=txn.amount,
            txn_type=txn.txn_type,
            narration=txn.narration,
            mode=txn.mode,
            category=txn.category,
            transaction_timestamp=txn.transaction_timestamp,
            balance_after=txn.balance_after,
            masked_acc_number=acc.masked_acc_number,
        )
        for txn, acc in result.all()
    ]
