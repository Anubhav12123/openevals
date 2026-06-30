from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = (
        "postgresql+asyncpg://openevals:password@localhost:5432/openevals"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10

    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    together_api_key: Optional[str] = None
    google_ai_key: Optional[str] = None

    api_secret_key: str = "change-me-in-production"
    api_rate_limit_per_minute: int = 100
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    prometheus_port: int = 9090

    pipeline_max_workers: int = 20
    pipeline_batch_size: int = 50
    pipeline_judge_timeout_seconds: int = 30
    pipeline_max_retries: int = 3

    environment: str = "development"
    log_level: str = "INFO"


settings = Settings()
