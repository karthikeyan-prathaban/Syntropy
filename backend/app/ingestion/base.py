from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class CanonicalAccount:
    """Bank account shape shared by every ingestion source."""

    linked_acc_ref: str
    masked_acc_number: str
    account_type: str = "SAVINGS"
    fi_type: str = "DEPOSIT"
    current_balance: float = 0.0
    currency: str = "INR"
    fip_id: str | None = None
    bank_name: str | None = None
    holder_name: str | None = None
    holdings: dict[str, Any] | None = None


@dataclass(slots=True)
class CanonicalTransaction:
    """Transaction shape shared by every ingestion source.

    `txn_hash` is filled by the dedupe layer, not by sources.
    """

    linked_acc_ref: str
    amount: float
    txn_type: str
    narration: str
    transaction_timestamp: datetime
    txn_id: str | None = None
    mode: str = ""
    balance_after: float | None = None
    reference: str | None = None


@dataclass(slots=True)
class IngestionResult:
    source: str
    accounts: list[CanonicalAccount] = field(default_factory=list)
    transactions: list[CanonicalTransaction] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class DataSource(Protocol):
    """Anything that can produce canonical accounts and transactions.

    AA is one implementation of this, not the foundation. Statement uploads are
    another. Adding a new source means adding a class here, nothing downstream.
    """

    name: str

    async def fetch(self, **kwargs: Any) -> IngestionResult:
        ...
