from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.ingestion.base import CanonicalAccount, CanonicalTransaction, IngestionResult
from app.services.fi_parser import parse_deposit_fi_data
from app.services.setu_client import setu_client

logger = logging.getLogger(__name__)


class AAError(RuntimeError):
    """Raised when the Setu AA session cannot deliver data."""


class AADataSource:
    """Setu Account Aggregator as one source behind the ingestion interface.

    The parsing logic is unchanged from services/fi_parser.py; this only adapts the
    output into the canonical shape so AA and statement uploads share a code path.
    """

    name = "aa"

    def __init__(self, poll_attempts: int = 15, poll_interval: float = 2.0) -> None:
        self.poll_attempts = poll_attempts
        self.poll_interval = poll_interval

    async def fetch(self, consent_id: str, **_: Any) -> IngestionResult:
        session = await setu_client.create_fi_session(consent_id)
        session_id = session.get("id") or session.get("sessionId")
        if not session_id:
            raise AAError("Setu did not return an FI session id")

        fi_data: dict[str, Any] = {}
        for _attempt in range(self.poll_attempts):
            fi_data = await setu_client.get_fi_session(session_id)
            status = fi_data.get("status")
            if status in {"COMPLETED", "PARTIAL"}:
                break
            if status in {"FAILED", "EXPIRED", "REJECTED"}:
                raise AAError(f"FI session ended with status {status}")
            await asyncio.sleep(self.poll_interval)
        else:
            raise AAError("FI session did not complete within the polling window")

        raw_accounts, raw_txns = parse_deposit_fi_data(fi_data)
        return IngestionResult(
            source=self.name,
            accounts=[
                CanonicalAccount(
                    linked_acc_ref=a["linked_acc_ref"],
                    masked_acc_number=a["masked_acc_number"],
                    account_type=a.get("account_type") or "SAVINGS",
                    fi_type="DEPOSIT",
                    current_balance=a.get("current_balance", 0.0),
                    currency=a.get("currency") or "INR",
                    fip_id=a.get("fip_id"),
                )
                for a in raw_accounts
            ],
            transactions=[
                CanonicalTransaction(
                    linked_acc_ref=t["linked_acc_ref"],
                    amount=t["amount"],
                    txn_type=t["txn_type"],
                    narration=t["narration"],
                    transaction_timestamp=t["transaction_timestamp"],
                    txn_id=t.get("txn_id"),
                    mode=t.get("mode") or "",
                    balance_after=t.get("balance_after"),
                )
                for t in raw_txns
            ],
            meta={"session_id": session_id, "session_status": fi_data.get("status")},
        )


aa_source = AADataSource()
