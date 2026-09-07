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
            if not isinstance(account_block, dict):
                continue

            # Check all possible Setu nesting structures
            data_field = account_block.get("data") or {}
            deposit = account_block.get("deposit") or account_block.get("DEPOSIT") or data_field.get("deposit") or data_field.get("DEPOSIT") or data_field or account_block
            account = deposit.get("account") if isinstance(deposit, dict) else None
            if not account and isinstance(data_field, dict) and "account" in data_field:
                account = data_field.get("account")
            if not account and isinstance(deposit, dict) and ("maskedAccNumber" in deposit or "masked_acc_number" in deposit):
                account = deposit
            if not account and isinstance(account_block, dict) and ("maskedAccNumber" in account_block or "linkRefNumber" in account_block):
                account = account_block

            if not account or not isinstance(account, dict):
                continue

            linked_ref = (
                account.get("linkedAccRef")
                or account.get("linked_acc_ref")
                or account_block.get("linkRefNumber")
                or account_block.get("linkedAccRef")
                or f"acc_{len(accounts)+1}"
            )
            masked = (
                account.get("maskedAccNumber")
                or account.get("masked_acc_number")
                or account_block.get("maskedAccNumber")
                or "****"
            )
            summary = account.get("summary") or account_block.get("summary") or {}
            balance_raw = summary.get("currentBalance") or summary.get("current_balance") or account.get("balance") or 0
            try:
                balance = float(balance_raw)
            except (ValueError, TypeError):
                balance = 0.0

            accounts.append({
                "linked_acc_ref": linked_ref,
                "masked_acc_number": masked,
                "account_type": account.get("type") or "DEPOSIT",
                "current_balance": balance,
                "currency": summary.get("currency") or "INR",
                "fip_id": fip_id,
            })

            txns_block = account.get("transactions") or account_block.get("transactions") or {}
            txns_list = []
            if isinstance(txns_block, dict):
                txns_list = txns_block.get("transaction") or txns_block.get("transactions") or []
            elif isinstance(txns_block, list):
                txns_list = txns_block

            for txn in txns_list:
                if not isinstance(txn, dict):
                    continue
                try:
                    amount = float(txn.get("amount") or 0)
                except (ValueError, TypeError):
                    amount = 0.0

                txn_type = str(txn.get("type") or txn.get("txnType") or "DEBIT").upper()
                narration = str(txn.get("narration") or txn.get("description") or "")
                bal_after = txn.get("currentBalance") or txn.get("balanceAfter") or txn.get("balance")
                try:
                    bal_after_float = float(bal_after) if bal_after is not None else None
                except (ValueError, TypeError):
                    bal_after_float = None

                transactions.append({
                    "txn_id": txn.get("txnId") or txn.get("txn_id") or txn.get("id") or f"{linked_ref}-{txn.get('transactionTimestamp', '')}-{len(transactions)}",
                    "linked_acc_ref": linked_ref,
                    "amount": amount,
                    "txn_type": txn_type,
                    "narration": narration,
                    "mode": txn.get("mode") or "",
                    "category": classify(narration, txn_type),
                    "transaction_timestamp": _parse_ts(txn.get("transactionTimestamp") or txn.get("transaction_timestamp") or txn.get("timestamp")),
                    "balance_after": bal_after_float,
                })

    return accounts, transactions
