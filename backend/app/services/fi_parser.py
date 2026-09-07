from datetime import datetime
from typing import Any

from dateutil import parser as date_parser

from app.services.categorizer import classify


def _parse_ts(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    try:
        return date_parser.parse(value).replace(tzinfo=None)
    except (ValueError, TypeError):
        return datetime.utcnow()


def parse_deposit_fi_data(fi_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accounts: list[dict[str, Any]] = []
    transactions: list[dict[str, Any]] = []

    fips = fi_payload.get("fips") or []
    for fip in fips:
        fip_id = fip.get("fipID") or fip.get("fipId") or ""
        for account_block in fip.get("accounts") or []:
            deposit = account_block.get("deposit") or account_block.get("DEPOSIT") or account_block
            account = deposit.get("account") if isinstance(deposit, dict) else None
            if not account and isinstance(deposit, dict) and "maskedAccNumber" in deposit:
                account = deposit
            if not account:
                continue

            linked_ref = account.get("linkedAccRef") or account.get("linked_acc_ref") or ""
            masked = account.get("maskedAccNumber") or account.get("masked_acc_number") or "****"
            summary = account.get("summary") or {}
            balance = float(summary.get("currentBalance") or summary.get("current_balance") or 0)

            accounts.append({
                "linked_acc_ref": linked_ref,
                "masked_acc_number": masked,
                "account_type": account.get("type") or "DEPOSIT",
                "current_balance": balance,
                "currency": summary.get("currency") or "INR",
                "fip_id": fip_id,
            })

            txns_block = account.get("transactions") or {}
            for txn in txns_block.get("transaction") or []:
                amount = float(txn.get("amount") or 0)
                txn_type = (txn.get("type") or "DEBIT").upper()
                narration = txn.get("narration") or ""
                transactions.append({
                    "txn_id": txn.get("txnId") or txn.get("txn_id") or f"{linked_ref}-{txn.get('transactionTimestamp', '')}",
                    "linked_acc_ref": linked_ref,
                    "amount": amount,
                    "txn_type": txn_type,
                    "narration": narration,
                    "mode": txn.get("mode") or "",
                    "category": classify(narration, txn_type),
                    "transaction_timestamp": _parse_ts(txn.get("transactionTimestamp") or txn.get("transaction_timestamp")),
                    "balance_after": float(txn["currentBalance"]) if txn.get("currentBalance") else None,
                })

    return accounts, transactions
