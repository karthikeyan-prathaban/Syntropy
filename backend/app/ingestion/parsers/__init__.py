from __future__ import annotations

import logging

from app.ingestion.parsers.banks import BANK_PARSERS, GenericCSVParser
from app.ingestion.parsers.base import ParsedStatement, ParseError, StatementRow
from app.ingestion.parsers.extract import extract
from app.ingestion.parsers.tabular import TabularParser

logger = logging.getLogger(__name__)

ALL_PARSERS: list[type[TabularParser]] = [*BANK_PARSERS, GenericCSVParser]


def detect_bank(data: bytes, filename: str, password: str | None = None) -> type[TabularParser]:
    """Pick a parser from the document's own text plus the filename.

    Also confirms the file actually contains a transaction table, so an unusable
    upload is rejected at the API instead of failing later inside a worker.
    """
    try:
        tables, text = extract(data, filename, password)
    except ParseError:
        raise
    except Exception as exc:
        raise ParseError(f"Could not read this file: {exc}") from exc

    haystack = f"{filename}\n{text}"
    scored = sorted(ALL_PARSERS, key=lambda p: p.matches(haystack), reverse=True)

    for parser_cls in scored:
        probe = parser_cls()
        if any(probe.locate_header(table) is not None for table in tables):
            return parser_cls

    raise ParseError(
        "No transaction table was found. Upload the bank's original statement "
        "export rather than a screenshot or edited copy."
    )


def parse_statement(
    data: bytes, filename: str, password: str | None = None, bank_hint: str | None = None
) -> ParsedStatement:
    """Parse a statement, preferring the detected bank and falling back to generic."""
    candidates: list[type[TabularParser]] = []
    if bank_hint:
        hint = bank_hint.strip().upper()
        candidates += [p for p in ALL_PARSERS if p.bank == hint]
    detected = detect_bank(data, filename, password)
    if detected not in candidates:
        candidates.append(detected)
    if GenericCSVParser not in candidates:
        candidates.append(GenericCSVParser)

    last_error: Exception | None = None
    for parser_cls in candidates:
        try:
            statement = parser_cls().parse(data, filename, password)
            if statement.rows:
                return statement
        except ParseError as exc:
            last_error = exc
            logger.debug("%s parser rejected %s: %s", parser_cls.bank, filename, exc)
        except Exception as exc:
            last_error = exc
            logger.warning("%s parser crashed on %s: %s", parser_cls.bank, filename, exc)

    raise ParseError(str(last_error) if last_error else "Unsupported statement format")


__all__ = [
    "ALL_PARSERS",
    "ParseError",
    "ParsedStatement",
    "StatementRow",
    "TabularParser",
    "detect_bank",
    "parse_statement",
]
