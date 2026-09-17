from __future__ import annotations

import hashlib
import re

from app.ingestion.base import CanonicalAccount, CanonicalTransaction, IngestionResult
from app.ingestion.parsers import ParsedStatement, parse_statement


def _account_ref(bank: str, account_number: str | None, filename: str) -> str:
    """Stable reference so repeated uploads for the same account reconcile.

    Falls back to a filename-derived key when the statement hides the account number,
    which keeps the upload usable without silently merging two different accounts.
    """
    if account_number:
        digits = re.sub(r"\D", "", account_number)
        if len(digits) >= 4:
            return f"{bank.lower()}-{digits[-4:]}"
    return f"{bank.lower()}-{hashlib.sha256(filename.encode()).hexdigest()[:8]}"


def to_ingestion_result(statement: ParsedStatement, filename: str) -> IngestionResult:
    ref = _account_ref(statement.bank, statement.account_number, filename)
    masked = statement.account_number or "****"
    if len(re.sub(r"\D", "", masked)) >= 4:
        masked = f"•••• {re.sub(r'[^0-9]', '', masked)[-4:]}"

    return IngestionResult(
        source="statement",
        accounts=[
            CanonicalAccount(
                linked_acc_ref=ref,
                masked_acc_number=masked,
                account_type="SAVINGS",
                fi_type="DEPOSIT",
                current_balance=statement.closing_balance or 0.0,
                bank_name=statement.bank,
                holder_name=statement.account_holder,
            )
        ],
        transactions=[
            CanonicalTransaction(
                linked_acc_ref=ref,
                amount=row.amount,
                txn_type=row.txn_type,
                narration=row.narration,
                transaction_timestamp=row.date,
                mode=row.mode,
                balance_after=row.balance,
                reference=row.reference,
            )
            for row in statement.rows
        ],
        meta={"bank": statement.bank, "rows": len(statement.rows), "filename": filename},
    )


class StatementDataSource:
    """Uploaded bank statements as an ingestion source."""

    name = "statement"

    async def fetch(
        self, data: bytes, filename: str, password: str | None = None, bank_hint: str | None = None
    ) -> IngestionResult:
        statement = parse_statement(data, filename, password, bank_hint)
        return to_ingestion_result(statement, filename)


statement_source = StatementDataSource()
