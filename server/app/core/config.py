from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Outlawer API"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 24

    database_url: str = "postgresql+psycopg://outlawer:outlawer@postgres:5432/outlawer"
    redis_url: str = "redis://redis:6379/0"
    broker_url: str = "amqp://guest:guest@rabbitmq:5672//"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "outlawer-assets"

    extractor_provider: str = "auto"
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    openrouter_models: str = (
        "qwen/qwen3-next-80b-a3b-instruct:free,"
        "google/gemma-4-31b-it:free,"
        "google/gemma-4-26b-a4b-it:free,"
        "nvidia/nemotron-3-super-120b-a12b:free,"
        "minimax/minimax-m2.5:free,"
        "arcee-ai/trinity-large-preview:free,"
        "nvidia/nemotron-nano-9b-v2:free,"
        "google/gemma-3-27b-it:free,"
        "google/gemma-3-4b-it:free,"
        "google/gemma-3n-e4b-it:free,"
        "google/gemma-3n-e2b-it:free,"
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
    )
    openrouter_site_url: str | None = None
    openrouter_app_name: str = "Outlawer"
    openrouter_timeout_seconds: float = 60.0
    openrouter_max_tokens: int = 2200
    openrouter_multimodal_model: str = "openrouter/free"
    openrouter_multimodal_max_bytes: int = 12 * 1024 * 1024
    local_media_models_dir: str = "/tmp/outlawer-models"
    local_media_tesseract_languages: str = "chi_sim+eng"
    local_media_ffmpeg_bin: str = "ffmpeg"
    local_media_tesseract_bin: str = "tesseract"

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
        ]
    )

    extractor_vector_size: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
