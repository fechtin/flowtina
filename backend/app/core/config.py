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
    # The scheduler uses an in-memory jobstore (no shared SQLite jobstore) to avoid
    # write contention that could lock the DB and kill the scheduler loop. Because
    # that store is not shared with the API process, the scheduler reconciles
    # DB-defined jobs into it on this interval so API create/update/delete take
    # effect without a restart.
    scheduler_resync_seconds: int = 60

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
    # --- Messenger (direct messages, webhook-driven) ---
    # Token echoed back during Meta's webhook verification (GET challenge). Set
    # the same value in the Messenger webhook config on the Meta dashboard.
    messenger_verify_token: str = ""
    # --- Messenger DM auto-reply (webhook enqueues, poller replies) ---
    # How often the inbox poller ticks to send queued DM replies, in seconds.
    # Small so replies feel prompt; the job is single-instance so it never piles up.
    messenger_inbox_tick_seconds: int = 5
    # A follower's messages are coalesced into one reply once they have paused for
    # this many seconds (debounce), so rapid-fire lines get a single, in-context reply.
    messenger_debounce_seconds: int = 6
    # Safety cap: at most this many queued messages are merged into one reply turn.
    messenger_coalesce_max: int = 10
    # Stop retrying a message after this many failed send attempts.
    messenger_max_attempts: int = 3
    # --- Comment auto-engagement (poller) ---
    # How often the scheduler "ticks" to look for pages due for engagement. The
    # actual cadence is per-page (FacebookPage.engage_interval_minutes); this is
    # just the polling granularity, so it should be <= the smallest page interval.
    facebook_engage_tick_minutes: int = 5
    # Recent posts scanned per page per poll (newest first).
    facebook_engage_max_posts: int = 25
    # Comments fetched per post per poll (newest first).
    facebook_engage_max_comments: int = 50

    # --- Long-term memory (per-user recall across conversations) ---
    # Master switch. When off, the engagement flow behaves exactly as before.
    memory_enabled: bool = True
    # Embedding backend used for semantic dedupe/retrieval:
    #   "hash"     - dependency-free feature-hash embedding (offline, deterministic)
    #   "gemini"   - Google text-embedding-004 via API (multilingual, needs gemini key)
    #   "model2vec"- local open-source static embeddings (needs the optional
    #                ``model2vec`` package installed; falls back to hash if missing)
    memory_embedding_provider: str = "hash"
    memory_embedding_model: str = "text-embedding-004"
    # Fixed embedding dimension. Mock and real backends are interchangeable as
    # long as this stays constant; changing it requires re-embedding memories.
    memory_embedding_dim: int = 256
    # A memory is stored when importance >= this OR it is an emotional/preference
    # event (see scorer). Range 1..100.
    memory_save_threshold: int = 60
    # Two memories with cosine similarity above this are merged, not duplicated.
    memory_dedupe_similarity: float = 0.90
    # Max memories injected into a reply prompt (after 4-bucket merge + ranking).
    memory_retrieval_limit: int = 30
    # Verbatim transcript turns kept inline as short-term context per reply.
    memory_history_turns: int = 6
    # Nightly consolidation (merge/decay/summary/archive). UTC cron expression.
    memory_consolidation_cron: str = "0 2 * * *"
    # Archive lowest-scoring memories once a user exceeds this count.
    memory_archive_cap: int = 10000

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

    # --- Media uploads (post images) ---
    # Directory for temporarily-stored uploaded post images. Files live here
    # only between upload and a successful Facebook publish, then are removed.
    upload_dir: str = str(BASE_DIR / "uploads")
    # Maximum accepted upload size in bytes (default 10 MiB).
    upload_max_bytes: int = 10 * 1024 * 1024

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
