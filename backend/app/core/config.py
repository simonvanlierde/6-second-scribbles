"""Application configuration via pydantic-settings."""

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=".env.dev", env_file_encoding="utf-8")

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

    @computed_field
    @property
    def redis_url(self) -> str:
        """Construct the Redis URL from host and port."""
        return f"redis://{self.redis_host}:{self.redis_port}"

    # Network configuration
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    allowed_origins: list[str] = ["http://localhost:5173"]

    # Game configuration
    max_players: int = 10
    host_transfer_delay_ms: int = 1000
    idle_timeout_seconds: int = 180
    room_ttl_seconds: int = 300
    room_hibernation_delay_seconds: int = 60
    game_complete_delay_seconds: int = 5


settings = Settings()
