from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.domain.models import BankAccount, Transaction, User
from app.ingestion.base import CanonicalAccount, CanonicalTransaction, IngestionResult
from app.ingestion.dedupe import compute_txn_hash, normalize_narration
from app.ingestion.upsert import ingest

BASE = datetime(2026, 3, 1, 10, 30)


def _result(source: str, count: int = 3, balance: float = 50000.0) -> IngestionResult:
    return IngestionResult(
        source=source,
        accounts=[
            CanonicalAccount(
                linked_acc_ref="hdfc-1234",
                masked_acc_number="•••• 1234",
                current_balance=balance,
            )
        ],
        transactions=[
            CanonicalTransaction(
                linked_acc_ref="hdfc-1234",
                amount=100.0 * (i + 1),
                txn_type="DEBIT",
                narration=f"UPI/5123456789{i}/swiggy@icici/Payment",
                transaction_timestamp=BASE + timedelta(days=i),
            )
            for i in range(count)
        ],
    )


async def _user(db) -> User:
    user = User(name="Ingest", mobile_enc="", email_enc="", vua_enc="")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def test_ingest_inserts_transactions(db):
    user = await _user(db)
    run = await ingest(db, user.id, _result("statement"))
    assert run.rows_in == 3
    assert run.rows_new == 3
    assert run.rows_duplicate == 0

    count = await db.scalar(select(func.count()).select_from(Transaction))
    assert count == 3


async def test_reingesting_the_same_data_adds_nothing(db):
    user = await _user(db)
    await ingest(db, user.id, _result("statement"))
    second = await ingest(db, user.id, _result("statement"))

    assert second.rows_new == 0
    assert second.rows_duplicate == 3
    assert await db.scalar(select(func.count()).select_from(Transaction)) == 3


async def test_same_transaction_from_statement_and_aa_collapses(db):
    """The whole point of the hash: two sources describing one event, one row."""
    user = await _user(db)
    await ingest(db, user.id, _result("statement"))
    aa_run = await ingest(db, user.id, _result("aa"))

    assert aa_run.rows_new == 0
    assert await db.scalar(select(func.count()).select_from(Transaction)) == 3


async def test_accounts_are_updated_not_recreated(db):
    user = await _user(db)
    await ingest(db, user.id, _result("statement", balance=50000.0))
    await ingest(db, user.id, _result("statement", count=4, balance=61000.0))

    accounts = (await db.execute(select(BankAccount))).scalars().all()
    assert len(accounts) == 1
    assert accounts[0].current_balance == 61000.0


async def test_refetch_never_destroys_history(db):
    """The old consent fetch deleted all accounts and transactions first."""
    user = await _user(db)
    await ingest(db, user.id, _result("aa", count=5))

    # A later fetch returns a shorter window, as AA commonly does.
    partial = _result("aa", count=2)
    await ingest(db, user.id, partial)

    assert await db.scalar(select(func.count()).select_from(Transaction)) == 5


async def test_duplicates_within_one_batch_are_collapsed(db):
    user = await _user(db)
    result = _result("statement", count=1)
    result.transactions.append(result.transactions[0])
    run = await ingest(db, user.id, result)
    assert run.rows_new == 1


def test_hash_ignores_reference_numbers_that_differ_between_sources():
    a = compute_txn_hash(1, "acc", BASE, 250.0, "DEBIT", "UPI/402938475612/swiggy@icici/Food")
    b = compute_txn_hash(1, "acc", BASE, 250.0, "DEBIT", "UPI/998877665544/swiggy@icici/Food")
    assert a == b


def test_hash_ignores_time_of_day_but_not_the_date():
    same_day = compute_txn_hash(1, "acc", BASE, 250.0, "DEBIT", "Coffee")
    later = compute_txn_hash(1, "acc", BASE + timedelta(hours=6), 250.0, "DEBIT", "Coffee")
    next_day = compute_txn_hash(1, "acc", BASE + timedelta(days=1), 250.0, "DEBIT", "Coffee")
    assert same_day == later
    assert same_day != next_day


def test_hash_separates_users_amounts_and_directions():
    base = compute_txn_hash(1, "acc", BASE, 250.0, "DEBIT", "Coffee")
    assert base != compute_txn_hash(2, "acc", BASE, 250.0, "DEBIT", "Coffee")
    assert base != compute_txn_hash(1, "acc", BASE, 251.0, "DEBIT", "Coffee")
    assert base != compute_txn_hash(1, "acc", BASE, 250.0, "CREDIT", "Coffee")
    assert base != compute_txn_hash(1, "other", BASE, 250.0, "DEBIT", "Coffee")


def test_narration_normalization_strips_noise():
    assert normalize_narration("UPI/512345678901/SWIGGY@ICICI/Pay") == "upi swiggy icici pay"
    assert normalize_narration("") == ""
