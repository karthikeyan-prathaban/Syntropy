from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
import json
import os

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def build_insights(transactions: list[dict[str, Any]], total_balance: float) -> dict[str, Any]:
    if not transactions:
        return {
            "health_score": 0,
            "total_income": 0,
            "total_expense": 0,
            "savings_rate": 0,
            "category_breakdown": [],
            "monthly_trend": [],
            "total_balance": total_balance,
            "recommendations": [
                {
                    "title": "Link your bank account to get started",
                    "description": "Complete the AA consent flow to unlock personalized analytics.",
                    "priority": "high",
                    "saving_potential": 0,
                }
            ],
        }

    now = datetime.utcnow()
    current_month = _month_key(now)
    month_txns = [t for t in transactions if _month_key(t["transaction_timestamp"]) == current_month]
    if len(month_txns) < 5:
        prev_month = _month_key(now - timedelta(days=30))
        month_txns = [t for t in transactions if _month_key(t["transaction_timestamp"]) == prev_month]

    income = sum(t["amount"] for t in month_txns if t["txn_type"] == "CREDIT")
    expense = sum(t["amount"] for t in month_txns if t["txn_type"] == "DEBIT")
    savings_rate = ((income - expense) / income * 100) if income > 0 else 0

    category_totals: dict[str, float] = defaultdict(float)
    category_counts: dict[str, int] = defaultdict(int)
    for t in month_txns:
        if t["txn_type"] == "DEBIT":
            category_totals[t["category"]] += t["amount"]
            category_counts[t["category"]] += 1

    category_breakdown = [
        {
            "category": k,
            "amount": round(v, 2),
            "percentage": round(v / expense * 100, 1) if expense else 0,
            "count": category_counts[k],
        }
        for k, v in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for t in transactions:
        key = _month_key(t["transaction_timestamp"])
        if t["txn_type"] == "CREDIT":
            monthly[key]["income"] += t["amount"]
        else:
            monthly[key]["expense"] += t["amount"]

    monthly_trend = [
        {"month": k, "income": round(v["income"], 2), "expense": round(v["expense"], 2)}
        for k, v in sorted(monthly.items())[-6:]
    ]

    health_score = 50
    if savings_rate >= 30:
        health_score += 30
    elif savings_rate >= 20:
        health_score += 20
    elif savings_rate >= 10:
        health_score += 10
    elif savings_rate < 0:
        health_score -= 20

    months_of_expenses = (total_balance / expense) if expense > 0 else 0
    if months_of_expenses >= 6:
        health_score += 10
    elif months_of_expenses >= 3:
        health_score += 5
    elif months_of_expenses < 1:
        health_score -= 10

    if category_breakdown and category_breakdown[0]["percentage"] > 50:
        health_score -= 10

    health_score = max(0, min(100, health_score))

    recommendations = _rule_recommendations(category_breakdown, income, expense, savings_rate, total_balance)
    return {
        "health_score": health_score,
        "total_income": round(income, 2),
        "total_expense": round(expense, 2),
        "savings_rate": round(savings_rate, 1),
        "total_balance": round(total_balance, 2),
        "category_breakdown": category_breakdown,
        "monthly_trend": monthly_trend,
        "recommendations": recommendations,
    }


def _rule_recommendations(
    category_breakdown: list[dict],
    income: float,
    expense: float,
    savings_rate: float,
    total_balance: float,
) -> list[dict]:
    recs: list[dict] = []
    if savings_rate < 20 and income > 0:
        gap = max(0, income * 0.20 - (income - expense))
        recs.append(
            {
                "title": "Boost your monthly savings",
                "description": f"You're saving {savings_rate:.1f}% of income. Reaching 20% needs ₹{gap:,.0f} more.",
                "priority": "high",
                "saving_potential": int(gap),
            }
        )
    food = next((c for c in category_breakdown if "Food" in c["category"]), None)
    if food and food["percentage"] > 15:
        cut = food["amount"] * 0.25
        recs.append(
            {
                "title": "Trim food & dining expenses",
                "description": f"Food is {food['percentage']:.1f}% of spending. Save ~₹{cut:,.0f}/month.",
                "priority": "medium",
                "saving_potential": int(cut),
            }
        )
    if expense > 0 and total_balance < expense * 3:
        recs.append(
            {
                "title": "Build a 3-month emergency fund",
                "description": f"Aim for ₹{expense * 3:,.0f} in liquid savings.",
                "priority": "high",
                "saving_potential": 0,
            }
        )
    if not recs:
        recs.append(
            {
                "title": "You're on the right track",
                "description": "Keep monitoring trends and consider index funds for surplus.",
                "priority": "low",
                "saving_potential": 0,
            }
        )
    return recs


async def stream_insights_chat(message: str, context: dict[str, Any]):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key and GEMINI_AVAILABLE:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"User question: {message}\nContext: {json.dumps(context)}\nAnswer as NOVAA financial advisor."
        response = model.generate_content(prompt)
        text = response.text or "I could not generate a response."
    else:
        text = (
            f"Based on your data: savings rate is {context.get('savings_rate', 0)}%. "
            f"Top category: {context.get('top_category', 'N/A')}. "
            "Consider reviewing recurring subscriptions and setting a 20% savings target."
        )
    for word in text.split(" "):
        yield word + " "
        await __import__("asyncio").sleep(0.03)
