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
    event_type: str | None
    start_time: str | None
    end_time: str | None
    time_precision: str
    time_text: str | None


class EventDetailResponse(EventResponse):
    participants: list[dict] = Field(default_factory=list)
