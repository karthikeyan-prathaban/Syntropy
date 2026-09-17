from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import BankAccount, ConsentRecord, Transaction, User, WaitlistEntry
from sqlalchemy import delete

router = APIRouter(tags=["marketing"])


class WaitlistPayload(BaseModel):
    email: EmailStr
    source: str | None = None
    utm: str | None = None


class AnalyticsEvent(BaseModel):
    event: str
    props: dict | None = None


@router.post("/waitlist")
async def join_waitlist(payload: WaitlistPayload, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == payload.email))
    if existing.scalar_one_or_none():
        count = await db.scalar(select(func.count()).select_from(WaitlistEntry))
        return {"status": "already_joined", "total": count, "position": count}
    db.add(WaitlistEntry(email=payload.email, source=payload.source, utm=payload.utm))
    await db.commit()
    count = await db.scalar(select(func.count()).select_from(WaitlistEntry))
    return {"status": "joined", "total": count, "position": count}


@router.get("/waitlist/count")
async def waitlist_count(db: AsyncSession = Depends(get_db)):
    count = await db.scalar(select(func.count()).select_from(WaitlistEntry)) or 0
    return {"count": count}


@router.post("/analytics")
async def track_event(payload: AnalyticsEvent):
    return {"ok": True, "event": payload.event}


@router.delete("/me/data")
async def purge_user_data(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Transaction).where(Transaction.user_id == user.id))
    await db.execute(delete(BankAccount).where(BankAccount.user_id == user.id))
    await db.execute(delete(ConsentRecord).where(ConsentRecord.user_id == user.id))
    await db.commit()
    return {"status": "purged"}
