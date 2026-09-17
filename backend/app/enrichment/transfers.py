from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from app.domain.models import Transaction

# A debit settles into the paired account within a few days at most. The small
# negative allowance covers statements that post the credit on the value date.
MATCH_WINDOW = timedelta(days=3)
BACKDATE_ALLOWANCE = timedelta(days=1)
AMOUNT_TOLERANCE = 0.01


def detect_transfers(transactions: list[Transaction]) -> int:
    """Pair self-transfers across a user's own accounts and mark both sides.

    Without this, moving money between your own accounts counts as both income and
    expense, which is the single largest source of wrong totals in a multi-account PFM.
    Returns the number of transactions newly marked.
    """
    debits: list[Transaction] = []
    credits_by_amount: dict[float, list[Transaction]] = defaultdict(list)

    for txn in transactions:
        rounded = round(float(txn.amount), 2)
        if txn.txn_type.upper() == "DEBIT":
            debits.append(txn)
        else:
            credits_by_amount[rounded].append(txn)

    # Reset first so a re-run after new data does not leave stale pairings behind.
    for txn in transactions:
        txn.is_transfer = False
        txn.transfer_pair_id = None

    claimed: set[int] = set()
    marked = 0

    for debit in sorted(debits, key=lambda t: t.transaction_timestamp):
        amount = round(float(debit.amount), 2)
        best: Transaction | None = None
        best_gap: timedelta | None = None

        for tolerance_key in (amount, round(amount + AMOUNT_TOLERANCE, 2), round(amount - AMOUNT_TOLERANCE, 2)):
            for credit in credits_by_amount.get(tolerance_key, []):
                if id(credit) in claimed or credit.account_id == debit.account_id:
                    continue
                gap = credit.transaction_timestamp - debit.transaction_timestamp
                if -BACKDATE_ALLOWANCE <= gap <= MATCH_WINDOW and (
                    best_gap is None or abs(gap) < abs(best_gap)
                ):
                    best, best_gap = credit, gap

        if best is None:
            continue

        claimed.add(id(best))
        debit.is_transfer = True
        best.is_transfer = True
        debit.category = "Internal Transfer"
        best.category = "Internal Transfer"
        if debit.id and best.id:
            debit.transfer_pair_id = best.id
            best.transfer_pair_id = debit.id
        marked += 2

    return marked
