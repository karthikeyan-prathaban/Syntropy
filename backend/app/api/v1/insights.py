from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import BankAccount, Transaction, User
from app.schemas.analytics import InsightsChat
from app.services.insight_engine import build_insights, stream_insights_chat

router = APIRouter(prefix="/insights", tags=["insights"])


@router.post("/chat")
async def insights_chat(
    payload: InsightsChat,
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
    context = {
        "savings_rate": insights["savings_rate"],
        "top_category": insights["category_breakdown"][0]["category"] if insights["category_breakdown"] else "N/A",
        "health_score": insights["health_score"],
    }

    async def event_stream():
        async for chunk in stream_insights_chat(payload.message, context):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/plain")
