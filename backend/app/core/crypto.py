import base64
import hashlib
import os
import re
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

SALT = b"novaa-fiu-aes256-rebit-compliance-salt"


@lru_cache(maxsize=1)
def _get_encryption_key() -> bytes:
    settings = get_settings()
    raw = settings.encryption_key
    if not raw:
        if settings.is_production:
            raise RuntimeError(
                "ENCRYPTION_KEY is not set. Financial data cannot be encrypted with a "
                "fallback key in production. Generate one with: "
                'python -c "import secrets; print(secrets.token_hex(32))"'
            )
        raw = settings.jwt_secret
    return hashlib.sha256(raw.encode("utf-8") + SALT).digest()


def email_hash(email: str) -> str:
    """Deterministic, indexable hash so encrypted emails remain searchable in O(1)."""
    normalized = (email or "").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8") + SALT).hexdigest()


def encrypt_field(plain_text: str | None) -> str:
    if plain_text is None or plain_text == "":
        return ""
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plain_text.encode("utf-8"), None)
    return "enc:" + base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_field(cipher_text: str | None) -> str:
    if cipher_text is None or cipher_text == "":
        return ""
    if not cipher_text.startswith("enc:"):
        return cipher_text
    combined = base64.b64decode(cipher_text[4:].encode("ascii"))
    nonce, ciphertext = combined[:12], combined[12:]
    aesgcm = AESGCM(_get_encryption_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def mask_account_number(account_number: str | None) -> str:
    if not account_number:
        return "•••• 0000"
    if any(c in account_number for c in "•X*"):
        return account_number
    clean = re.sub(r"[^\w]", "", account_number)
    return f"•••• {clean[-4:]}" if len(clean) > 4 else f"•••• {clean}"


def mask_phone(phone: str | None) -> str:
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) >= 10:
        return f"+91 {digits[-10:-8]}•••• •{digits[-4:]}"
    return "••••••••••"


def mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return email or ""
    local, domain = email.split("@", 1)
    masked = local[0] + "•" * max(1, len(local) - 2) + (local[-1] if len(local) > 1 else "")
    return f"{masked}@{domain}"
