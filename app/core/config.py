from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and an optional .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Todo API"
    version: str = "1.1.0"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./todo.db"

    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Tracing is enabled only when an OTLP endpoint is configured.
    otel_exporter_otlp_endpoint: str | None = None


# Fields are read from the environment, which type checkers cannot see.
settings = Settings()  # pyright: ignore[reportCallIssue]
