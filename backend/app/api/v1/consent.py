import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import BankAccount, ConsentRecord, Transaction, User
from app.services.fi_parser import parse_deposit_fi_data
from app.services.setu_client import setu_client

router = APIRouter(prefix="/consent", tags=["consent"])


@router.post("/create")
async def create_consent(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    from app.core.crypto import decrypt_field

    mobile = decrypt_field(user.mobile_enc)
    data = await setu_client.create_consent(mobile, settings.consent_redirect_url)
    record = ConsentRecord(
        user_id=user.id,
        request_id=data.get("id") or data.get("requestId") or data.get("request_id", ""),
        consent_url=data.get("url") or data.get("consentUrl") or data.get("consent_url"),
        status="PENDING",
    )
    db.add(record)
    await db.commit()
    return {
        "request_id": record.request_id,
        "consent_url": record.consent_url,
        "status": record.status,
    }


@router.get("/{request_id}/status")
async def consent_status(request_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ConsentRecord).where(ConsentRecord.request_id == request_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Consent not found")
    try:
        data = await setu_client.get_consent(request_id)
        status = data.get("status") or record.status
        consent_id = data.get("consentId") or data.get("consent_id")
        record.status = status
        if consent_id:
            record.consent_id = consent_id
        await db.commit()
    except Exception:
        pass
    return {"request_id": record.request_id, "status": record.status, "consent_id": record.consent_id}


@router.post("/{request_id}/fetch")
async def fetch_financial_data(request_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ConsentRecord).where(ConsentRecord.request_id == request_id))
    record = result.scalar_one_or_none()
    if not record or not record.consent_id:
        raise HTTPException(status_code=400, detail="Consent not active")
    if record.status not in {"ACTIVE", "APPROVED", "SUCCESS"}:
        raise HTTPException(status_code=400, detail=f"Consent status: {record.status}")

    session = await setu_client.create_fi_session(record.consent_id)
    session_id = session.get("id") or session.get("sessionId")
    fi_data = {}
    for _ in range(15):
        fi_data = await setu_client.get_fi_session(session_id)
        if fi_data.get("status") in {"COMPLETED", "PARTIAL"}:
            break
        await asyncio.sleep(2)

    accounts, transactions = parse_deposit_fi_data(fi_data)
    await db.execute(delete(Transaction).where(Transaction.user_id == record.user_id))
    await db.execute(delete(BankAccount).where(BankAccount.user_id == record.user_id))

    account_map: dict[str, int] = {}
    for acc in accounts:
        row = BankAccount(user_id=record.user_id, **acc)
        db.add(row)
        await db.flush()
        account_map[acc["linked_acc_ref"]] = row.id

    for txn in transactions:
        db.add(
            Transaction(
                user_id=record.user_id,
                account_id=account_map[txn["linked_acc_ref"]],
                txn_id=txn["txn_id"],
                amount=txn["amount"],
                txn_type=txn["txn_type"],
                narration=txn["narration"],
                mode=txn["mode"],
                category=txn["category"],
                transaction_timestamp=txn["transaction_timestamp"],
                balance_after=txn.get("balance_after"),
            )
        )
    await db.commit()
    return {"accounts": len(accounts), "transactions": len(transactions), "session_status": fi_data.get("status")}


@router.post("/{consent_id}/revoke")
async def revoke_consent(consent_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == user.id, ConsentRecord.consent_id == consent_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Consent not found")
    await setu_client.revoke_consent(consent_id)
    record.status = "REVOKED"
    await db.commit()
    return {"status": "REVOKED", "consent_id": consent_id}
