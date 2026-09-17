from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import apply_zero_leakage_logging
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import init_db

apply_zero_leakage_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="NOVAA API",
    description="Net-worth Observability via Verified Account Aggregation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "NOVAA",
        "version": "1.0.0",
        "tagline": "Your money, in full resolution.",
    }
