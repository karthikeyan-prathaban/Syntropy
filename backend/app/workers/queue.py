from __future__ import annotations

import logging
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_pool: ArqRedis | None = None
_unavailable = False


async def get_queue() -> ArqRedis | None:
    global _pool, _unavailable
    if _unavailable:
        return None
    if _pool is not None:
        return _pool

    settings = get_settings()
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    if not settings.is_production:
        # Fail fast locally instead of retrying with backoff against a Redis
        # that is deliberately not running.
        redis_settings.conn_retries = 0
        redis_settings.conn_timeout = 2

    try:
        _pool = await create_pool(redis_settings)
    except Exception as exc:
        if settings.is_production:
            raise
        logger.warning("Job queue unavailable (%s); jobs will run inline", exc)
        _unavailable = True
        return None
    return _pool


async def enqueue(function: str, *args: Any) -> bool:
    """Queue a job. Returns False when no queue is available so the caller can
    fall back to running the work inline (development without Redis)."""
    queue = await get_queue()
    if queue is None:
        return False
    await queue.enqueue_job(function, *args)
    return True


async def close_queue() -> None:
    global _pool, _unavailable
    if _pool is not None:
        await _pool.aclose()
        _pool = None
    _unavailable = False
