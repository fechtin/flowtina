"""Application configuration.

Loads settings from environment variables (and an optional ``.env`` file) using
Pydantic Settings. Designed to run on a 1 CPU / 1GB VPS with sane production
defaults and SQLite as the default database.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=(
            BASE_DIR / "config" / ".env",
            BASE_DIR.parent / "config" / ".env",
            BASE_DIR.parent / ".env",  # project-root .env (canonical secrets)
            BASE_DIR / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "Flowtina"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    default_language: str = "en"

    # --- Database ---
    database_url: str = Field(default=f"sqlite:///{BASE_DIR / 'database' / 'app.db'}")
    db_pool_size: int = 5
    db_max_overflow: int = 5

    # --- Security ---
    jwt_secret: str = "change-me-in-production-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    # Fernet key (urlsafe base64, 32 bytes). Auto-generated for dev if unset.
    encryption_key: str = ""

    # --- Logging ---
    log_level: str = "INFO"
    log_dir: str = str(BASE_DIR / "logs")
    log_retention_days: int = 30

    # --- Scheduler ---
    scheduler_max_threads: int = 2
    scheduler_enabled: bool = True

    # --- Public URL & Telegram webhook ---
    # Public HTTPS base URL of the deployment, e.g. https://example.com
    # Used to register the Telegram webhook for approval callbacks.
    public_base_url: str = ""
    # Shared secret sent by Telegram in the X-Telegram-Bot-Api-Secret-Token header.
    telegram_webhook_secret: str = ""

    # --- Facebook (self-host minimal setup) ---
    # A System User / long-lived token used to auto-discover the operator's own
    # Pages, so users don't paste per-page tokens. Optional.
    facebook_system_token: str = ""
    # Optional app credentials: when set, a short-lived user token is exchanged
    # for a long-lived one before discovering Pages.
    facebook_app_id: str = ""
    facebook_app_secret: str = ""

    # --- Rate limiting (requests / minute) ---
    rate_limit_anonymous: int = 30
    rate_limit_authenticated: int = 300
    rate_limit_admin: int = 1000

    # --- Outbound content HTTP (RSS / URL fetching) ---
    # Emulate a real browser when fetching external pages/feeds. Many sites sit
    # behind a WAF that returns HTTP 403 to non-browser clients until a session
    # cookie from an initial "challenge" request is presented.
    http_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    http_fetch_timeout_seconds: int = 30

    # --- Pipeline / providers ---
    provider_timeout_seconds: int = 60
    provider_max_retries: int = 3
    quality_threshold: int = 60
    quality_max_retries: int = 2

    # --- Provider API keys (env fallback for model discovery / connection tests) ---
    # Used when the dashboard form has no key typed in, so operators can list a
    # provider's available models without re-entering the secret each time.
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    openrouter_api_key: str = ""
    claude_api_key: str = ""

    def provider_api_key(self, provider: str) -> str:
        """Return the env-configured API key for ``provider`` (empty if none)."""
        return str(getattr(self, f"{provider.lower()}_api_key", "") or "")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton ``Settings`` instance."""
    return Settings()


settings = get_settings()
