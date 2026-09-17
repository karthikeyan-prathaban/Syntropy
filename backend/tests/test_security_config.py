import pytest

from app.api.v1.webhooks import verify_signature
from app.core.config import Settings
from app.core.crypto import decrypt_field, email_hash, encrypt_field, mask_account_number, mask_phone
from app.core.rate_limit import _match

PROD = {
    "environment": "production",
    "jwt_secret": "a" * 48,
    "encryption_key": "b" * 48,
    "enable_demo_routes": False,
    "database_url": "postgresql+asyncpg://u:p@db/novaa",
}


def _settings(**overrides) -> Settings:
    return Settings(**{**PROD, **overrides})


# --- startup guards ------------------------------------------------------


def test_a_correctly_configured_production_boots():
    _settings().validate_production()


def test_placeholder_jwt_secret_blocks_startup():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _settings(jwt_secret="novaa-dev-secret-change-in-prod").validate_production()


def test_short_jwt_secret_blocks_startup():
    with pytest.raises(RuntimeError, match="at least 32"):
        _settings(jwt_secret="short").validate_production()


def test_missing_encryption_key_blocks_startup():
    with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
        _settings(encryption_key="").validate_production()


def test_demo_routes_block_startup_in_production():
    with pytest.raises(RuntimeError, match="ENABLE_DEMO_ROUTES"):
        _settings(enable_demo_routes=True).validate_production()


def test_sqlite_blocks_startup_in_production():
    with pytest.raises(RuntimeError, match="SQLite"):
        _settings(database_url="sqlite+aiosqlite:///./novaa.db").validate_production()


def test_development_is_never_blocked():
    Settings(environment="development", jwt_secret="novaa-dev-secret-change-in-prod").validate_production()


def test_production_cors_does_not_silently_allow_localhost():
    settings = _settings(cors_origins="https://novaa.app")
    assert settings.cors_origin_list == ["https://novaa.app"]
    assert "http://localhost:5173" in Settings(environment="development").cors_origin_list


def test_postgres_url_is_upgraded_to_the_async_driver():
    assert Settings(database_url="postgresql://u:p@h/db").async_database_url.startswith(
        "postgresql+asyncpg://"
    )
    assert Settings(database_url="postgres://u:p@h/db").async_database_url.startswith(
        "postgresql+asyncpg://"
    )


# --- crypto --------------------------------------------------------------


def test_encryption_round_trips():
    cipher = encrypt_field("9876543210")
    assert cipher.startswith("enc:")
    assert "9876543210" not in cipher
    assert decrypt_field(cipher) == "9876543210"


def test_encryption_is_randomised_per_call():
    assert encrypt_field("same") != encrypt_field("same")


def test_email_hash_is_stable_and_case_insensitive():
    assert email_hash("Asha@Example.COM ") == email_hash("asha@example.com")
    assert email_hash("a@x.com") != email_hash("b@x.com")


def test_masking_never_reveals_the_full_value():
    assert mask_account_number("50100123456789") == "•••• 6789"
    assert "9876543210" not in mask_phone("9876543210")


# --- rate limit routing --------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
        "/api/v1/consent/create",
        "/api/v1/consent/abc-123/revoke",
        "/api/v1/consent/abc-123/fetch",
        "/api/v1/statements/upload",
        "/api/v1/me/data",
    ],
)
def test_sensitive_paths_are_rate_limited(path):
    assert _match(path) is not None


def test_the_parameterised_revoke_route_is_covered():
    """The old literal list had /consent/revoke, which no route ever matches."""
    assert _match("/api/v1/consent/revoke") is None
    assert _match("/api/v1/consent/9f3c-consent-id/revoke") is not None


def test_ordinary_reads_are_not_rate_limited():
    assert _match("/api/v1/dashboard") is None
    assert _match("/api/v1/health") is None


# --- webhook signatures --------------------------------------------------


def test_unsigned_webhooks_are_rejected(monkeypatch):
    from app.core import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("SETU_WEBHOOK_SECRET", "webhook-secret")
    try:
        body = b'{"data":{"consentId":"c1"}}'
        assert verify_signature(body, None) is False
        assert verify_signature(body, "sha256=deadbeef") is False

        import hashlib
        import hmac

        valid = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
        assert verify_signature(body, valid) is True
        assert verify_signature(body, f"sha256={valid}") is True
        # A different body must not validate against the same signature.
        assert verify_signature(b'{"data":{"consentId":"c2"}}', valid) is False
    finally:
        config.get_settings.cache_clear()


def test_webhooks_are_rejected_when_no_secret_is_configured(monkeypatch):
    from app.core import config

    config.get_settings.cache_clear()
    monkeypatch.delenv("SETU_WEBHOOK_SECRET", raising=False)
    try:
        assert verify_signature(b"{}", "sha256=anything") is False
    finally:
        config.get_settings.cache_clear()
