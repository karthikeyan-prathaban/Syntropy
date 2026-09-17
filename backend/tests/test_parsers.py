from pathlib import Path

import pytest

from app.ingestion.parsers import ParseError, detect_bank, parse_statement
from app.ingestion.parsers.base import parse_amount, parse_date
from app.ingestion.statement_source import to_ingestion_result

FIXTURES = Path(__file__).parent / "fixtures" / "statements"

CASES = [
    ("hdfc_sample.csv", "HDFC", 6),
    ("icici_sample.csv", "ICICI", 5),
    ("sbi_sample.csv", "SBI", 4),
    ("axis_sample.csv", "AXIS", 4),
    ("kotak_sample.csv", "KOTAK", 4),
]


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.mark.parametrize("filename,expected_bank,_rows", CASES)
def test_bank_is_detected_from_the_document(filename, expected_bank, _rows):
    assert detect_bank(_load(filename), filename).bank == expected_bank


@pytest.mark.parametrize("filename,expected_bank,expected_rows", CASES)
def test_every_row_is_parsed(filename, expected_bank, expected_rows):
    statement = parse_statement(_load(filename), filename)
    assert statement.bank == expected_bank
    assert len(statement.rows) == expected_rows
    assert all(row.amount > 0 for row in statement.rows)
    assert all(row.txn_type in {"DEBIT", "CREDIT"} for row in statement.rows)
    # Rows come back in chronological order regardless of the file's ordering.
    assert statement.rows == sorted(statement.rows, key=lambda r: r.date)


def test_hdfc_directions_and_amounts():
    statement = parse_statement(_load("hdfc_sample.csv"), "hdfc_sample.csv")
    swiggy = statement.rows[0]
    assert swiggy.txn_type == "DEBIT"
    assert swiggy.amount == 348.00
    assert swiggy.mode == "UPI"

    salary = next(r for r in statement.rows if r.txn_type == "CREDIT")
    assert salary.amount == 125000.0
    assert "ACME" in salary.narration


def test_lakh_grouping_is_handled():
    statement = parse_statement(_load("kotak_sample.csv"), "kotak_sample.csv")
    salary = next(r for r in statement.rows if r.txn_type == "CREDIT")
    assert salary.amount == 95000.0


def test_kotak_uses_the_dr_cr_marker_column():
    statement = parse_statement(_load("kotak_sample.csv"), "kotak_sample.csv")
    assert [r.txn_type for r in statement.rows] == ["DEBIT", "CREDIT", "DEBIT", "DEBIT"]


def test_generic_fallback_reads_signed_amounts_and_semicolons():
    statement = parse_statement(_load("generic_sample.csv"), "generic_sample.csv")
    assert len(statement.rows) == 3
    assert [r.txn_type for r in statement.rows] == ["DEBIT", "CREDIT", "DEBIT"]
    assert statement.rows[2].amount == 25000.0


def test_account_number_is_extracted():
    statement = parse_statement(_load("icici_sample.csv"), "icici_sample.csv")
    assert statement.account_number is not None
    assert "1234567890" in statement.account_number


def test_unparseable_content_raises_a_useful_error():
    with pytest.raises(ParseError):
        parse_statement(b"this is not a statement at all", "junk.csv")


def test_parsed_statement_maps_to_canonical_shape():
    statement = parse_statement(_load("hdfc_sample.csv"), "hdfc_sample.csv")
    result = to_ingestion_result(statement, "hdfc_sample.csv")
    assert result.source == "statement"
    assert len(result.accounts) == 1
    assert len(result.transactions) == len(statement.rows)
    assert result.accounts[0].linked_acc_ref.startswith("hdfc-")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1,299.00", 1299.0),
        ("1,25,000.50", 125000.50),
        ("(450.00)", -450.0),
        ("450.00 Dr", -450.0),
        ("450.00 Cr", 450.0),
        ("", None),
        ("-", None),
        ("abc", None),
    ],
)
def test_amount_parsing(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    "raw,iso",
    [
        ("01/03/2026", "2026-03-01"),
        ("01-03-26", "2026-03-01"),
        ("02 Mar 2026", "2026-03-02"),
        ("2026-03-05", "2026-03-05"),
        ("05.03.2026", "2026-03-05"),
    ],
)
def test_date_parsing_across_indian_formats(raw, iso):
    parsed = parse_date(raw)
    assert parsed is not None
    assert parsed.date().isoformat() == iso


def test_unknown_date_returns_none_rather_than_guessing():
    assert parse_date("not a date") is None
