"""Application configuration via pydantic-settings."""

from functools import cached_property

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_db: str = "scribbles_dev"

    redis_url: str = "redis://localhost:6379"
    allowed_origins: list[str] = ["http://localhost:5173"]
    max_players: int = 10
    host_transfer_delay_ms: int = 1000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @cached_property
    def database_url(self):
        return f"postgresql+asyncpg://postgres:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()
