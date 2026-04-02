"""Application configuration via pydantic-settings."""

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_db: str = "scribbles_dev"

    # Optional direct DATABASE_URL override (e.g. for tests or cloud deployments)
    database_url_override: str | None = Field(None, validation_alias="DATABASE_URL")

    redis_url: str = "redis://localhost:6379"
    allowed_origins: list[str] = ["http://localhost:5173"]
    max_players: int = 10
    host_transfer_delay_ms: int = 1000
    idle_timeout_seconds: int = 180  # 3 minutes of player inactivity during a game
    room_ttl_seconds: int = 300  # Redis TTL and hibernation timeout (5 minutes)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @computed_field
    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
