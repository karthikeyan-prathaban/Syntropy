from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import new_session
from app.domain.models import ConsentRecord, StatementUpload
from app.enrichment.pipeline import run_enrichment
from app.ingestion.aa_source import aa_source
from app.ingestion.statement_source import statement_source
from app.ingestion.upsert import ingest

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"ACTIVE", "APPROVED", "SUCCESS"}
AA_REFRESH_INTERVAL = timedelta(hours=12)
STATEMENT_FILE_RETENTION = timedelta(days=90)
WEBHOOK_RETENTION = timedelta(days=180)


async def parse_statement_job(_ctx, upload_id: int) -> dict:
    """Parse an uploaded statement, ingest it, then enrich.

    Parsing a large PDF takes seconds, so it never runs inside the request.
    """
    from app.core.storage import storage

    async with new_session() as db:
        upload = (
            await db.execute(select(StatementUpload).where(StatementUpload.id == upload_id))
        ).scalar_one_or_none()
        if upload is None:
            return {"error": "upload not found"}

        upload.status = "parsing"
        await db.commit()

        try:
            data = await storage.get(upload.storage_key)
            result = await statement_source.fetch(
                data=data, filename=upload.filename, bank_hint=upload.detected_bank
            )
            run = await ingest(db, upload.user_id, result, trigger="statement_upload")

            upload.detected_bank = result.meta.get("bank")
            upload.rows_parsed = run.rows_in
            upload.rows_imported = run.rows_new
            upload.rows_duplicate = run.rows_duplicate
            upload.status = "completed"
            upload.completed_at = datetime.utcnow()
            await db.commit()
        except Exception as exc:
            await db.rollback()
            upload.status = "failed"
            upload.error = str(exc)[:1000]
            upload.completed_at = datetime.utcnow()
            await db.commit()
            logger.exception("Statement parse failed for upload %s", upload_id)
            return {"status": "failed", "error": str(exc)}

        await run_enrichment(db, upload.user_id)
        return {
            "status": "completed",
            "rows_new": upload.rows_imported,
            "rows_duplicate": upload.rows_duplicate,
        }


async def refresh_consent_job(_ctx, consent_record_id: int) -> dict:
    """Pull fresh data for one PERIODIC consent."""
    async with new_session() as db:
        record = (
            await db.execute(select(ConsentRecord).where(ConsentRecord.id == consent_record_id))
        ).scalar_one_or_none()
        if record is None or not record.consent_id or record.status not in ACTIVE_STATUSES:
            return {"skipped": True}

        try:
            result = await aa_source.fetch(consent_id=record.consent_id)
            run = await ingest(db, record.user_id, result, trigger="scheduled_refresh")
            record.last_fetched_at = datetime.utcnow()
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.warning("Scheduled AA refresh failed for consent %s: %s", record.consent_id, exc)
            return {"status": "failed", "error": str(exc)}

        await run_enrichment(db, record.user_id)
        return {"status": "ok", "rows_new": run.rows_new}


async def refresh_all_consents(ctx) -> dict:
    """Cron entry point. The consent is created PERIODIC, so something has to poll it."""
    cutoff = datetime.utcnow() - AA_REFRESH_INTERVAL
    async with new_session() as db:
        rows = await db.execute(
            select(ConsentRecord.id).where(
                ConsentRecord.status.in_(ACTIVE_STATUSES),
                ConsentRecord.consent_id.is_not(None),
                (ConsentRecord.last_fetched_at.is_(None)) | (ConsentRecord.last_fetched_at < cutoff),
            )
        )
        ids = list(rows.scalars())

    for consent_id in ids:
        await refresh_consent_job(ctx, consent_id)
        await asyncio.sleep(1)  # Stay well under Setu's rate limits.
    return {"refreshed": len(ids)}


async def enforce_retention(ctx) -> dict:
    """DPDP retention limits: source files and webhook payloads do not live forever.

    Derived transactions are kept because they are the product; the raw PDF a user
    uploaded is not needed once it has been parsed.
    """
    from sqlalchemy import delete

    from app.core.storage import storage
    from app.domain.models import WebhookEvent

    now = datetime.utcnow()
    statements_purged = 0

    async with new_session() as db:
        stale = (
            await db.execute(
                select(StatementUpload).where(
                    StatementUpload.status == "completed",
                    StatementUpload.completed_at < now - STATEMENT_FILE_RETENTION,
                    StatementUpload.storage_key != "",
                )
            )
        ).scalars().all()

        for upload in stale:
            try:
                await storage.delete(upload.storage_key)
            except Exception:
                logger.exception("Could not delete expired statement %s", upload.storage_key)
                continue
            # The parse result stays; only the source file is gone.
            upload.storage_key = ""
            statements_purged += 1

        result = await db.execute(
            delete(WebhookEvent).where(WebhookEvent.received_at < now - WEBHOOK_RETENTION)
        )
        await db.commit()

    return {"statements_purged": statements_purged, "webhooks_purged": result.rowcount or 0}


async def enrich_user_job(_ctx, user_id: int) -> dict:
    async with new_session() as db:
        return await run_enrichment(db, user_id)


async def nightly_enrichment(ctx) -> dict:
    """Recompute merchants, transfers and recurring series for everyone with data."""
    from app.domain.models import Transaction

    async with new_session() as db:
        rows = await db.execute(select(Transaction.user_id).distinct())
        user_ids = list(rows.scalars())

    for user_id in user_ids:
        await enrich_user_job(ctx, user_id)
    return {"users": len(user_ids)}
