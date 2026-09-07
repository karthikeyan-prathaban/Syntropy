from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os

from app.api.routes import router
from app.config import get_settings
from app.database import Base, engine
from app.models import models  # noqa: F401

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Syntropy API",
    version="2.0.0",
    description="Open Finance Dashboard — AI-powered personal finance on India's Account Aggregator framework",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"ok": True, "service": "syntropy-api", "version": "2.0.0"}


# ── Waitlist ──────────────────────────────────────────────────────────────────
class WaitlistEntry(BaseModel):
    email: str
    source: Optional[str] = "web"
    utm: Optional[dict] = None


@app.post("/api/waitlist")
async def join_waitlist(entry: WaitlistEntry):
    """Capture waitlist emails with full marketing attribution — stored in waitlist.json."""
    path = "waitlist.json"
    try:
        data = json.loads(open(path).read()) if os.path.exists(path) else []
        emails = [item["email"] if isinstance(item, dict) else item for item in data]
        if entry.email not in emails:
            new_record = {
                "email": entry.email,
                "source": entry.source or "web",
                "utm": entry.utm or {},
                "created_at": datetime.utcnow().isoformat(),
            }
            data.append(new_record)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            pos = 1480 + len(data)
        else:
            idx = emails.index(entry.email)
            pos = 1480 + idx + 1
        return {"status": "added", "total": len(data), "position": pos}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ── Analytics event tracking ──────────────────────────────────────────────────
class AnalyticsEvent(BaseModel):
    event: str
    props: Optional[dict] = {}
    ts: Optional[int] = None
    url: Optional[str] = None


@app.post("/api/analytics")
async def track_event(event: AnalyticsEvent, request: Request):
    """
    Capture custom frontend analytics events.
    Events are appended to analytics_events.jsonl for later analysis.
    Swap for Segment / Mixpanel / PostHog in production.
    """
    path = "analytics_events.jsonl"
    try:
        line = json.dumps({
            "event": event.event,
            "props": event.props,
            "ts": event.ts,
            "url": event.url,
            "ip": request.client.host if request.client else None,
            "ua": request.headers.get("user-agent", ""),
        })
        with open(path, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
    return {"ok": True}


@app.get("/api/analytics/summary")
async def analytics_summary():
    """Quick summary of tracked events — for internal use."""
    path = "analytics_events.jsonl"
    if not os.path.exists(path):
        return {"events": [], "total": 0}
    events: dict = {}
    with open(path) as f:
        for line in f:
            try:
                e = json.loads(line)
                name = e.get("event", "unknown")
                events[name] = events.get(name, 0) + 1
            except Exception:
                pass
    return {"breakdown": events, "total": sum(events.values())}


@app.get("/api/waitlist/count")
async def waitlist_count():
    """Returns waitlist size — for landing page social proof."""
    path = "waitlist.json"
    if not os.path.exists(path):
        return {"count": 0}
    try:
        data = json.loads(open(path).read())
        return {"count": len(data)}
    except Exception:
        return {"count": 0}
