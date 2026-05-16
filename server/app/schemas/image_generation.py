from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.asset import AssetResponse


class ImageGenerationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1)
    model: str | None = "gpt-image-2"
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "3:4"] = "9:16"
    image_size: Literal["1K", "2K"] = "1K"
    reference_asset_ids: list[str] = Field(default_factory=list)

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("prompt must not be blank")
        return stripped


class ImageGenerationCreateResponse(BaseModel):
    generation_id: str
    job_id: str
    status: str


class ImageGenerationResponse(BaseModel):
    id: str
    job_id: str | None = None
    status: str
    prompt: str
    model_name: str
    aspect_ratio: str
    image_size: str
    reference_asset_ids: list[str] = Field(default_factory=list)
    upstream_task_id: str | None = None
    result_urls: list[str] = Field(default_factory=list)
    result_asset_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None
    raw_response_json: dict[str, Any] = Field(default_factory=dict)
    result_assets: list[AssetResponse] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
