import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt_field
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.models import ConsentRecord, User
from app.enrichment.pipeline import run_enrichment
from app.ingestion.aa_source import AAError, aa_source
from app.ingestion.upsert import ingest
from app.services.setu_client import setu_client
from app.workers.queue import enqueue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/consent", tags=["consent"])

ACTIVE_STATUSES = {"ACTIVE", "APPROVED", "SUCCESS"}


async def _get_owned_consent(db: AsyncSession, user_id: int, request_id: str) -> ConsentRecord:
    """Every consent lookup is scoped by user_id, never by request_id alone."""
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == user_id, ConsentRecord.request_id == request_id
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Consent not found")
    return record


@router.post("/create")
async def create_consent(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    mobile = decrypt_field(user.mobile_enc)
    if not mobile:
        raise HTTPException(status_code=400, detail="Add a mobile number before linking a bank")

    try:
        data = await setu_client.create_consent(mobile, settings.consent_redirect_url)
    except httpx.HTTPError as exc:
        logger.error("Setu consent creation failed for user %s: %s", user.id, exc)
        raise HTTPException(status_code=502, detail="Account Aggregator is unavailable") from exc

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
async def consent_status(
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await _get_owned_consent(db, user.id, request_id)
    try:
        data = await setu_client.get_consent(request_id)
        record.status = data.get("status") or record.status
        consent_id = data.get("consentId") or data.get("consent_id")
        if consent_id:
            record.consent_id = consent_id
        await db.commit()
    except httpx.HTTPError as exc:
        # The cached status is still useful, but the failure must not be silent.
        logger.warning("Setu status poll failed for consent %s: %s", request_id, exc)
    except Exception:
        logger.exception("Unexpected error polling consent %s", request_id)

    return {
        "request_id": record.request_id,
        "status": record.status,
        "consent_id": record.consent_id,
    }


@router.post("/{request_id}/fetch")
async def fetch_financial_data(
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await _get_owned_consent(db, user.id, request_id)
    if not record.consent_id:
        raise HTTPException(status_code=400, detail="Consent not active")
    if record.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=400, detail=f"Consent status: {record.status}")

    try:
        result = await aa_source.fetch(consent_id=record.consent_id)
    except AAError as exc:
        logger.warning("AA fetch failed for user %s: %s", user.id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        logger.error("Setu transport error during fetch for user %s: %s", user.id, exc)
        raise HTTPException(status_code=502, detail="Account Aggregator is unavailable") from exc

    run = await ingest(db, user.id, result, trigger="consent_fetch")
    record.last_fetched_at = datetime.utcnow()
    await db.commit()

    if not await enqueue("enrich_user_job", user.id):
        await run_enrichment(db, user.id)

    return {
        "accounts": run.accounts_seen,
        "transactions_received": run.rows_in,
        "transactions_new": run.rows_new,
        "transactions_duplicate": run.rows_duplicate,
        "session_status": result.meta.get("session_status"),
    }


@router.post("/{consent_id}/revoke")
async def revoke_consent(
    consent_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == user.id, ConsentRecord.consent_id == consent_id
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Consent not found")
    try:
        await setu_client.revoke_consent(consent_id)
    except httpx.HTTPError as exc:
        logger.error("Setu revoke failed for consent %s: %s", consent_id, exc)
        raise HTTPException(status_code=502, detail="Could not revoke consent upstream") from exc
    record.status = "REVOKED"
    await db.commit()
    return {"status": "REVOKED", "consent_id": consent_id}
