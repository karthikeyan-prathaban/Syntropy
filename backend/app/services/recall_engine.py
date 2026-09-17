import asyncio
from collections import defaultdict
from typing import Any, AsyncGenerator


def _search_transactions(query: str, transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q = query.lower()
    results = []
    for t in transactions:
        haystack = f"{t['narration']} {t['category']} {t['txn_type']}".lower()
        if any(word in haystack for word in q.split() if len(word) > 2):
            results.append(t)
    return results[:20]


async def stream_recall_answer(query: str, transactions: list[dict[str, Any]], insights: dict[str, Any]) -> AsyncGenerator[str, None]:
    matches = _search_transactions(query, transactions)
    q = query.lower()

    if "spend" in q or "expense" in q or "how much" in q:
        total = sum(t["amount"] for t in matches if t["txn_type"] == "DEBIT") if matches else insights.get("total_expense", 0)
        answer = f"You spent ₹{total:,.0f} matching your query. "
    elif "save" in q or "savings" in q:
        answer = f"Your savings rate is {insights.get('savings_rate', 0)}%. "
    elif "category" in q or "top" in q:
        cats = insights.get("category_breakdown", [])
        top = cats[0]["category"] if cats else "N/A"
        answer = f"Your top spending category is {top}. "
    elif matches:
        answer = f"Found {len(matches)} transactions. Most recent: {matches[0]['narration']} for ₹{matches[0]['amount']:,.0f}. "
    else:
        answer = "I searched your linked accounts. "

    if matches:
        by_cat: dict[str, float] = defaultdict(float)
        for t in matches:
            if t["txn_type"] == "DEBIT":
                by_cat[t["category"]] += t["amount"]
        if by_cat:
            top_cat = max(by_cat, key=by_cat.get)
            answer += f"Most of this was in {top_cat} (₹{by_cat[top_cat]:,.0f}). "
    else:
        answer += "Try linking a bank account or broadening your search terms."

    for word in answer.split(" "):
        yield word + " "
        await asyncio.sleep(0.025)
