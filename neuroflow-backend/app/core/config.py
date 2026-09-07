"""Application settings, loaded from environment variables / .env.

Settings are validated at import time (via get_settings(), called at app
startup) so a missing or malformed variable fails loudly at boot rather than
inside a request at 3am. See docs/08-backend-architecture.md #8.8.
"""
from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False

    # --- Identity & wire ---
    public_url: str = "http://localhost:8000"
    cors_origins: list[AnyHttpUrl] = Field(default_factory=list)

    # --- Datastores ---
    database_url: PostgresDsn
    redis_url: RedisDsn

    # --- Secrets ---
    # No defaults for either key in production: the app refuses to boot
    # without them (enforced in main.py's lifespan, not here, so that local
    # dev with a throwaway .env stays convenient).
    secret_key: SecretStr = SecretStr("")
    credential_master_key: SecretStr = SecretStr("")

    # --- Auth ---
    access_token_ttl: timedelta = timedelta(minutes=15)
    refresh_token_ttl: timedelta = timedelta(days=30)
    jwt_algorithm: str = "HS256"

    # --- Execution limits ---
    max_execution_seconds: int = 3600
    max_payload_mb: int = 16
    execution_retention_days: int = 30
    worker_max_jobs: int = 10

    # --- Feature toggles ---
    code_node_enabled: bool = True
    code_node_network: bool = False
    ssrf_allow_cidrs: list[str] = Field(default_factory=list)

    # --- Object storage (optional; falls back to inline-only payloads) ---
    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_access_key: SecretStr | None = None
    s3_secret_key: SecretStr | None = None

    # --- Observability ---
    log_level: str = "info"
    otel_exporter_otlp_endpoint: str | None = None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from env/.env, not constructor args
