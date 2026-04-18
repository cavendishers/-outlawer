from pydantic import BaseModel


class AssetResponse(BaseModel):
    id: str
    asset_type: str
    title: str
    status: str
    original_text: str | None = None
    mime_type: str | None = None
    object_key: str | None = None
    raw_url: str | None = None


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
