"""Application configuration via pydantic-settings."""

import os
from enum import Enum
from typing import Literal, Self

from pydantic import SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ENV=dev loads .env.dev, ENV=prod loads .env.prod, etc.
# If the resolved file does not exist, pydantic-settings ignores it silently.
_ENV_STR = os.getenv("ENV", "dev").lower()


class ENV(str, Enum):
    DEV = "dev"
    PROD = "prod"


try:
    CURRENT_ENV = ENV(_ENV_STR)
except ValueError:
    CURRENT_ENV = ENV.DEV


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=f".env.{_ENV_STR}", env_file_encoding="utf-8")

    # Database configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: SecretStr = SecretStr("password")
    postgres_db: str = "scribbles_dev"

    @computed_field
    @property
    def database_url(self) -> str:
        """Construct the async database URL from individual components."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Cache configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    auth_session_ttl_seconds: int = 60 * 60 * 24 * 30
    session_cookie_name: str = "scribbles_session"
    session_cookie_secure: bool = False
    session_cookie_same_site: Literal["lax", "strict", "none"] = "lax"
    auth_guest_rate_limit: int = 20
    auth_guest_rate_window_seconds: int = 60
    auth_register_rate_limit: int = 10
    auth_register_rate_window_seconds: int = 60
    auth_login_rate_limit: int = 10
    auth_login_rate_window_seconds: int = 60
    category_mutation_rate_limit: int = 30
    category_mutation_rate_window_seconds: int = 60
    category_locale_availability_ttl_seconds: int = 120

    @computed_field
    @property
    def redis_url(self) -> str:
        """Construct the Redis URL from host and port."""
        return f"redis://{self.redis_host}:{self.redis_port}"

    # Network configuration
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    # Allowed origins are validated below in _prod_safety_checks to ensure it's set and does not contain wildcards in production.
    allowed_origins: list[str] | None = None

    # Game configuration
    max_players: int = 10
    host_transfer_delay_ms: int = 1000
    idle_timeout_seconds: int = 180
    room_ttl_seconds: int = 300
    room_hibernation_delay_seconds: int = 60
    game_start_delay_seconds: int = 1
    drawing_to_guessing_buffer_seconds: int = 2
    round_results_countdown_seconds: int = 5
    game_complete_delay_seconds: int = 5

    @model_validator(mode="after")
    def _prod_safety_checks(self) -> Self:
        # Apply environment-specific cookie security defaults.
        if CURRENT_ENV == ENV.DEV:
            # Cross-site development: SameSite=none to allow fetch credentials across origins.
            self.session_cookie_same_site = "none"
            self.session_cookie_secure = False
            if not self.allowed_origins:
                self.allowed_origins = ["*"]
        else:
            # Production: stricter cookie policy for same-origin setup (via Caddy proxy).
            self.session_cookie_same_site = "lax"
            self.session_cookie_secure = True
            # Production safety checks: ensure explicit origins and no wildcard.
            if not self.allowed_origins:
                msg = (
                    "Production ENV detected but `allowed_origins` is not set. "
                    "Set allowed_origins in .env.prod to a list of trusted origins."
                )
                raise ValueError(msg)
            if "*" in self.allowed_origins:  # noqa: PLR2004 # '*' is a common wildcard for "allow all origins"
                msg = (
                    "Wildcard origin ('*') is not permitted in production. "
                    "Set `allowed_origins` to a concrete list of origins in .env.prod."
                )
                raise ValueError(msg)
        return self


settings = Settings()
