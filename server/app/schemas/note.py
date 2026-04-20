from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    title: str | None = None


class NoteReplayActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = None


class NoteResponse(BaseModel):
    id: str
    title: str
    summary: str | None
    canonical_text: str | None
    category: str | None
    status: str
    asset_id: str | None
    active_projection_id: str | None = None
    primary_time: str | None
    processed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class NoteCreateResponse(BaseModel):
    note_id: str
    job_id: str


class ExtractionRunSummaryResponse(BaseModel):
    title: str
    category: str
    entity_count: int
    event_count: int
    relation_count: int
    similarity_hint_count: int


class ExtractionRunResponse(BaseModel):
    id: str
    note_id: str
    source_asset_id: str | None = None
    status: str
    is_applied: bool
    extractor_name: str
    extractor_version: str
    provider_name: str
    model_name: str
    prompt_version: str
    schema_version: str
    input_hash: str
    parent_run_id: str | None = None
    run_kind: str
    projection_status: str
    created_at: str | None = None
    updated_at: str | None = None
    summary: ExtractionRunSummaryResponse


class ReplayActionResponse(BaseModel):
    id: str
    action_type: str
    created_at: str | None = None
    status_before: str | None = None
    status_after: str | None = None
    run_id: str
    previous_run_id: str | None = None
    projection_version_id: str | None = None
    previous_projection_version_id: str | None = None
    extractor_name: str
    extractor_version: str
    provider_name: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    schema_version: str | None = None
    note: str | None = None


class ProjectionResultResponse(BaseModel):
    note_id: str
    event_id: str | None = None
    projection_version_id: str | None = None
    extractor_name: str
    extractor_version: str
    entity_count: int
    relation_count: int
    similarity_hint_count: int


class ExtractionRunDiffFieldResponse(BaseModel):
    field: str
    base: Any = None
    candidate: Any = None
    changed: bool


class ExtractionRunItemChangeResponse(BaseModel):
    key: str
    base: dict[str, Any] = Field(default_factory=dict)
    candidate: dict[str, Any] = Field(default_factory=dict)


class ExtractionRunCollectionDiffResponse(BaseModel):
    changed: bool
    added: list[dict[str, Any]] = Field(default_factory=list)
    removed: list[dict[str, Any]] = Field(default_factory=list)
    changed_items: list[ExtractionRunItemChangeResponse] = Field(default_factory=list)
    unchanged_count: int
    base_count: int
    candidate_count: int


class ExtractionRunSectionDiffResponse(BaseModel):
    changed: bool
    fields: list[ExtractionRunDiffFieldResponse] = Field(default_factory=list)


class ExtractionRunCompareDiffResponse(BaseModel):
    changed: bool
    summary: ExtractionRunSectionDiffResponse
    entities: ExtractionRunCollectionDiffResponse
    events: ExtractionRunCollectionDiffResponse
    relations: ExtractionRunCollectionDiffResponse
    similarity_hints: ExtractionRunCollectionDiffResponse
    style_payload: ExtractionRunSectionDiffResponse


class ExtractionRunCompareResponse(BaseModel):
    note_id: str
    base_run: ExtractionRunResponse
    candidate_run: ExtractionRunResponse
    diff: ExtractionRunCompareDiffResponse


class NoteExtractionRunApplyResponse(BaseModel):
    note: NoteResponse
    applied_run: ExtractionRunResponse
    projection_result: ProjectionResultResponse
    replay_actions: list[ReplayActionResponse] = Field(default_factory=list)


class NoteExtractionRunApproveResponse(BaseModel):
    note: NoteResponse
    approved_run: ExtractionRunResponse
    projection_result: ProjectionResultResponse
    replay_actions: list[ReplayActionResponse] = Field(default_factory=list)


class NoteExtractionRunRejectResponse(BaseModel):
    note: NoteResponse
    rejected_run: ExtractionRunResponse
    replay_actions: list[ReplayActionResponse] = Field(default_factory=list)
