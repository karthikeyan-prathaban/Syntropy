import asyncio
import time

import httpx
from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import get_settings
from app.core.redis import get_redis
from app.db.session import engine

router = APIRouter(tags=["health"])


async def _check_postgres() -> dict:
    started = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": round((time.perf_counter() - started) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:200]}


async def _check_redis() -> dict:
    started = time.perf_counter()
    try:
        redis = await get_redis()
        if redis is None:
            return {"status": "unavailable", "detail": "Redis not configured or unreachable"}
        await redis.ping()
        return {"status": "ok", "latency_ms": round((time.perf_counter() - started) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:200]}


async def _check_setu() -> dict:
    settings = get_settings()
    if not settings.setu_client_id:
        return {"status": "not_configured"}
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.setu_fiu_base_url}/health")
        healthy = response.status_code < 500
        return {
            "status": "ok" if healthy else "degraded",
            "http_status": response.status_code,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:200]}


@router.get("/health")
async def health():
    """Liveness. Intentionally cheap so the orchestrator never restarts on a slow dep."""
    return {"status": "ok", "service": "novaa-api", "version": "2.0.0"}


@router.get("/health/ready")
async def readiness(response: Response):
    """Readiness. Actually probes the dependencies rather than asserting they work."""
    postgres, redis, setu = await asyncio.gather(
        _check_postgres(), _check_redis(), _check_setu()
    )
    checks = {"postgres": postgres, "redis": redis, "setu": setu}
    # Setu being down degrades AA refresh but the app still serves stored data.
    ready = postgres["status"] == "ok"
    if not ready:
        response.status_code = 503
    return {
        "status": "ready" if ready else "not_ready",
        "environment": get_settings().environment,
        "checks": checks,
    }
