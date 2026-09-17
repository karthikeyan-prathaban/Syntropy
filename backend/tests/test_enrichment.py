from datetime import datetime, timedelta

import pytest

from app.domain.models import Transaction
from app.enrichment.merchants import normalize_merchant
from app.enrichment.recurring import detect_recurring
from app.enrichment.transfers import detect_transfers


def _txn(
    amount: float,
    txn_type: str,
    narration: str,
    when: datetime,
    account_id: int = 1,
    merchant: str | None = None,
    txn_id: str | None = None,
) -> Transaction:
    return Transaction(
        id=abs(hash((narration, when, amount, account_id))) % 10**8,
        user_id=1,
        account_id=account_id,
        txn_id=txn_id or f"t{when.timestamp()}{amount}",
        txn_hash="h",
        amount=amount,
        txn_type=txn_type,
        narration=narration,
        raw_narration=narration,
        category="Other",
        merchant_name=merchant,
        transaction_timestamp=when,
        is_transfer=False,
    )


# --- merchant normalization ---------------------------------------------


@pytest.mark.parametrize(
    "narration,mode,expected",
    [
        ("UPI/512345678901/swiggy@icici/Payment to Swiggy", "UPI", "Swiggy"),
        ("UPI-ZOMATO-zomato@ybl-YESB0000001-998877665544", "UPI", "Zomato"),
        ("POS 4567XXXXXX1234 AMAZON PAY INDIA", "POS", "Amazon"),
        ("NEFT-AXISP00123456-ACME PRIVATE LIMITED", "NEFT", None),
        ("ACH D- HDFCBANK-NETFLIX ENTERTAINMENT", "ACH", "Netflix"),
        ("VPS/BLINKIT/blinkit@paytm/Groceries", "", "Blinkit"),
        ("POS/4567XX1234/STARBUCKS COFFEE KORAMANGALA", "POS", "Starbucks"),
        ("UPI/402938475612/UBER INDIA SYSTEMS/uber@axis", "UPI", "Uber"),
        ("BIL/ONL/000123/JIO RECHARGE", "", "Jio"),
    ],
)
def test_known_merchants_are_resolved(narration, mode, expected):
    match = normalize_merchant(narration, mode)
    if expected is None:
        # An unknown counterparty must still not return a bank code.
        assert match.display_name.upper() not in {"UPI", "NEFT", "POS", "ACH", "IMPS"}
        assert "AXISP" not in match.display_name.upper()
    else:
        assert match.display_name == expected


def test_ifsc_codes_are_never_mistaken_for_merchants():
    match = normalize_merchant("NEFT-HDFC0001234-ACME PRIVATE LIMITED", "NEFT")
    assert "HDFC0001234" not in match.display_name
    assert match.display_name


def test_long_reference_numbers_are_stripped():
    match = normalize_merchant("UPI/512345678901234/somebody@okaxis/Pay", "UPI")
    assert "512345678901234" not in match.display_name


def test_the_old_naive_split_would_have_returned_a_bank_code():
    """narration.split("/")[0] on this returns "UPI", which is the bug being fixed."""
    narration = "UPI/512345678901/swiggy@icici/Payment"
    assert narration.split("/")[0].split("-")[0] == "UPI"
    assert normalize_merchant(narration, "UPI").display_name == "Swiggy"


def test_empty_narration_is_handled():
    match = normalize_merchant("", "")
    assert match.display_name == "Unknown"
    assert match.confidence == 0.0


def test_vpa_is_captured():
    match = normalize_merchant("UPI/512345678901/swiggy@icici/Pay", "UPI")
    assert match.vpa == "swiggy@icici"


# --- transfer detection --------------------------------------------------


def test_matching_debit_and_credit_across_accounts_are_paired():
    when = datetime(2026, 3, 10, 9, 0)
    debit = _txn(25000.0, "DEBIT", "IMPS TO SELF ICICI", when, account_id=1)
    credit = _txn(25000.0, "CREDIT", "IMPS FROM SELF HDFC", when + timedelta(hours=2), account_id=2)

    marked = detect_transfers([debit, credit])

    assert marked == 2
    assert debit.is_transfer and credit.is_transfer
    assert debit.category == "Internal Transfer"


def test_same_account_movements_are_not_transfers():
    when = datetime(2026, 3, 10)
    debit = _txn(5000.0, "DEBIT", "Payment", when, account_id=1)
    credit = _txn(5000.0, "CREDIT", "Refund", when + timedelta(hours=1), account_id=1)

    assert detect_transfers([debit, credit]) == 0
    assert not debit.is_transfer


def test_transfers_outside_the_window_are_not_paired():
    when = datetime(2026, 3, 1)
    debit = _txn(25000.0, "DEBIT", "Send", when, account_id=1)
    credit = _txn(25000.0, "CREDIT", "Receive", when + timedelta(days=10), account_id=2)

    assert detect_transfers([debit, credit]) == 0


def test_different_amounts_are_not_paired():
    when = datetime(2026, 3, 1)
    debit = _txn(25000.0, "DEBIT", "Send", when, account_id=1)
    credit = _txn(24000.0, "CREDIT", "Receive", when + timedelta(days=1), account_id=2)

    assert detect_transfers([debit, credit]) == 0


def test_a_credit_is_claimed_by_only_one_debit():
    when = datetime(2026, 3, 1)
    debit_a = _txn(1000.0, "DEBIT", "Send A", when, account_id=1)
    debit_b = _txn(1000.0, "DEBIT", "Send B", when + timedelta(hours=1), account_id=1)
    credit = _txn(1000.0, "CREDIT", "Receive", when + timedelta(hours=2), account_id=2)

    assert detect_transfers([debit_a, debit_b, credit]) == 2
    assert debit_a.is_transfer
    assert not debit_b.is_transfer


def test_rerunning_clears_stale_pairings():
    when = datetime(2026, 3, 1)
    debit = _txn(1000.0, "DEBIT", "Send", when, account_id=1)
    credit = _txn(1000.0, "CREDIT", "Receive", when + timedelta(hours=1), account_id=2)
    detect_transfers([debit, credit])
    assert debit.is_transfer

    # The matching credit is gone on the second run, so the flag must clear.
    detect_transfers([debit])
    assert not debit.is_transfer


# --- recurring detection -------------------------------------------------


def _monthly(merchant: str, amount: float, count: int, jitter: float = 0.0) -> list[Transaction]:
    start = datetime(2026, 1, 5)
    return [
        _txn(
            amount + (jitter * i),
            "DEBIT",
            f"{merchant} subscription",
            start + timedelta(days=30 * i),
            merchant=merchant,
        )
        for i in range(count)
    ]


def test_a_monthly_subscription_is_detected_with_a_next_due_date():
    series = detect_recurring(_monthly("Netflix", 649.0, 5))
    assert len(series) == 1
    item = series[0]
    assert item.merchant_name == "Netflix"
    assert item.cadence == "monthly"
    assert item.expected_amount == 649.0
    assert item.next_due == item.last_seen + timedelta(days=30)
    assert item.confidence > 0.7


def test_two_occurrences_are_not_enough():
    """The old rule flagged any merchant with two similar amounts."""
    assert detect_recurring(_monthly("Netflix", 649.0, 2)) == []


def test_wildly_varying_amounts_are_not_recurring():
    txns = _monthly("Grocery", 1000.0, 5, jitter=800.0)
    assert detect_recurring(txns) == []


def test_weekly_and_annual_cadences_are_distinguished():
    weekly = [
        _txn(200.0, "DEBIT", "Gym", datetime(2026, 1, 5) + timedelta(days=7 * i), merchant="Gym")
        for i in range(6)
    ]
    annual = [
        _txn(1499.0, "DEBIT", "Domain", datetime(2022, 1, 5) + timedelta(days=365 * i), merchant="Domain")
        for i in range(4)
    ]
    assert detect_recurring(weekly)[0].cadence == "weekly"
    assert detect_recurring(annual)[0].cadence == "annual"


def test_irregular_intervals_are_rejected():
    dates = [0, 3, 40, 95, 100]
    txns = [
        _txn(500.0, "DEBIT", "Random", datetime(2026, 1, 1) + timedelta(days=d), merchant="Random")
        for d in dates
    ]
    assert detect_recurring(txns) == []


def test_transfers_are_excluded_from_recurring():
    txns = _monthly("Self", 25000.0, 5)
    for txn in txns:
        txn.is_transfer = True
    assert detect_recurring(txns) == []
