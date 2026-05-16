from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CharacterCardCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["faithful", "creative"] = "faithful"
    include_story_view: bool = True
    include_character_book: bool = True
    style: Literal["sillytavern"] = "sillytavern"
    language: Literal["zh-CN", "en-US"] = "zh-CN"


class CharacterCardUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    status: Literal["draft", "ready", "archived"] | None = None
    spec_json: dict[str, Any] | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped


class CharacterCardAvatarGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = "gpt-image-2-square"
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "3:4"] = "1:1"
    image_size: Literal["1K", "2K"] = "1K"


class CharacterCardAvatarGenerateResponse(BaseModel):
    card: "CharacterCardResponse"
    generation_id: str
    job_id: str
    status: str


class CharacterCardRoleImageGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = "gpt-image-2-three-four"
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "3:4"] = "3:4"
    image_size: Literal["1K", "2K"] = "1K"


class CharacterCardRoleImageGenerateResponse(BaseModel):
    card: "CharacterCardResponse"
    generation_id: str
    job_id: str
    status: str


class CharacterCardResponse(BaseModel):
    id: str
    source_entity_id: str
    status: str
    title: str
    card_format: str
    card_version: str
    mode: str
    spec_json: dict[str, Any] = Field(default_factory=dict)
    source_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    avatar_asset_id: str | None = None
    avatar_url: str | None = None
    role_image_asset_id: str | None = None
    role_image_url: str | None = None
    export_asset_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CharacterCardCreateResponse(BaseModel):
    card: CharacterCardResponse
