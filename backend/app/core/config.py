from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_SECRETS = {
    "novaa-dev-secret-change-in-prod",
    "syntropy-dev-secret-change-in-prod",
    "your-super-secret-jwt-key-min-32-chars",
    "change-me",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    enable_demo_routes: bool = True

    setu_client_id: str = ""
    setu_client_secret: str = ""
    setu_org_id: str = ""
    setu_org_name: str = "NOVAA"
    setu_fiu_base_url: str = "https://fiu-sandbox.setu.co"
    setu_auth_url: str = "https://accountservice.setu.co/v1/users/login"
    setu_product_instance_id: str = "796f9c0e-e9d7-437c-8148-9423228909b7"
    setu_webhook_secret: str = ""

    database_url: str = "sqlite+aiosqlite:///./novaa.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "novaa-dev-secret-change-in-prod"
    encryption_key: str = ""
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    storage_backend: str = "local"
    storage_local_path: str = "./var/statements"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = "ap-south-1"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""

    frontend_url: str = "http://localhost:5173"
    redirect_url: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    gemini_api_key: str = ""
    sentry_dsn: str = ""
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def consent_redirect_url(self) -> str:
        if self.redirect_url:
            return self.redirect_url.rstrip("/")
        return f"{self.frontend_url.rstrip('/')}/consent/callback"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.is_production:
            return origins
        for default in ("http://localhost:5173", "http://127.0.0.1:5173"):
            if default not in origins:
                origins.append(default)
        return origins

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("sqlite:///") and "aiosqlite" not in url:
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        return (
            self.async_database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
        )

    def validate_production(self) -> None:
        """Refuse to boot in production with development secrets or demo routes on."""
        if not self.is_production:
            return
        problems: list[str] = []
        if self.jwt_secret in PLACEHOLDER_SECRETS or "change-in-prod" in self.jwt_secret:
            problems.append("JWT_SECRET is still a development placeholder")
        if len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be at least 32 characters")
        if not self.encryption_key:
            problems.append("ENCRYPTION_KEY must be set explicitly in production")
        if len(self.encryption_key) < 32:
            problems.append("ENCRYPTION_KEY must be at least 32 characters")
        if self.enable_demo_routes:
            problems.append("ENABLE_DEMO_ROUTES must be false in production")
        if self.database_url.startswith("sqlite"):
            problems.append("SQLite is not supported in production; use PostgreSQL")
        if problems:
            raise RuntimeError(
                "Refusing to start in production:\n  - " + "\n  - ".join(problems)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
