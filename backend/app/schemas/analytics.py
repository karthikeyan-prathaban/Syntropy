from pydantic import BaseModel, Field


class CashflowPoint(BaseModel):
    month: str
    income: float
    expense: float
    net: float


class CategorySlice(BaseModel):
    category: str
    amount: float
    percentage: float
    count: int


class MerchantRow(BaseModel):
    merchant: str
    amount: float
    count: int
    category: str


class RecurringItem(BaseModel):
    merchant: str
    amount: float
    frequency: str
    category: str
    last_date: str


class CalendarDay(BaseModel):
    date: str
    amount: float
    count: int


class AnomalyItem(BaseModel):
    txn_id: str
    narration: str
    amount: float
    reason: str
    date: str


class ForecastPoint(BaseModel):
    month: str
    projected_expense: float
    projected_income: float
    runway_months: float | None


class BudgetCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    monthly_limit: float = Field(gt=0)
    alert_threshold: float = Field(default=0.8, gt=0, le=1)


class BudgetResponse(BaseModel):
    id: int
    category: str
    monthly_limit: float
    alert_threshold: float
    is_active: bool

    model_config = {"from_attributes": True}


class RecallQuery(BaseModel):
    query: str = Field(min_length=2, max_length=500)


class InsightsChat(BaseModel):
    message: str = Field(min_length=2, max_length=1000)
