from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    summary: str | None = None
    description: str | None = None
    event_type: str | None = None
    status: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    time_precision: str | None = None
    time_text: str | None = None
    timeline_sort_time: datetime | None = None
    location_text: str | None = None


class EventParticipantUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    role: str | None = None
    relation_type: str | None = None


class EventRelationUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: str
    related_type: str
    related_id: str
    relation_type: str


class EventRelationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: str | None = None
    related_type: str | None = None
    related_id: str | None = None
    relation_type: str | None = None


class EventResponse(BaseModel):
    id: str
    title: str
    summary: str | None
    description: str | None = None
    event_type: str | None
    status: str | None = None
    start_time: str | None
    end_time: str | None
    time_precision: str
    time_text: str | None
    timeline_sort_time: str | None = None
    location_text: str | None = None
    source_note_id: str | None = None
    confidence_score: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class EventParticipantResponse(BaseModel):
    id: str
    display_name: str
    entity_type: str
    role: str | None = None
    relation_type: str | None = None
    confidence_score: float | None = None


class EventRelatedEventResponse(BaseModel):
    id: str
    title: str
    summary: str | None = None
    time_text: str | None = None
    event_type: str | None = None
    connection_score: float
    connection_reasons: list[str] = Field(default_factory=list)
    shared_participants: list[str] = Field(default_factory=list)
    distance_days: int | None = None
    source_note_title: str | None = None


class EventDetailResponse(EventResponse):
    source_note_title: str | None = None
    participants: list[EventParticipantResponse] = Field(default_factory=list)
    related_events: list[EventRelatedEventResponse] = Field(default_factory=list)
