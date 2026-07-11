from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.entity import EntityResponse
from app.schemas.event import EventResponse


class ManualEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str | None = None
    raw_asset_id: str | None = None
    excerpt: str | None = None
    curator_note: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "ManualEvidenceInput":
        if bool(self.note_id) == bool(self.raw_asset_id):
            raise ValueError("Exactly one of note_id or raw_asset_id is required")
        return self


class ManualEntityCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str = "person"
    canonical_name: str
    display_name: str | None = None
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    evidence: ManualEvidenceInput | None = None


class ManualEventCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str | None = None
    description: str | None = None
    event_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    time_precision: str = "unknown"
    time_text: str | None = None
    timeline_sort_time: datetime | None = None
    location_text: str | None = None
    evidence: ManualEvidenceInput | None = None


class ManualEvidenceCreateRequest(ManualEvidenceInput):
    target_type: str
    target_id: str


class ManualEvidenceResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    note_id: str | None = None
    raw_asset_id: str | None = None
    source_title: str
    excerpt: str | None = None
    curator_note: str | None = None
    provenance_type: str
    created_at: str | None = None


class ManualEntityCreateResponse(BaseModel):
    entity: EntityResponse
    evidence: ManualEvidenceResponse | None = None
    routes: dict[str, str]


class ManualEventCreateResponse(BaseModel):
    event: EventResponse
    evidence: ManualEvidenceResponse | None = None
    routes: dict[str, str]


class GraphManualNodeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_type: str
    name: str
    description: str | None = None
    subtype: str | None = None
    anchor_type: str
    anchor_id: str
    relation_type: str | None = None
    role: str | None = None
    event_time: datetime | None = None
    evidence: ManualEvidenceInput | None = None


class GraphManualNodeCreateResponse(BaseModel):
    node_type: str
    node_id: str
    label: str
    connection_type: str
    connection_id: str
    evidence: ManualEvidenceResponse | None = None
    graph_href: str
