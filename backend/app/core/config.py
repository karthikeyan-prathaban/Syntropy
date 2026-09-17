from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    setu_client_id: str = ""
    setu_client_secret: str = ""
    setu_org_id: str = ""
    setu_org_name: str = "NOVAA"
    setu_fiu_base_url: str = "https://fiu-sandbox.setu.co"
    setu_auth_url: str = "https://accountservice.setu.co/v1/users/login"
    setu_product_instance_id: str = "796f9c0e-e9d7-437c-8148-9423228909b7"
    database_url: str = "sqlite+aiosqlite:///./novaa.db"
    jwt_secret: str = "novaa-dev-secret-change-in-prod"
    encryption_key: str = ""
    frontend_url: str = "http://localhost:5173"
    redirect_url: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    gemini_api_key: str = ""

    @property
    def consent_redirect_url(self) -> str:
        if self.redirect_url:
            return self.redirect_url.rstrip("/")
        return f"{self.frontend_url.rstrip('/')}/consent/callback"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        for default in ("http://localhost:5173", "http://127.0.0.1:5173"):
            if default not in origins:
                origins.append(default)
        return origins

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("sqlite:///") and "aiosqlite" not in url:
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
