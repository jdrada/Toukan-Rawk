"""Application configuration using Pydantic BaseSettings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    aws_endpoint_url: Optional[str] = None  # For LocalStack

    # S3
    s3_bucket_name: str = "rawk-audio-bucket"

    # SQS
    sqs_queue_url: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_enabled: bool = True

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "rawk_db"
    db_user: str = "postgres"
    db_password: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    whisper_model: str = "whisper-1"

    # App
    environment: str = "development"
    debug: bool = True

    @property
    def database_url(self) -> str:
        """Build async PostgreSQL connection string."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
