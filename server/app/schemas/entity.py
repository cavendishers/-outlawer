from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EntityUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str | None = None
    canonical_name: str | None = None
    display_name: str | None = None
    description: str | None = None
    status: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None


class EntityAliasCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: str
    alias_type: str | None = None


class EntityRelationUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: str
    related_type: str
    related_id: str
    relation_type: str


class EntityRelationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: str | None = None
    related_type: str | None = None
    related_id: str | None = None
    relation_type: str | None = None


class EntityResponse(BaseModel):
    id: str
    entity_type: str
    canonical_name: str
    display_name: str
    description: str | None
    aliases: list[str]


class EntityDetailResponse(EntityResponse):
    related_events: list[dict] = Field(default_factory=list)
