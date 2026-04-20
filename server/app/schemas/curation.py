from typing import Any

from pydantic import BaseModel, Field

from app.schemas.entity import (
    EntityAliasResponse,
    EntityRelatedEventResponse,
    EntityResponse,
    EntityTimelineFragmentResponse,
)
from app.schemas.event import EventParticipantResponse, EventResponse
from app.schemas.note import NoteResponse


CurationObjectDataResponse = EntityResponse | EventResponse | NoteResponse


class CurationObjectSummaryResponse(BaseModel):
    id: str
    object_type: str
    label: str
    subtitle: str | None = None
    href: str
    data: CurationObjectDataResponse


class CurationRelationItemResponse(BaseModel):
    id: str
    direction: str
    relation_type: str
    peer: CurationObjectSummaryResponse
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class EntityCurationStatsResponse(BaseModel):
    alias_count: int
    related_event_count: int
    related_note_count: int
    relation_count: int


class EntityCurationContextResponse(BaseModel):
    entity: EntityResponse
    aliases: list[EntityAliasResponse] = Field(default_factory=list)
    related_events: list[EntityRelatedEventResponse] = Field(default_factory=list)
    relations: list[CurationRelationItemResponse] = Field(default_factory=list)
    timeline_fragments: list[EntityTimelineFragmentResponse] = Field(default_factory=list)
    stats: EntityCurationStatsResponse


class EntityAliasRemovedResponse(BaseModel):
    entity_id: str
    alias_id: str
    status: str


class RelationRemovedResponse(BaseModel):
    relation_id: str
    status: str


class EventCurationSubjectResponse(EventResponse):
    source_note_title: str | None = None


class EventCurationStatsResponse(BaseModel):
    participant_count: int
    relation_count: int


class EventCurationContextResponse(BaseModel):
    event: EventCurationSubjectResponse
    participants: list[EventParticipantResponse] = Field(default_factory=list)
    relations: list[CurationRelationItemResponse] = Field(default_factory=list)
    stats: EventCurationStatsResponse


class EventParticipantResponsePayload(BaseModel):
    event_id: str
    entity_id: str
    role: str | None = None
    relation_type: str


class EventParticipantRemovedResponse(BaseModel):
    event_id: str
    entity_id: str
    status: str
