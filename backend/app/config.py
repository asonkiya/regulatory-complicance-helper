from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/accessibility_copilot"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Storage
    storage_base_path: str = "/tmp/accessibility_copilot_storage"

    # Anthropic
    anthropic_api_key: str = ""

    # Whisper
    whisper_model_size: str = "base"  # base | small | medium | large

    # API
    allowed_origins: list[str] = ["http://localhost:3000"]
    max_upload_size_bytes: int = 500 * 1024 * 1024  # 500 MB

    # Environment
    environment: str = "development"
    debug: bool = True


settings = Settings()
