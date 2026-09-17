import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.storage import storage
from app.db.session import get_db
from app.domain.models import StatementUpload, User
from app.ingestion.parsers import ALL_PARSERS, ParseError, detect_bank
from app.workers.queue import enqueue
from app.workers.tasks import parse_statement_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/statements", tags=["statements"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_SUFFIXES = (".pdf", ".csv", ".xls", ".xlsx", ".txt")


@router.get("/supported-banks")
async def supported_banks():
    return {
        "banks": [
            {"code": p.bank, "name": p.display_name}
            for p in ALL_PARSERS
        ],
        "formats": ["PDF", "CSV", "XLS", "XLSX"],
        "max_size_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
    }


@router.post("/upload", status_code=202)
async def upload_statement(
    file: UploadFile = File(...),
    password: str | None = Form(None),
    bank: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "statement"
    if not filename.lower().endswith(ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type. Accepted: {', '.join(ALLOWED_SUFFIXES)}",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )

    # Detect the bank synchronously so a wrong password or unreadable file fails
    # immediately with a useful message rather than silently in a worker.
    try:
        parser = detect_bank(data, filename, password)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    storage_key = await storage.put(user.id, filename, data)
    upload = StatementUpload(
        user_id=user.id,
        filename=filename,
        storage_key=storage_key,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        detected_bank=bank or parser.bank,
        status="pending",
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    if not await enqueue("parse_statement_job", upload.id):
        # No queue configured (local development): parse synchronously so the
        # caller still gets a result rather than a job that never runs.
        await parse_statement_job(None, upload.id)
        await db.refresh(upload)

    return {
        "id": upload.id,
        "status": upload.status,
        "detected_bank": upload.detected_bank,
        "filename": upload.filename,
    }


@router.get("")
async def list_statements(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(StatementUpload)
        .where(StatementUpload.user_id == user.id)
        .order_by(StatementUpload.created_at.desc())
        .limit(50)
    )
    return [
        {
            "id": u.id,
            "filename": u.filename,
            "detected_bank": u.detected_bank,
            "status": u.status,
            "rows_parsed": u.rows_parsed,
            "rows_imported": u.rows_imported,
            "rows_duplicate": u.rows_duplicate,
            "error": u.error,
            "created_at": u.created_at,
            "completed_at": u.completed_at,
        }
        for u in rows.scalars()
    ]


@router.get("/{upload_id}/status")
async def statement_status(
    upload_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    row = await db.execute(
        select(StatementUpload).where(
            StatementUpload.id == upload_id, StatementUpload.user_id == user.id
        )
    )
    upload = row.scalar_one_or_none()
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    return {
        "id": upload.id,
        "status": upload.status,
        "detected_bank": upload.detected_bank,
        "rows_parsed": upload.rows_parsed,
        "rows_imported": upload.rows_imported,
        "rows_duplicate": upload.rows_duplicate,
        "error": upload.error,
        "completed_at": upload.completed_at,
    }


@router.delete("/{upload_id}", status_code=204)
async def delete_statement(
    upload_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    row = await db.execute(
        select(StatementUpload).where(
            StatementUpload.id == upload_id, StatementUpload.user_id == user.id
        )
    )
    upload = row.scalar_one_or_none()
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    # The imported transactions stay; only the source file is purged.
    await storage.delete(upload.storage_key)
    await db.delete(upload)
    await db.commit()
