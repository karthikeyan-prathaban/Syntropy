import logging

from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Redis | None = None
_unavailable = False


async def get_redis() -> Redis | None:
    """Return a connected Redis client, or None if Redis is not reachable.

    Callers degrade gracefully rather than failing the request, so local development
    works without a Redis instance running.
    """
    global _client, _unavailable
    if _unavailable:
        return None
    if _client is not None:
        return _client
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
    except Exception as exc:
        # The pool must be released, or its sockets keep the process alive at exit.
        await client.aclose()
        if settings.is_production:
            raise
        logger.warning("Redis unavailable (%s); falling back to in-process state", exc)
        _unavailable = True
        return None
    _client = client
    return _client


async def close_redis() -> None:
    global _client, _unavailable
    if _client is not None:
        await _client.aclose()
        _client = None
    _unavailable = False
