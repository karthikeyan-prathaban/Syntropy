from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import BankAccount, Transaction, User
from app.schemas.analytics import RecallQuery
from app.services.insight_engine import build_insights
from app.services.recall_engine import stream_recall_answer

router = APIRouter(prefix="/recall", tags=["recall"])


@router.post("/query")
async def recall_query(
    payload: RecallQuery,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Transaction).where(Transaction.user_id == user.id))
    txns = [
        {
            "txn_id": t.txn_id,
            "amount": t.amount,
            "txn_type": t.txn_type,
            "narration": t.narration,
            "category": t.category,
            "transaction_timestamp": t.transaction_timestamp,
        }
        for t in result.scalars().all()
    ]
    acc_result = await db.execute(select(BankAccount).where(BankAccount.user_id == user.id))
    balance = sum(a.current_balance for a in acc_result.scalars().all())
    insights = build_insights(txns, balance)

    async def event_stream():
        async for chunk in stream_recall_answer(payload.query, txns, insights):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/plain")
