import re
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.redis import get_redis

# (regex, max_requests, window_seconds). Patterns are matched against the full path
# so parameterised routes like /consent/{id}/revoke are actually covered.
RATE_LIMITS: list[tuple[re.Pattern[str], int, int]] = [
    (re.compile(r"^/api/v1/auth/login$"), 10, 60),
    (re.compile(r"^/api/v1/auth/signup$"), 5, 60),
    (re.compile(r"^/api/v1/auth/demo-login$"), 5, 60),
    (re.compile(r"^/api/v1/auth/refresh$"), 30, 60),
    (re.compile(r"^/api/v1/auth/password-reset"), 5, 300),
    (re.compile(r"^/api/v1/consent/create$"), 10, 60),
    (re.compile(r"^/api/v1/consent/[^/]+/status$"), 60, 60),
    (re.compile(r"^/api/v1/consent/[^/]+/fetch$"), 10, 60),
    (re.compile(r"^/api/v1/consent/[^/]+/revoke$"), 10, 60),
    (re.compile(r"^/api/v1/statements/upload$"), 20, 300),
    (re.compile(r"^/api/v1/me/data$"), 3, 300),
    (re.compile(r"^/api/v1/recall/query$"), 30, 60),
    (re.compile(r"^/api/v1/insights/chat$"), 30, 60),
]


def _match(path: str) -> tuple[int, int] | None:
    for pattern, limit, window in RATE_LIMITS:
        if pattern.match(path):
            return limit, window
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limiter. Uses Redis when available so limits hold across workers,
    falling back to per-process memory only for local development."""

    def __init__(self, app):
        super().__init__(app)
        self._memory: dict[str, list[float]] = defaultdict(list)

    def reset(self) -> None:
        self._memory.clear()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if get_settings().environment == "test":
            return await call_next(request)
        matched = _match(request.url.path)
        if matched is None:
            return await call_next(request)

        limit, window = matched
        client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        key = f"ratelimit:{client_ip}:{request.url.path}"

        if await self._is_limited(key, limit, window):
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please try again shortly."},
                status_code=429,
                headers={"Retry-After": str(window)},
            )
        return await call_next(request)

    async def _is_limited(self, key: str, limit: int, window: int) -> bool:
        redis = await get_redis()
        if redis is not None:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window)
            return count > limit

        now = time.time()
        hits = [t for t in self._memory[key] if t > now - window]
        self._memory[key] = hits
        if len(hits) >= limit:
            return True
        hits.append(now)
        return False
