"""Application configuration via pydantic-settings."""

import os
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal  # Needed for runtime  validation of Pydantic Settings

from pydantic import SecretStr, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

if TYPE_CHECKING:
    from typing import Self

# ENV=dev loads .env.dev, ENV=prod loads .env.prod, etc.
# If the resolved file does not exist, pydantic-settings ignores it silently.
_ENV_STR = os.getenv("ENV", "dev").lower()


class ENV(StrEnum):
    """Environment enum for selecting configuration profiles.

    The value corresponds to the suffix of the .env file to load.
    """

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
    category_cache_ttl_seconds: int = 60 * 60 * 24

    @computed_field
    @property
    def redis_url(self) -> str:
        """Construct the Redis URL from host and port."""
        return f"redis://{self.redis_host}:{self.redis_port}"

    # Network configuration
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    # Allowed origins are validated below in _prod_safety_checks.
    # NoDecode keeps pydantic-settings from JSON-parsing the env value so the
    # validator below can accept a plain comma-separated string (e.g. in .env.prod).
    allowed_origins: Annotated[list[str] | None, NoDecode] = None

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_allowed_origins(cls, value: object) -> object:
        """Allow ALLOWED_ORIGINS to be a comma-separated string in env files."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

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
    kick_vote_timeout_seconds: int = 60

    # Abuse / overload protection
    max_total_rooms: int = 500
    ws_max_message_bytes: int = 64 * 1024
    ws_draw_messages_per_window: int = 60
    ws_draw_window_seconds: int = 1
    room_creation_rate_limit: int = 10
    room_creation_rate_window_seconds: int = 60

    @model_validator(mode="after")
    def _prod_safety_checks(self) -> Self:
        # Apply environment-specific cookie security defaults.
        if CURRENT_ENV == ENV.DEV:
            # Local development often runs over plain HTTP, so avoid browser
            # warnings by keeping the cookie first-party unless explicitly
            # overridden in the environment.
            self.session_cookie_same_site = "lax"
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
