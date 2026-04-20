from typing import Any

from pydantic import BaseModel, Field


class AssetResponse(BaseModel):
    id: str
    asset_type: str
    title: str
    status: str
    original_text: str | None = None
    mime_type: str | None = None
    object_key: str | None = None
    file_size: int | None = None
    checksum: str | None = None
    raw_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AssetDerivativeResponse(BaseModel):
    id: str
    derivative_type: str
    version: str | None = None
    content_preview: str
    meta_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class AssetNoteReferenceResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: str | None = None
    processed_at: str | None = None


class AssetDetailResponse(AssetResponse):
    derivatives: list[AssetDerivativeResponse] = Field(default_factory=list)
    notes: list[AssetNoteReferenceResponse] = Field(default_factory=list)


class AssetRawResponse(BaseModel):
    asset_id: str
    original_text: str | None = None
    raw_url: str | None = None


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
