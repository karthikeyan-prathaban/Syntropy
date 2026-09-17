from fastapi import APIRouter

from app.api.v1 import analytics, auth, consent, dashboard, insights, marketing, recall, transactions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(consent.router)
api_router.include_router(dashboard.router)
api_router.include_router(analytics.router)
api_router.include_router(insights.router)
api_router.include_router(recall.router)
api_router.include_router(transactions.router)
api_router.include_router(marketing.router)


@api_router.get("/health")
async def health():
    return {"status": "ok", "service": "novaa-api", "version": "1.0.0"}
