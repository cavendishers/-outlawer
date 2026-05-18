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


class NoteStoryViewSnapshotResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    title: str
    content: str
    style_type: str


class NoteStoryRegenerateResponse(BaseModel):
    note_id: str
    story_view: NoteStoryViewSnapshotResponse
    run_id: str | None = None


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


class AnalysisWorkflowAssetResponse(BaseModel):
    id: str
    asset_type: str
    title: str
    status: str
    mime_type: str | None = None
    file_size: int | None = None
    original_text_preview: str | None = None
    created_at: str | None = None


class AnalysisWorkflowDerivativeResponse(BaseModel):
    id: str
    derivative_type: str
    version: str
    content_preview: str
    meta_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class AnalysisWorkflowJobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    target_type: str
    target_id: str
    error_message: str | None = None
    retry_count: int
    payload_json: dict[str, Any] = Field(default_factory=dict)
    result_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    finished_at: str | None = None


class AnalysisWorkflowRunResponse(ExtractionRunResponse):
    raw_result_json: dict[str, Any] = Field(default_factory=dict)
    normalized_result_json: dict[str, Any] = Field(default_factory=dict)


class AnalysisWorkflowProjectionResponse(BaseModel):
    id: str
    extraction_run_id: str
    source_asset_id: str | None = None
    previous_projection_id: str | None = None
    action_type: str
    summary_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class AnalysisWorkflowEvidenceSampleResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    field_name: str | None = None
    evidence_text: str
    evidence_offset_start: int | None = None
    evidence_offset_end: int | None = None
    extractor_name: str
    extractor_version: str
    confidence_score: float | None = None
    created_at: str | None = None


class AnalysisWorkflowEvidenceGroupResponse(BaseModel):
    target_type: str
    target_id: str
    field_names: list[str] = Field(default_factory=list)
    evidence_count: int
    average_confidence: float | None = None
    samples: list[AnalysisWorkflowEvidenceSampleResponse] = Field(default_factory=list)


class AnalysisWorkflowStepResponse(BaseModel):
    step_key: str
    title: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    model_name: str | None = None
    provider_name: str | None = None
    summary: str
    evidence: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)


class AnalysisWorkflowStatsResponse(BaseModel):
    job_count: int
    derivative_count: int
    run_count: int
    projection_count: int
    replay_action_count: int
    evidence_count: int


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


class AnalysisWorkflowResponse(BaseModel):
    note: NoteResponse
    asset: AnalysisWorkflowAssetResponse | None = None
    active_run_id: str | None = None
    latest_run_id: str | None = None
    active_projection_id: str | None = None
    stats: AnalysisWorkflowStatsResponse
    steps: list[AnalysisWorkflowStepResponse] = Field(default_factory=list)
    jobs: list[AnalysisWorkflowJobResponse] = Field(default_factory=list)
    derivatives: list[AnalysisWorkflowDerivativeResponse] = Field(default_factory=list)
    runs: list[AnalysisWorkflowRunResponse] = Field(default_factory=list)
    projections: list[AnalysisWorkflowProjectionResponse] = Field(default_factory=list)
    evidence_groups: list[AnalysisWorkflowEvidenceGroupResponse] = Field(default_factory=list)
    raw_normalized_diff: ExtractionRunCompareDiffResponse
    replay_actions: list[ReplayActionResponse] = Field(default_factory=list)


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
