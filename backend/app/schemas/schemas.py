from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    mobile: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# ── Users ─────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    mobile: str = Field(min_length=10, max_length=15)


class UserResponse(BaseModel):
    id: int
    name: str
    mobile: str
    vua: str
    email: Optional[str] = None
    avatar_initials: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Consent ───────────────────────────────────────────────────────────────────
class ConsentCreateResponse(BaseModel):
    request_id: str
    consent_url: str
    status: str


class ConsentStatusResponse(BaseModel):
    request_id: str
    status: str
    consent_id: str | None = None


# ── Transactions ──────────────────────────────────────────────────────────────
class TransactionResponse(BaseModel):
    id: int
    txn_id: str
    amount: float
    txn_type: str
    narration: str
    mode: str
    category: str
    transaction_timestamp: datetime
    balance_after: float | None
    masked_acc_number: str | None = None

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────
class Recommendation(BaseModel):
    title: str
    description: str
    priority: str
    saving_potential: int = 0


class DashboardResponse(BaseModel):
    user: UserResponse
    total_balance: float
    health_score: int
    total_income: float
    total_expense: float
    savings_rate: float
    category_breakdown: list[dict]
    monthly_trend: list[dict]
    recommendations: list[dict]
    recent_transactions: list[TransactionResponse]
    consent_status: str | None = None
    accounts: list[dict] = []
