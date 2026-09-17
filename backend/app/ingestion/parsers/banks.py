"""Per-bank statement parsers.

Each subclass only declares what is genuinely bank-specific: the tokens that
identify the issuer and the column headings that bank uses. Everything else is
inherited from TabularParser.
"""

from app.ingestion.parsers.tabular import TabularParser


class HDFCParser(TabularParser):
    bank = "HDFC"
    display_name = "HDFC Bank"
    detect_tokens = ("hdfc bank", "hdfcbank", "hdfc0", "we understand your world")

    date_aliases = ("date", "txn date", "transaction date", "value dt", "value date")
    narration_aliases = ("narration", "description", "particulars")
    debit_aliases = ("withdrawal amt.", "withdrawal amt", "withdrawalamt", "debit amount", "debit")
    credit_aliases = ("deposit amt.", "deposit amt", "depositamt", "credit amount", "credit")
    balance_aliases = ("closing balance", "balance")
    reference_aliases = ("chq./ref.no.", "chq/ref no", "ref no", "chq no")


class ICICIParser(TabularParser):
    bank = "ICICI"
    display_name = "ICICI Bank"
    detect_tokens = ("icici bank", "icicibank", "icic0")

    date_aliases = ("transaction date", "txn date", "value date", "tran date", "date")
    narration_aliases = ("transaction remarks", "remarks", "particulars", "description")
    debit_aliases = ("withdrawal amount (inr )", "withdrawal amount", "withdrawal amt", "debit")
    credit_aliases = ("deposit amount (inr )", "deposit amount", "deposit amt", "credit")
    balance_aliases = ("balance (inr )", "balance", "available balance")
    reference_aliases = ("cheque number", "chequeno", "ref no", "s no")


class SBIParser(TabularParser):
    bank = "SBI"
    display_name = "State Bank of India"
    detect_tokens = ("state bank of india", "sbi", "onlinesbi", "sbin0")

    date_aliases = ("txn date", "transaction date", "value date", "date")
    narration_aliases = ("description", "particulars", "narration")
    debit_aliases = ("debit", "withdrawal", "withdrawal amt")
    credit_aliases = ("credit", "deposit", "deposit amt")
    balance_aliases = ("balance", "closing balance")
    reference_aliases = ("ref no./cheque no.", "ref no", "cheque no")


class AxisParser(TabularParser):
    bank = "AXIS"
    display_name = "Axis Bank"
    detect_tokens = ("axis bank", "axisbank", "utib0")

    date_aliases = ("tran date", "transaction date", "value date", "date")
    narration_aliases = ("particulars", "transaction particulars", "description", "narration")
    debit_aliases = ("debit", "withdrawal (dr)", "dr", "withdrawal amount")
    credit_aliases = ("credit", "deposit (cr)", "cr", "deposit amount")
    balance_aliases = ("balance", "closing balance")
    reference_aliases = ("chq no", "cheque no", "ref no", "init. br")


class KotakParser(TabularParser):
    bank = "KOTAK"
    display_name = "Kotak Mahindra Bank"
    detect_tokens = ("kotak mahindra", "kotak bank", "kkbk0", "kotak")

    date_aliases = ("date", "transaction date", "value date")
    narration_aliases = ("description", "narration", "particulars")
    # Kotak exports a single signed amount plus an explicit Dr/Cr marker.
    amount_aliases = ("amount", "withdrawal (dr)/deposit (cr)", "amount (inr)")
    type_aliases = ("dr / cr", "dr/cr", "drcr", "type")
    debit_aliases = ("withdrawal (dr)", "debit")
    credit_aliases = ("deposit (cr)", "credit")
    balance_aliases = ("balance", "balance (inr)")
    reference_aliases = ("chq / ref no", "chq/ref no", "ref no")


class GenericCSVParser(TabularParser):
    """Last-resort parser. Accepts any table with a date, a description and money."""

    bank = "GENERIC"
    display_name = "Generic statement"
    detect_tokens = ()

    @classmethod
    def matches(cls, text: str) -> int:
        return 1  # Always a candidate, always the lowest score.


BANK_PARSERS: list[type[TabularParser]] = [
    HDFCParser,
    ICICIParser,
    SBIParser,
    AxisParser,
    KotakParser,
]
