from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from app.enrichment.aliases import MERCHANT_ALIASES, TOKEN_INDEX

# IFSC codes: four letters, a zero, then six alphanumerics. These appear inline in
# NEFT/IMPS narrations and would otherwise be mistaken for the merchant.
IFSC = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
# Bank reference tokens that are not valid IFSCs but follow the same shape:
# AXISP00123456, HDFCN0012345, SBIN00998877.
BANK_REF = re.compile(r"\b[A-Za-z]{2,8}\d{4,}[A-Za-z0-9]*\b")
# UTRs, RRNs, card numbers, and epoch-ish references.
LONG_DIGITS = re.compile(r"\b\d{6,}\b")
MASKED_CARD = re.compile(r"\b\d{4}[Xx*]{2,}\d{2,4}\b")
VPA = re.compile(r"\b([A-Za-z0-9._\-]{2,})@([A-Za-z]{2,})\b")
DATE_TOKEN = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")

# Payment-rail prefixes and bank noise that are never the merchant.
NOISE_TOKENS = {
    "upi", "imps", "neft", "rtgs", "ach", "ecs", "nach", "pos", "atm", "chq", "cheque",
    "debit", "credit", "dr", "cr", "txn", "trf", "transfer", "payment", "pmt", "ref",
    "refno", "rrn", "utr", "inb", "mmt", "vps", "nfs", "onl", "bil", "billdesk",
    "razorpay", "payu", "ccavenue", "cashfree", "billpay", "autopay", "mandate",
    "collect", "p2m", "p2a", "p2p", "sbin", "hdfc", "icic", "utib", "kkbk", "pytm",
    "ybl", "okaxis", "okhdfcbank", "okicici", "oksbi", "apl", "axl", "ibl", "paytm",
    "phonepe", "gpay", "googlepay", "bhim", "amazonpay", "india", "private", "limited",
    "ltd", "pvt", "services", "service", "technologies", "solutions", "and", "the",
    "from", "to", "by", "for", "no", "na", "null", "none", "bank", "acc", "ac",
}

# UPI PSP handles: the domain half of a VPA is the bank/PSP, not the merchant.
PSP_HANDLES = {
    "okaxis", "okhdfcbank", "okicici", "oksbi", "ybl", "ibl", "axl", "apl", "paytm",
    "ptyes", "ptaxis", "ptsbi", "pthdfc", "upi", "icici", "hdfcbank", "sbi", "axisbank",
    "kotak", "yesbank", "idfcbank", "indus", "airtel", "freecharge", "jio", "fbl",
    "rapl", "abfspay", "waaxis", "wahdfcbank", "waicici", "wasbi",
}


@dataclass(slots=True)
class MerchantMatch:
    canonical_key: str
    display_name: str
    category: str | None
    vpa: str | None
    confidence: float


def _extract_vpa(narration: str) -> tuple[str | None, str | None]:
    """Return (full vpa, merchant-ish local part) if the narration carries one."""
    for match in VPA.finditer(narration):
        local = match.group(1)
        # The local part is the payee; the handle is only the PSP that routed it.
        cleaned = LONG_DIGITS.sub("", re.sub(r"[._\-]+", " ", local)).strip()
        if cleaned and not cleaned.isdigit():
            return match.group(0), cleaned
    return None, None


def _strip_noise(text: str) -> list[str]:
    text = MASKED_CARD.sub(" ", text)
    text = IFSC.sub(" ", text)
    text = BANK_REF.sub(" ", text)
    text = DATE_TOKEN.sub(" ", text)
    text = LONG_DIGITS.sub(" ", text)
    text = re.sub(r"[^A-Za-z0-9@. ]+", " ", text)
    tokens = [t for t in text.lower().split() if t]
    return [t for t in tokens if t not in NOISE_TOKENS and not t.isdigit() and len(t) > 1]


def _lookup(candidate: str) -> tuple[str, float] | None:
    """Exact token hit, then substring, then fuzzy — in decreasing confidence."""
    key = candidate.strip().lower()
    if not key:
        return None
    if key in TOKEN_INDEX:
        return TOKEN_INDEX[key], 1.0
    compact = key.replace(" ", "")
    if compact in TOKEN_INDEX:
        return TOKEN_INDEX[compact], 0.97
    for token, canonical in TOKEN_INDEX.items():
        if len(token) >= 4 and (token in key or token.replace(" ", "") in compact):
            return canonical, 0.9
    close = difflib.get_close_matches(compact, list(TOKEN_INDEX), n=1, cutoff=0.86)
    if close:
        return TOKEN_INDEX[close[0]], 0.75
    return None


def normalize_merchant(narration: str, mode: str = "", txn_type: str = "DEBIT") -> MerchantMatch:
    """Extract the counterparty from an Indian bank narration.

    The extraction is mode-aware because each rail encodes the payee differently:
    UPI puts it in the VPA, POS after the masked card, NEFT after the IFSC, and
    ACH after the mandate sponsor.
    """
    raw = (narration or "").strip()
    if not raw:
        return MerchantMatch("unknown", "Unknown", None, None, 0.0)

    upper_mode = (mode or "").upper()
    vpa, vpa_name = _extract_vpa(raw)

    candidates: list[str] = []
    if vpa_name:
        candidates.append(vpa_name)

    tokens = _strip_noise(raw)

    if "POS" in upper_mode or raw.upper().startswith("POS"):
        # POS 4567XX...1234 AMAZON PAY INDIA -> everything after the card is the merchant.
        after_card = MASKED_CARD.split(raw)
        if len(after_card) > 1:
            candidates.append(" ".join(_strip_noise(after_card[-1])))
    if "ACH" in raw.upper() or "NACH" in raw.upper():
        # ACH D- HDFCBANK-SIP: the segment after the sponsor bank names the mandate.
        segments = [s for s in re.split(r"[-/]", raw) if s.strip()]
        if len(segments) >= 2:
            candidates.append(" ".join(_strip_noise(segments[-1])))

    # Longest meaningful run of tokens first, then individual tokens.
    if tokens:
        candidates.append(" ".join(tokens[:3]))
        candidates.extend(tokens)

    for candidate in candidates:
        hit = _lookup(candidate)
        if hit:
            canonical, confidence = hit
            entry = MERCHANT_ALIASES[canonical]
            return MerchantMatch(canonical, entry["display"], entry["category"], vpa, confidence)

    # No alias match: fall back to the cleanest name the narration offers, which is
    # still far better than the old narration.split("/")[0] that returned bank codes.
    fallback_source = vpa_name or (" ".join(tokens[:3]) if tokens else "")
    display = " ".join(w.capitalize() for w in fallback_source.split())[:60]
    if not display:
        display = "Unknown"
    canonical = re.sub(r"[^a-z0-9]+", "", display.lower()) or "unknown"
    return MerchantMatch(canonical, display, None, vpa, 0.4 if display != "Unknown" else 0.0)
