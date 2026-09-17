from __future__ import annotations

import re

from app.ingestion.parsers.base import (
    ParsedStatement,
    ParseError,
    StatementRow,
    clean_text,
    find_column,
    infer_mode,
    normalize_header,
    parse_amount,
    parse_date,
)
from app.ingestion.parsers.extract import Table, extract

ACCOUNT_PATTERNS = [
    re.compile(r"account\s*(?:no|number|#)?\s*[:\-]?\s*([X\*x\d]{6,20})", re.I),
    re.compile(r"a/?c\s*(?:no|number)?\s*[:\-]?\s*([X\*x\d]{6,20})", re.I),
]
HOLDER_PATTERNS = [
    re.compile(r"(?:account\s*name|customer\s*name|name)\s*[:\-]\s*([A-Z][A-Za-z .]{3,50})"),
]


class TabularParser:
    """Shared engine for statements that resolve to a header row plus data rows.

    Each bank subclass supplies detection tokens and its column aliases; the row
    mechanics — header discovery, debit/credit vs signed amount, multi-line
    narration continuation — are identical across banks.
    """

    bank = "generic"
    display_name = "Generic"
    detect_tokens: tuple[str, ...] = ()

    date_aliases: tuple[str, ...] = ("date", "txndate", "transactiondate", "valuedate", "postingdate", "tran date")
    narration_aliases: tuple[str, ...] = (
        "narration", "particulars", "description", "transactionremarks", "remarks",
        "transactiondetails", "details", "narrative",
    )
    debit_aliases: tuple[str, ...] = ("withdrawalamt", "withdrawal", "debit", "debitamount", "withdrawals", "dr")
    credit_aliases: tuple[str, ...] = ("depositamt", "deposit", "credit", "creditamount", "deposits", "cr")
    amount_aliases: tuple[str, ...] = ("amount", "txnamount", "transactionamount")
    type_aliases: tuple[str, ...] = ("type", "drcr", "crdr", "transactiontype", "debitcredit")
    balance_aliases: tuple[str, ...] = ("closingbalance", "balance", "runningbalance", "balanceamt", "availablebalance")
    reference_aliases: tuple[str, ...] = ("chqrefno", "refno", "referencenumber", "chequeno", "utrno", "refchequeno")

    @classmethod
    def matches(cls, text: str) -> int:
        """Confidence score from 0. Higher wins during auto-detection."""
        haystack = text.lower()
        return sum(3 for token in cls.detect_tokens if token.lower() in haystack)

    # --- header discovery -------------------------------------------------
    def locate_header(self, table: Table) -> int | None:
        for idx, row in enumerate(table[:25]):
            normalized = {normalize_header(cell) for cell in row if cell}
            has_date = any(normalize_header(a) in normalized for a in self.date_aliases) or any(
                "date" in cell for cell in normalized
            )
            has_narration = any(
                normalize_header(a) in cell for a in self.narration_aliases for cell in normalized if cell
            )
            has_money = any(
                normalize_header(a) in cell
                for a in (*self.debit_aliases, *self.credit_aliases, *self.amount_aliases, *self.balance_aliases)
                for cell in normalized
                if cell
            )
            if has_date and has_narration and has_money:
                return idx
        return None

    def _pick_table(self, tables: list[Table]) -> tuple[Table, int]:
        best: tuple[Table, int] | None = None
        for table in tables:
            header_idx = self.locate_header(table)
            if header_idx is None:
                continue
            data_rows = len(table) - header_idx - 1
            if best is None or data_rows > len(best[0]) - best[1] - 1:
                best = (table, header_idx)
        if best is None:
            raise ParseError(
                "Could not find a transaction table. Upload the bank's original "
                "statement export rather than a screenshot or edited copy."
            )
        return best

    # --- row building -----------------------------------------------------
    def _row_to_txn(self, cells: list[str], cols: dict[str, int | None]) -> StatementRow | None:
        def cell(name: str) -> str:
            idx = cols.get(name)
            return clean_text(cells[idx]) if idx is not None and idx < len(cells) else ""

        when = parse_date(cell("date"))
        if when is None:
            return None

        narration = cell("narration")
        debit = parse_amount(cell("debit")) if cols.get("debit") is not None else None
        credit = parse_amount(cell("credit")) if cols.get("credit") is not None else None

        if debit or credit:
            amount = debit or credit or 0.0
            txn_type = "DEBIT" if debit else "CREDIT"
        else:
            raw = parse_amount(cell("amount"))
            if raw is None or raw == 0:
                return None
            marker = cell("type").strip().upper()
            if marker.startswith("D") or marker in {"DR", "DEBIT", "W"}:
                txn_type = "DEBIT"
            elif marker.startswith("C") or marker in {"CR", "CREDIT", "D"}:
                txn_type = "CREDIT"
            else:
                # No explicit marker: a signed amount carries the direction.
                txn_type = "DEBIT" if raw < 0 else "CREDIT"
            amount = abs(raw)

        if not narration:
            narration = cell("reference") or "Transaction"

        return StatementRow(
            date=when,
            narration=narration,
            amount=abs(amount),
            txn_type=txn_type,
            balance=parse_amount(cell("balance")),
            reference=cell("reference") or None,
            mode=infer_mode(narration),
        )

    def _metadata(self, statement: ParsedStatement, text: str) -> None:
        for pattern in ACCOUNT_PATTERNS:
            match = pattern.search(text)
            if match:
                statement.account_number = match.group(1).strip()
                break
        for pattern in HOLDER_PATTERNS:
            match = pattern.search(text)
            if match:
                statement.account_holder = match.group(1).strip()
                break

    def parse(self, data: bytes, filename: str, password: str | None = None) -> ParsedStatement:
        tables, text = extract(data, filename, password)
        table, header_idx = self._pick_table(tables)
        headers = table[header_idx]

        cols: dict[str, int | None] = {
            "date": find_column(headers, self.date_aliases),
            "narration": find_column(headers, self.narration_aliases),
            "debit": find_column(headers, self.debit_aliases),
            "credit": find_column(headers, self.credit_aliases),
            "amount": find_column(headers, self.amount_aliases),
            "type": find_column(headers, self.type_aliases),
            "balance": find_column(headers, self.balance_aliases),
            "reference": find_column(headers, self.reference_aliases),
        }
        # A single "Amount" column must not be mistaken for the debit column.
        if cols["debit"] is not None and cols["debit"] == cols["credit"]:
            cols["debit"] = cols["credit"] = None

        statement = ParsedStatement(bank=self.bank)
        self._metadata(statement, text)

        for cells in table[header_idx + 1 :]:
            if not any(clean_text(c) for c in cells):
                continue
            row = self._row_to_txn(list(cells), cols)
            if row is not None:
                statement.rows.append(row)
                continue
            # PDF extraction splits long narrations across lines; stitch them back on.
            if statement.rows:
                trailing = " ".join(clean_text(c) for c in cells if clean_text(c))
                if trailing and not parse_amount(trailing):
                    statement.rows[-1].narration = f"{statement.rows[-1].narration} {trailing}".strip()

        if not statement.rows:
            raise ParseError("No transactions could be read from this statement")

        statement.rows.sort(key=lambda r: r.date)
        statement.closing_balance = next(
            (r.balance for r in reversed(statement.rows) if r.balance is not None), None
        )
        return statement
