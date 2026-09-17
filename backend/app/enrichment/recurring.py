from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median, pstdev

from app.domain.models import Transaction

# (label, expected days, tolerance in days)
CADENCE_BANDS: list[tuple[str, float, float]] = [
    ("weekly", 7, 2),
    ("fortnightly", 14, 3),
    ("monthly", 30.4, 6),
    ("quarterly", 91.3, 12),
    ("annual", 365, 30),
]

MIN_OCCURRENCES = 3
MAX_AMOUNT_CV = 0.15


@dataclass(slots=True)
class DetectedSeries:
    merchant_name: str
    category: str
    cadence: str
    interval_days: float
    expected_amount: float
    amount_variation: float
    occurrences: int
    confidence: float
    direction: str
    first_seen: date
    last_seen: date
    next_due: date | None


def _classify_cadence(interval: float) -> tuple[str, float] | None:
    for label, expected, tolerance in CADENCE_BANDS:
        if abs(interval - expected) <= tolerance:
            # Closer to the band centre means higher confidence.
            return label, 1.0 - (abs(interval - expected) / (tolerance * 2))
    return None


def detect_recurring(transactions: list[Transaction]) -> list[DetectedSeries]:
    """Find genuine recurring charges.

    A series qualifies only when the median gap between consecutive charges lands in a
    known cadence band, the amount's coefficient of variation stays under 0.15, and
    there are at least three occurrences. The old rule flagged any merchant with two
    similar amounts and hardcoded the cadence as "monthly".
    """
    grouped: dict[tuple[str, str], list[Transaction]] = defaultdict(list)
    for txn in transactions:
        if txn.is_transfer:
            continue
        name = txn.merchant_name or "Unknown"
        if name == "Unknown":
            continue
        grouped[(name, txn.txn_type.upper())].append(txn)

    series: list[DetectedSeries] = []
    for (merchant, direction), txns in grouped.items():
        if len(txns) < MIN_OCCURRENCES:
            continue
        txns.sort(key=lambda t: t.transaction_timestamp)

        dates = [t.transaction_timestamp.date() for t in txns]
        intervals = [(b - a).days for a, b in zip(dates, dates[1:], strict=False) if (b - a).days > 0]
        if len(intervals) < MIN_OCCURRENCES - 1:
            continue

        median_interval = float(median(intervals))
        cadence = _classify_cadence(median_interval)
        if cadence is None:
            continue
        label, cadence_confidence = cadence

        amounts = [abs(float(t.amount)) for t in txns]
        mean_amount = sum(amounts) / len(amounts)
        if mean_amount <= 0:
            continue
        cv = pstdev(amounts) / mean_amount if len(amounts) > 1 else 0.0
        if cv > MAX_AMOUNT_CV:
            continue

        # Regular intervals matter as much as a regular amount.
        interval_spread = pstdev(intervals) / median_interval if len(intervals) > 1 else 0.0
        confidence = round(
            max(
                0.0,
                min(
                    1.0,
                    0.45 * cadence_confidence
                    + 0.3 * (1 - min(cv / MAX_AMOUNT_CV, 1))
                    + 0.25 * (1 - min(interval_spread, 1)),
                ),
            ),
            2,
        )

        series.append(
            DetectedSeries(
                merchant_name=merchant,
                category=txns[-1].category,
                cadence=label,
                interval_days=round(median_interval, 1),
                expected_amount=round(median(amounts), 2),
                amount_variation=round(cv, 3),
                occurrences=len(txns),
                confidence=confidence,
                direction=direction,
                first_seen=dates[0],
                last_seen=dates[-1],
                next_due=dates[-1] + timedelta(days=round(median_interval)),
            )
        )

    return sorted(series, key=lambda s: s.expected_amount, reverse=True)
