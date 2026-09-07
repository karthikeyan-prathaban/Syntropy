"""
AI-powered spend advisor for Syntropy.
Provides intelligent financial recommendations based on transaction patterns.
Uses Google Gemini if API key available, falls back to enhanced rule engine.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
import os
import json

# Try to import Gemini — optional dependency
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or not GEMINI_AVAILABLE:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


def _analyze_with_gemini(model, category_breakdown: list, monthly_trend: list, 
                          income: float, expense: float, savings_rate: float) -> list[dict]:
    """Use Gemini to generate contextual financial advice."""
    try:
        categories_summary = ", ".join([
            f"{c['category']}: ₹{c['amount']:,.0f} ({c['percentage']:.1f}%)" 
            for c in category_breakdown[:6]
        ])
        
        prompt = f"""You are a personal finance advisor for Indian users. Analyze this spending data and provide 4-5 specific, actionable recommendations.

Monthly Income: ₹{income:,.0f}
Monthly Expense: ₹{expense:,.0f}  
Savings Rate: {savings_rate:.1f}%
Top Spending Categories: {categories_summary}

Return ONLY a JSON array with objects having: title (string, max 8 words), description (string, 1-2 sentences with specific ₹ amounts), priority (high/medium/low), saving_potential (estimated monthly savings in INR as number).

Focus on: specific actionable steps, realistic savings amounts, Indian context (UPI, grocery apps, etc.)"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception:
        return []


def build_insights(transactions: list[dict[str, Any]], total_balance: float) -> dict[str, Any]:
    """Main insights builder — tries Gemini, falls back to enhanced rule engine."""
    
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
                    "description": "Complete the AA consent flow to fetch your transactions and unlock personalized AI-powered spending insights.",
                    "priority": "high",
                    "saving_potential": 0,
                }
            ],
        }

    now = datetime.utcnow()
    current_month = _month_key(now)
    
    # Use last 3 months of data for better analysis
    three_months_ago = now - timedelta(days=90)
    recent_txns = [t for t in transactions if t["transaction_timestamp"] >= three_months_ago]
    month_txns = [t for t in transactions if _month_key(t["transaction_timestamp"]) == current_month]
    
    # If current month has < 5 txns (early in month), use previous month
    if len(month_txns) < 5:
        prev_month = _month_key(now - timedelta(days=30))
        month_txns = [t for t in transactions if _month_key(t["transaction_timestamp"]) == prev_month]

    income = sum(t["amount"] for t in month_txns if t["txn_type"] == "CREDIT")
    expense = sum(t["amount"] for t in month_txns if t["txn_type"] == "DEBIT")
    savings_rate = ((income - expense) / income * 100) if income > 0 else 0

    # Category breakdown for current/prev month
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

    # Monthly trend (last 6 months)
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

    # --- Health Score Calculation (0-100) ---
    health_score = 50

    # Savings rate impact (±30 pts)
    if savings_rate >= 30:
        health_score += 30
    elif savings_rate >= 20:
        health_score += 20
    elif savings_rate >= 10:
        health_score += 10
    elif savings_rate >= 0:
        health_score += 2
    else:
        health_score -= 20

    # Balance cushion impact (±10 pts)
    months_of_expenses = (total_balance / expense) if expense > 0 else 0
    if months_of_expenses >= 6:
        health_score += 10
    elif months_of_expenses >= 3:
        health_score += 5
    elif months_of_expenses < 1:
        health_score -= 10

    # Spending diversity penalty (too much in one category)
    if category_breakdown:
        top_category_pct = category_breakdown[0]["percentage"]
        if top_category_pct > 50:
            health_score -= 10
        elif top_category_pct > 35:
            health_score -= 5

    # Income stability (look at last 3 months)
    last_3_months = sorted(monthly.keys())[-3:]
    if len(last_3_months) >= 3:
        incomes = [monthly[m]["income"] for m in last_3_months]
        if all(i > 0 for i in incomes):
            health_score += 5  # consistent income

    health_score = max(0, min(100, health_score))

    # --- Smart Recommendations ---
    # Try Gemini first
    gemini_model = _get_gemini_client()
    recommendations = []
    
    if gemini_model and category_breakdown and income > 0:
        recommendations = _analyze_with_gemini(
            gemini_model, category_breakdown, monthly_trend, income, expense, savings_rate
        )

    # Rule-based engine (used as fallback or supplement)
    if not recommendations:
        food_pct = next((c["percentage"] for c in category_breakdown if "Food" in c["category"]), 0)
        food_amt = next((c["amount"] for c in category_breakdown if "Food" in c["category"]), 0)
        entertainment_amt = category_totals.get("Entertainment", 0)
        shopping_amt = category_totals.get("Shopping", 0)
        transport_amt = category_totals.get("Transport", 0)
        
        if savings_rate < 20 and income > 0:
            target_savings = income * 0.20
            current_savings = income - expense
            gap = max(0, target_savings - current_savings)
            recommendations.append({
                "title": "Boost your monthly savings",
                "description": f"You're saving {savings_rate:.1f}% of income. Reaching the 20% goal needs ₹{gap:,.0f} more savings — try auto-debiting to a RD or liquid fund on salary day.",
                "priority": "high",
                "saving_potential": int(gap),
            })

        if food_pct > 15 and food_amt > 0:
            cut = food_amt * 0.25
            recommendations.append({
                "title": "Trim food & dining expenses",
                "description": f"Food & dining is {food_pct:.1f}% of your spending (₹{food_amt:,.0f}). Cooking 2 more meals at home per week could save ~₹{cut:,.0f}/month.",
                "priority": "high" if food_pct > 25 else "medium",
                "saving_potential": int(cut),
            })

        if total_balance < expense * 3 and expense > 0:
            target = expense * 3
            gap = max(0, target - total_balance)
            recommendations.append({
                "title": "Build a 3-month emergency fund",
                "description": f"Your balance covers less than 3 months of expenses. Aim for ₹{target:,.0f} in a high-yield savings account for financial security.",
                "priority": "high",
                "saving_potential": 0,
            })

        if entertainment_amt > 1500:
            cut = entertainment_amt * 0.30
            recommendations.append({
                "title": "Audit streaming subscriptions",
                "description": f"You spent ₹{entertainment_amt:,.0f} on entertainment. Cancelling 1-2 unused subscriptions could free up ₹{cut:,.0f}/month.",
                "priority": "medium",
                "saving_potential": int(cut),
            })

        if shopping_amt > income * 0.15 and income > 0:
            cut = shopping_amt * 0.20
            recommendations.append({
                "title": "Apply 48-hour rule for shopping",
                "description": f"Shopping is ₹{shopping_amt:,.0f} this month ({shopping_amt/income*100:.1f}% of income). A 48-hour wait before non-essential purchases can save ~₹{cut:,.0f}.",
                "priority": "medium",
                "saving_potential": int(cut),
            })

        if transport_amt > 2000:
            cut = transport_amt * 0.15
            recommendations.append({
                "title": "Optimise transport costs",
                "description": f"₹{transport_amt:,.0f} on transport this month. Consider monthly passes or carpooling to save ~₹{cut:,.0f}.",
                "priority": "low",
                "saving_potential": int(cut),
            })

        if savings_rate >= 25 and total_balance > expense * 6:
            recommendations.append({
                "title": "Your finances look great!",
                "description": "You have strong savings rate and a healthy emergency fund. Consider investing surplus in index funds (Nifty 50 ETF) or PPF for long-term wealth creation.",
                "priority": "low",
                "saving_potential": 0,
            })

    # Ensure we always have at least one recommendation
    if not recommendations:
        recommendations.append({
            "title": "You're on the right track",
            "description": "Keep monitoring your monthly trends. Consider allocating any surplus to a Nifty 50 index fund for long-term wealth building.",
            "priority": "low",
            "saving_potential": 0,
        })

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
