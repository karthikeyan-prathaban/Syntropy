from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

DATE_FORMATS = (
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %b, %Y",
    "%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y", "%d.%m.%y",
)

_AMOUNT_CLEAN = re.compile(r"[^\d.\-]")
_MULTISPACE = re.compile(r"\s+")


class ParseError(Exception):
    """Raised when a file cannot be parsed as a statement."""


@dataclass(slots=True)
class StatementRow:
    date: datetime
    narration: str
    amount: float
    txn_type: str
    balance: float | None = None
    reference: str | None = None
    mode: str = ""


@dataclass(slots=True)
class ParsedStatement:
    bank: str
    rows: list[StatementRow] = field(default_factory=list)
    account_number: str | None = None
    account_holder: str | None = None
    closing_balance: float | None = None
    warnings: list[str] = field(default_factory=list)


def parse_date(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    text = _MULTISPACE.sub(" ", str(value).replace("\n", " ")).strip()
    # Some statements append a posting time or value date to the same cell.
    candidates = [text, text.split(" ")[0]]
    for candidate in candidates:
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    return None


def parse_amount(value: str | float | int | None) -> float | None:
    """Indian statements use lakh grouping, trailing Cr/Dr, and (1,234.00) for negatives."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"-", "--", "NA", "N/A"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    suffix = text.upper().replace(".", "").strip()
    if suffix.endswith("CR"):
        text = text[:-2]
    elif suffix.endswith("DR"):
        text = text[:-2]
        negative = True
    cleaned = _AMOUNT_CLEAN.sub("", text)
    if not cleaned or cleaned in {"-", "."}:
        return None
    try:
        amount = float(cleaned)
    except ValueError:
        return None
    return -amount if negative and amount > 0 else amount


def clean_text(value: object) -> str:
    return _MULTISPACE.sub(" ", str(value or "").replace("\n", " ")).strip()


def normalize_header(value: object) -> str:
    return re.sub(r"[^a-z]", "", str(value or "").lower())


def find_column(headers: Sequence[str], aliases: Iterable[str]) -> int | None:
    """Match a logical column to a physical one, exact first then by containment."""
    normalized = [normalize_header(h) for h in headers]
    wanted = [normalize_header(a) for a in aliases]
    for target in wanted:
        if target in normalized:
            return normalized.index(target)
    for target in wanted:
        for idx, header in enumerate(normalized):
            if target and header and (target in header or header in target):
                return idx
    return None


def infer_mode(narration: str) -> str:
    text = (narration or "").upper()
    for token, mode in (
        ("UPI", "UPI"), ("IMPS", "IMPS"), ("NEFT", "NEFT"), ("RTGS", "RTGS"),
        ("POS", "CARD"), ("ATM", "ATM"), ("ACH", "ACH"), ("NACH", "ACH"),
        ("ECS", "ACH"), ("CHQ", "CHEQUE"), ("CHEQUE", "CHEQUE"), ("EMI", "ACH"),
    ):
        if token in text:
            return mode
    return "OTHERS"
