import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

SENSITIVE_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/signup",
    "/api/v1/consent/create",
    "/api/v1/consent/revoke",
    "/api/v1/me/data",
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if not any(path.startswith(p) for p in SENSITIVE_PATHS):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{path}"
        now = time.time()
        window_start = now - self.window_seconds
        self._hits[key] = [t for t in self._hits[key] if t > window_start]
        if len(self._hits[key]) >= self.max_requests:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        self._hits[key].append(now)
        return await call_next(request)
