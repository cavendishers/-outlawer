from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.entity import EntityAliasResponse, EntityResponse, EntityTimelineFragmentResponse
from app.schemas.event import EventDetailResponse, EventResponse
from app.schemas.note import NoteResponse


class MergeCandidateRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = "rejected_by_user"
    note: str | None = None


class MergeCandidateAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution: Literal["merge", "alias_only"] = "merge"
    survivor_id: str | None = None
    note: str | None = None


class ConfirmEntityAliasRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: str
    note: str | None = None


ReviewObjectDataResponse = EntityResponse | EventResponse | NoteResponse


class ReviewObjectSummaryResponse(BaseModel):
    id: str
    label: str
    href: str
    stats: dict[str, int] = Field(default_factory=dict)
    data: ReviewObjectDataResponse


class MergeCandidateResponse(BaseModel):
    id: str
    object_type: str
    status: str
    score: float
    reason: dict[str, Any] = Field(default_factory=dict)
    reviewed_at: str | None = None
    review_note: str | None = None
    source: ReviewObjectSummaryResponse | None = None
    candidate: ReviewObjectSummaryResponse | None = None


class MergeCandidateDetailResponse(MergeCandidateResponse):
    can_accept: bool
    can_reject: bool


class MergeCandidateRejectResponse(BaseModel):
    candidate_id: str
    status: str


class MergeCandidateAcceptResponse(BaseModel):
    candidate_id: str
    status: str
    resolution: str
    survivor_id: str
    merged_id: str | None = None


class ConfirmEntityAliasResponse(BaseModel):
    entity_id: str
    aliases: list[str] = Field(default_factory=list)


class EntityReviewStatsResponse(BaseModel):
    related_event_count: int
    related_note_count: int
    alias_count: int
    candidate_count: int


class EntityReviewContextResponse(BaseModel):
    entity: EntityResponse
    aliases: list[EntityAliasResponse] = Field(default_factory=list)
    stats: EntityReviewStatsResponse
    timeline_fragments: list[EntityTimelineFragmentResponse] = Field(default_factory=list)
    candidates: list[MergeCandidateResponse] = Field(default_factory=list)


class EventReviewStatsResponse(BaseModel):
    participant_count: int
    linked_note_count: int
    candidate_count: int


class EventReviewContextResponse(BaseModel):
    event: EventDetailResponse
    stats: EventReviewStatsResponse
    candidates: list[MergeCandidateResponse] = Field(default_factory=list)
