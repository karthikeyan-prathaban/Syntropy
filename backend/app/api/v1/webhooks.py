import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.domain.models import ConsentRecord, WebhookEvent
from app.workers.queue import enqueue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

ACTIVE_STATUSES = {"ACTIVE", "APPROVED", "SUCCESS"}


def verify_signature(body: bytes, signature: str | None) -> bool:
    secret = get_settings().setu_webhook_secret
    if not secret:
        # Without a configured secret nothing can be trusted, so nothing is processed.
        return False
    if not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    provided = signature.split("=")[-1].strip()
    return hmac.compare_digest(expected, provided)


@router.post("/setu", status_code=202)
async def setu_webhook(
    request: Request,
    x_setu_signature: str | None = Header(None, alias="X-Setu-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """Receive Setu consent and FI notifications.

    The consent is created PERIODIC, so this is what makes data actually refresh
    rather than only updating when a user opens the app.
    """
    body = await request.body()
    valid = verify_signature(body, x_setu_signature)

    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    data = payload.get("data") or payload
    consent_id = data.get("consentId") or data.get("consent_id")
    event = WebhookEvent(
        provider="setu",
        event_type=payload.get("type") or payload.get("eventType"),
        consent_id=consent_id,
        session_id=data.get("sessionId") or data.get("session_id"),
        payload=payload,
        signature_valid=valid,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    if not valid:
        logger.warning("Rejected Setu webhook with invalid signature (event %s)", event.id)
        raise HTTPException(status_code=401, detail="Invalid signature")

    if not consent_id:
        event.processed = True
        event.error = "No consentId in payload"
        await db.commit()
        return {"received": True, "action": "ignored"}

    record = (
        await db.execute(select(ConsentRecord).where(ConsentRecord.consent_id == consent_id))
    ).scalar_one_or_none()
    if record is None:
        event.processed = True
        event.error = "Unknown consent"
        await db.commit()
        return {"received": True, "action": "unknown_consent"}

    status = (data.get("status") or "").upper()
    if status:
        record.status = status
    await db.commit()

    action = "status_updated"
    if status in ACTIVE_STATUSES or (event.event_type or "").upper().startswith("SESSION"):
        # Fetching can take a while, so it always goes through the queue.
        if await enqueue("refresh_consent_job", record.id):
            action = "refresh_queued"
        else:
            action = "refresh_skipped_no_queue"

    event.processed = True
    await db.commit()
    return {"received": True, "action": action}
