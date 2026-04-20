from pydantic import BaseModel, Field

from app.schemas.job import JobResponse


class OperationsStatusCountResponse(BaseModel):
    status: str
    count: int


class OperationsExtractionRunSignalResponse(BaseModel):
    run_id: str
    note_id: str
    note_title: str
    status: str
    extractor_name: str
    extractor_version: str
    created_at: str | None = None
    href: str


class OperationsMergeCandidateSignalResponse(BaseModel):
    id: str
    object_type: str
    status: str
    score: float
    source_label: str | None = None
    candidate_label: str | None = None
    href: str


class OperationsActivityItemResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    action_type: str
    status_before: str | None = None
    status_after: str | None = None
    created_at: str | None = None
    href: str
    href_label: str
    summary: str


class OperationsJobSummaryResponse(BaseModel):
    total: int
    pending: int
    running: int
    failed: int
    completed: int
    by_status: list[OperationsStatusCountResponse] = Field(default_factory=list)
    recent_failed_jobs: list[JobResponse] = Field(default_factory=list)


class OperationsAssetSummaryResponse(BaseModel):
    total: int
    uploaded: int
    by_type: list[OperationsStatusCountResponse] = Field(default_factory=list)


class OperationsReviewSummaryResponse(BaseModel):
    pending_total: int
    pending_entities: int
    pending_events: int
    recent_candidates: list[OperationsMergeCandidateSignalResponse] = Field(default_factory=list)


class OperationsExtractionSummaryResponse(BaseModel):
    ready_for_review: int
    processing_notes: int
    recent_reviewable_runs: list[OperationsExtractionRunSignalResponse] = Field(default_factory=list)


class OperationsActivitySummaryResponse(BaseModel):
    recent_actions: list[OperationsActivityItemResponse] = Field(default_factory=list)


class OperationsOverviewResponse(BaseModel):
    jobs: OperationsJobSummaryResponse
    assets: OperationsAssetSummaryResponse
    review: OperationsReviewSummaryResponse
    extraction: OperationsExtractionSummaryResponse
    activity: OperationsActivitySummaryResponse
