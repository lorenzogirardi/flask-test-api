"""Application configuration via Pydantic Settings (env-based)."""

import re
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All config is driven by environment variables with sane defaults."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # --- App ---
    app_name: str = "pytbak"
    app_version: str = "2.0.0"
    app_env: Literal["development", "production", "test"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    shutdown_timeout: int = Field(default=30, description="Graceful shutdown timeout in seconds")

    # --- Auth (basic auth for diag endpoints) ---
    diag_username: str = "admin"
    diag_password: str = "password"

    # --- Debug endpoints ---
    debug_endpoints_enabled: bool = Field(default=True, description="Set to false to disable /debug/* in production")

    # --- MCP server ---
    mcp_enabled: bool = Field(default=True, description="Mount the MCP server at /api/mcp (Basic Auth protected)")

    # --- Redis ---
    redis_url: str | None = Field(default=None, description="redis://host:port/db or http(s) endpoint in prod")
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_retry_attempts: int = 3
    redis_retry_delay: float = 0.5

    # --- PostgreSQL ---
    database_url: str | None = Field(default=None, description="postgresql+asyncpg://user:pass@host/db")
    db_pool_size: int = Field(default=5, description="SQLAlchemy connection pool size")
    db_max_overflow: int = Field(default=10, description="SQLAlchemy max overflow connections")

    # --- Cache ---
    cache_ttl: int = Field(default=300, description="Local cache TTL in seconds")
    cache_max_size: int = Field(default=1000, description="Max items in local cache")

    # --- Rate limiting ---
    rate_limit: str = "100/minute"
    debug_rate_limit: str = "10/minute"

    # --- OTEL ---
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_exporter_timeout: int = Field(default=10, description="OTLP exporter timeout in seconds")
    otel_service_name: str = "pytbak"

    # --- Prometheus ---
    prometheus_enabled: bool = True

    # --- Webdis (legacy compat) ---
    webdis_url: str = "http://webdis-svc.webdis:7379"

    @property
    def effective_redis_url(self) -> str:
        """Return redis_url if set, otherwise build from host/port/db."""
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def sanitized_redis_url(self) -> str:
        """Return Redis URL with password masked for logging."""
        return re.sub(r"://[^@]*@", "://***@", self.effective_redis_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
