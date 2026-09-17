from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Any


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _merchant_from_narration(narration: str) -> str:
    text = (narration or "").strip()
    if not text:
        return "Unknown"
    return text.split("/")[0].split("-")[0].strip().title()[:40] or "Unknown"


def _merchant_of(t: dict[str, Any]) -> str:
    """Enrichment already resolved the merchant; the narration split is only a fallback
    for rows ingested before the pipeline last ran."""
    return t.get("merchant") or _merchant_from_narration(t["narration"])


def txn_dicts(transactions: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "txn_id": t.txn_id,
            "amount": t.amount,
            "txn_type": t.txn_type,
            "narration": t.narration,
            "merchant": t.merchant_name,
            "mode": t.mode,
            "category": t.category,
            "transaction_timestamp": t.transaction_timestamp,
        }
        for t in transactions
    ]


def cashflow_series(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for t in transactions:
        key = _month_key(t["transaction_timestamp"])
        if t["txn_type"] == "CREDIT":
            monthly[key]["income"] += t["amount"]
        else:
            monthly[key]["expense"] += t["amount"]
    return [
        {
            "month": k,
            "income": round(v["income"], 2),
            "expense": round(v["expense"], 2),
            "net": round(v["income"] - v["expense"], 2),
        }
        for k, v in sorted(monthly.items())[-12:]
    ]


def category_slices(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for t in transactions:
        if t["txn_type"] == "DEBIT":
            totals[t["category"]] += t["amount"]
            counts[t["category"]] += 1
    total = sum(totals.values()) or 1
    return [
        {
            "category": k,
            "amount": round(v, 2),
            "percentage": round(v / total * 100, 1),
            "count": counts[k],
        }
        for k, v in sorted(totals.items(), key=lambda x: x[1], reverse=True)
    ]


def merchant_leaderboard(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merchants: dict[str, dict[str, Any]] = defaultdict(lambda: {"amount": 0.0, "count": 0, "category": "Other"})
    for t in transactions:
        if t["txn_type"] != "DEBIT":
            continue
        m = _merchant_of(t)
        merchants[m]["amount"] += t["amount"]
        merchants[m]["count"] += 1
        merchants[m]["category"] = t["category"]
    return [
        {
            "merchant": k,
            "amount": round(v["amount"], 2),
            "count": v["count"],
            "category": v["category"],
        }
        for k, v in sorted(merchants.items(), key=lambda x: x[1]["amount"], reverse=True)[:20]
    ]


def recurring_subscriptions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    debits = [t for t in transactions if t["txn_type"] == "DEBIT"]
    by_merchant: dict[str, list[dict]] = defaultdict(list)
    for t in debits:
        by_merchant[_merchant_of(t)].append(t)

    recurring = []
    for merchant, txns in by_merchant.items():
        if len(txns) < 2:
            continue
        amounts = [t["amount"] for t in txns]
        if len({round(a, 0) for a in amounts}) <= 2:
            recurring.append(
                {
                    "merchant": merchant,
                    "amount": round(mean(amounts), 2),
                    "frequency": "monthly" if len(txns) >= 2 else "occasional",
                    "category": txns[-1]["category"],
                    "last_date": txns[-1]["transaction_timestamp"].strftime("%Y-%m-%d"),
                }
            )
    return sorted(recurring, key=lambda x: x["amount"], reverse=True)[:10]


def spending_calendar(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    days: dict[str, dict[str, float | int]] = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for t in transactions:
        if t["txn_type"] != "DEBIT":
            continue
        key = t["transaction_timestamp"].strftime("%Y-%m-%d")
        days[key]["amount"] += t["amount"]
        days[key]["count"] += 1
    return [
        {"date": k, "amount": round(v["amount"], 2), "count": int(v["count"])}
        for k, v in sorted(days.items())[-90:]
    ]


def detect_anomalies(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    debits = [t for t in transactions if t["txn_type"] == "DEBIT"]
    if len(debits) < 5:
        return []
    amounts = [t["amount"] for t in debits]
    avg = mean(amounts)
    sd = stdev(amounts) if len(amounts) > 1 else 0
    threshold = avg + (2 * sd if sd else avg)
    anomalies = []
    for t in debits:
        if t["amount"] > threshold:
            anomalies.append(
                {
                    "txn_id": t["txn_id"],
                    "narration": t["narration"],
                    "amount": t["amount"],
                    "reason": f"Amount exceeds typical spending by 2σ (avg ₹{avg:,.0f})",
                    "date": t["transaction_timestamp"].strftime("%Y-%m-%d"),
                }
            )
    return anomalies[:10]


def forecast_runway(transactions: list[dict[str, Any]], total_balance: float) -> list[dict[str, Any]]:
    monthly_expense: dict[str, float] = defaultdict(float)
    monthly_income: dict[str, float] = defaultdict(float)
    for t in transactions:
        key = _month_key(t["transaction_timestamp"])
        if t["txn_type"] == "DEBIT":
            monthly_expense[key] += t["amount"]
        else:
            monthly_income[key] += t["amount"]

    recent_exp = list(monthly_expense.values())[-3:] or [0]
    recent_inc = list(monthly_income.values())[-3:] or [0]
    avg_exp = mean(recent_exp) if recent_exp else 0
    avg_inc = mean(recent_inc) if recent_inc else 0
    runway = (total_balance / avg_exp) if avg_exp > 0 else None

    now = datetime.utcnow()
    points = []
    for i in range(1, 4):
        month = (now + timedelta(days=30 * i)).strftime("%Y-%m")
        points.append(
            {
                "month": month,
                "projected_expense": round(avg_exp * (1 + 0.02 * i), 2),
                "projected_income": round(avg_inc, 2),
                "runway_months": round(runway or 0, 1) if runway else None,
            }
        )
    return points
