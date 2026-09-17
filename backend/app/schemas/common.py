from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: int
    name: str
    mobile: str
    vua: str
    email: str | None = None
    avatar_initials: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    mobile: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TransactionResponse(BaseModel):
    id: int
    txn_id: str
    amount: float
    txn_type: str
    narration: str
    mode: str
    category: str
    transaction_timestamp: datetime
    balance_after: float | None = None
    masked_acc_number: str | None = None

    model_config = {"from_attributes": True}


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
    consent_status: str | None
    accounts: list[dict]
