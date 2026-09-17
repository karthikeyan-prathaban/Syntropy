import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.observability import ObservabilityMiddleware, init_sentry, metrics_endpoint
from app.core.rate_limit import RateLimitMiddleware
from app.core.redis import close_redis
from app.db.schema_check import verify_schema

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()
# Refuses to boot with development secrets or demo routes enabled in production.
settings.validate_production()
init_sentry()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema is owned by Alembic; nothing is created at runtime. This only checks
    # that the migrations have actually been applied.
    logger.info("NOVAA API starting in %s mode", settings.environment)
    await verify_schema()
    yield
    await close_redis()
    from app.workers.queue import close_queue

    await close_queue()


app = FastAPI(
    title="NOVAA API",
    description="Net-worth Observability via Verified Account Aggregation",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ObservabilityMiddleware)

app.include_router(api_router, prefix="/api/v1")
app.add_api_route("/metrics", metrics_endpoint, include_in_schema=False)


@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "NOVAA",
        "version": "2.0.0",
        "tagline": "Your money, in full resolution.",
    }
