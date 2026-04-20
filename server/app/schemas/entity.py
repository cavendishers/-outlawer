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
    aliases: list[str] = Field(default_factory=list)
    status: str
    confidence_score: float | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class EntityRelatedEventResponse(BaseModel):
    id: str
    title: str
    summary: str | None = None
    time_text: str | None = None
    event_type: str | None = None
    location_text: str | None = None
    role: str | None = None
    relation_type: str | None = None
    start_time: str | None = None


class EntityTimelineFragmentResponse(BaseModel):
    event_id: str
    title: str
    summary: str | None = None
    time_text: str | None = None
    event_type: str | None = None
    location_text: str | None = None
    role: str | None = None
    relation_type: str | None = None
    chapter_label: str
    source_note_title: str | None = None
    position: int
    total: int


class EntityEventResponse(BaseModel):
    id: str
    title: str
    summary: str | None = None
    event_type: str | None = None
    start_time: str | None = None


class EntityEventListResponse(BaseModel):
    items: list[EntityEventResponse] = Field(default_factory=list)


class EntityDetailResponse(EntityResponse):
    related_events: list[EntityRelatedEventResponse] = Field(default_factory=list)
    timeline_fragments: list[EntityTimelineFragmentResponse] = Field(default_factory=list)
