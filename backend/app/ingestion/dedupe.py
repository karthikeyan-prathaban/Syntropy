import hashlib
import re
from datetime import datetime

# Reference numbers, UTRs and timestamps differ between the same transaction as
# reported by a PDF statement and by the AA feed, so they are stripped before hashing.
_DIGIT_RUN = re.compile(r"\d{6,}")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")
_WHITESPACE = re.compile(r"\s+")


def normalize_narration(narration: str) -> str:
    """Collapse a narration to the part that is stable across sources."""
    text = (narration or "").lower()
    text = _DIGIT_RUN.sub(" ", text)
    text = _NON_ALNUM.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    # Keep the leading tokens: the tail is usually bank-specific padding.
    return " ".join(text.split()[:8])


def compute_txn_hash(
    user_id: int,
    account_ref: str,
    timestamp: datetime,
    amount: float,
    txn_type: str,
    narration: str,
) -> str:
    """Deterministic fingerprint of a transaction.

    Date granularity (not time) is deliberate: statements carry a posting date only,
    while AA carries a full timestamp, and both describe the same event.
    """
    parts = [
        str(user_id),
        (account_ref or "").strip().lower(),
        timestamp.date().isoformat(),
        f"{round(float(amount), 2):.2f}",
        (txn_type or "").strip().upper(),
        normalize_narration(narration),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
