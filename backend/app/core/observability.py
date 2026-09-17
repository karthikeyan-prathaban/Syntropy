from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

from app.core.config import get_settings
from app.core.logging import request_id_var, user_id_var

logger = logging.getLogger(__name__)

REQUESTS = Counter(
    "novaa_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
LATENCY = Histogram(
    "novaa_http_request_seconds", "HTTP request latency", ["method", "path"]
)
INGESTION_ROWS = Counter(
    "novaa_ingestion_rows_total", "Transactions ingested", ["source", "outcome"]
)


def _route_template(request: Request) -> str:
    """Use the route pattern, not the raw path, so IDs do not explode cardinality."""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_var.set(request_id)
        user_token = user_id_var.set("-")
        started = time.perf_counter()

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            raise
        finally:
            elapsed = time.perf_counter() - started
            path = _route_template(request)
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(request.method, path).observe(elapsed)
            request_id_var.reset(token)
            user_id_var.reset(user_token)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{elapsed * 1000:.1f}"
        return response


def init_sentry() -> None:
    settings = get_settings()
    if not settings.sentry_dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.1,
        # Financial narration is PII; never let it into an error report.
        send_default_pii=False,
    )


async def metrics_endpoint() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
