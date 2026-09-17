import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import BankAccount, ConsentRecord, Transaction, User
from app.schemas.common import DashboardResponse, TransactionResponse
from app.services.insight_engine import build_insights
from app.services.user_service import user_to_response

router = APIRouter(tags=["dashboard"])


async def _txn_dicts(db: AsyncSession, user_id: int) -> list[dict]:
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.transaction_timestamp.desc())
    )
    return [
        {
            "txn_id": t.txn_id,
            "amount": t.amount,
            "txn_type": t.txn_type,
            "narration": t.narration,
            "mode": t.mode,
            "category": t.category,
            "transaction_timestamp": t.transaction_timestamp,
            "balance_after": t.balance_after,
        }
        for t in result.scalars().all()
    ]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    acc_result = await db.execute(select(BankAccount).where(BankAccount.user_id == user.id))
    accounts = acc_result.scalars().all()
    total_balance = sum(a.current_balance for a in accounts)

    txn_result = await db.execute(
        select(Transaction, BankAccount)
        .join(BankAccount, Transaction.account_id == BankAccount.id)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.transaction_timestamp.desc())
        .limit(50)
    )
    recent = []
    for txn, acc in txn_result.all():
        recent.append(
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
        )

    consent_result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == user.id).order_by(ConsentRecord.created_at.desc())
    )
    consent = consent_result.scalars().first()
    insights = build_insights(await _txn_dicts(db, user.id), total_balance)

    return DashboardResponse(
        user=user_to_response(user),
        total_balance=insights["total_balance"],
        health_score=insights["health_score"],
        total_income=insights["total_income"],
        total_expense=insights["total_expense"],
        savings_rate=insights["savings_rate"],
        category_breakdown=insights["category_breakdown"],
        monthly_trend=insights["monthly_trend"],
        recommendations=insights["recommendations"],
        recent_transactions=recent,
        consent_status=consent.status if consent else None,
        accounts=[
            {
                "id": a.id,
                "masked_acc_number": a.masked_acc_number,
                "account_type": a.account_type,
                "current_balance": a.current_balance,
                "currency": a.currency,
                "fip_id": a.fip_id,
            }
            for a in accounts
        ],
    )


@router.post("/mock/load")
async def load_mock(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    fixture = Path(__file__).resolve().parents[3] / "fixtures" / "mock_data.json"
    data = json.loads(fixture.read_text())

    await db.execute(delete(Transaction).where(Transaction.user_id == user.id))
    await db.execute(delete(BankAccount).where(BankAccount.user_id == user.id))

    account_map: dict[str, int] = {}
    for acc in data["accounts"]:
        row = BankAccount(user_id=user.id, **acc)
        db.add(row)
        await db.flush()
        account_map[acc["linked_acc_ref"]] = row.id

    for txn in data["transactions"]:
        from datetime import datetime

        ts = txn["transaction_timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        db.add(
            Transaction(
                user_id=user.id,
                account_id=account_map[txn["linked_acc_ref"]],
                txn_id=txn["txn_id"],
                amount=txn["amount"],
                txn_type=txn["txn_type"],
                narration=txn["narration"],
                mode=txn["mode"],
                category=txn["category"],
                transaction_timestamp=ts,
                balance_after=txn.get("balance_after"),
            )
        )

    consent = ConsentRecord(
        user_id=user.id,
        request_id=f"mock-{user.id}",
        consent_id=f"mock-consent-{user.id}",
        status="ACTIVE",
    )
    db.add(consent)
    await db.commit()
    return {"status": "loaded", "transactions": len(data["transactions"])}
