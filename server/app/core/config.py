from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Outlawer API"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 24
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_display_name: str = "Outlawer Admin"

    database_url: str = "postgresql+psycopg://outlawer:outlawer@postgres:5432/outlawer"
    redis_url: str = "redis://redis:6379/0"
    broker_url: str = "amqp://guest:guest@rabbitmq:5672//"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "outlawer-assets"

    extractor_provider: str = "auto"
    chat_provider: str = "deepseek"
    chat_base_url: str = "https://api.deepseek.com"
    chat_api_key: str | None = None
    chat_model: str = "deepseek-v4-pro"
    chat_timeout_seconds: float = 60.0
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
    vision_provider: str = "bailian"
    audio_transcription_provider: str = "bailian"
    bailian_api_key: str | None = None
    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_vision_model: str = "qwen3.5-plus"
    bailian_video_model: str = "qwen3.5-plus"
    bailian_audio_model: str = "qwen3-omni-30b-a3b-captioner"
    bailian_audio_stream: bool = False
    bailian_timeout_seconds: float = 180.0
    bailian_multimodal_max_bytes: int = 50 * 1024 * 1024
    bailian_video_fps: float = 2.0
    sy_gpt_base_url: str = "https://console.viiideo.com"
    sy_gpt_api_key: str | None = None
    sy_gpt_timeout_seconds: float = 300.0
    sy_gpt_poll_interval_seconds: float = 2.0
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

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        if self.secret_key in {"", "change-me", "dev-secret-key"}:
            raise ValueError("SECRET_KEY must be set to a non-default value in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
