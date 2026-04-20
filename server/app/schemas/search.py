from pydantic import BaseModel, Field


class SearchResultItemResponse(BaseModel):
    id: str
    title: str
    summary: str | None = None
    type: str


class SearchResultListResponse(BaseModel):
    items: list[SearchResultItemResponse] = Field(default_factory=list)


class SearchNoteResultResponse(BaseModel):
    id: str
    title: str
    summary: str | None = None
    status: str
    primary_time: str | None = None
    href: str
    search_type: str


class SearchEntityResultResponse(BaseModel):
    id: str
    display_name: str
    canonical_name: str
    entity_type: str
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    confidence_score: float | None = None
    href: str
    search_type: str


class SearchEventResultResponse(BaseModel):
    id: str
    title: str
    summary: str | None = None
    event_type: str | None = None
    time_text: str | None = None
    location_text: str | None = None
    confidence_score: float | None = None
    href: str
    search_type: str


class SimilarNoteResultResponse(BaseModel):
    note_id: str
    id: str
    title: str
    summary: str | None = None
    primary_time: str | None = None
    href: str
    search_type: str


class SearchTopHitResponse(BaseModel):
    id: str
    label: str
    summary: str | None = None
    href: str
    result_type: str
    meta: list[str | None] = Field(default_factory=list)


class UnifiedSearchStatsResponse(BaseModel):
    top_hit_count: int
    note_count: int
    entity_count: int
    event_count: int
    similar_count: int


class UnifiedSearchResponse(BaseModel):
    query: str
    seed_note_id: str | None = None
    seed_note_title: str | None = None
    top_hits: list[SearchTopHitResponse] = Field(default_factory=list)
    notes: list[SearchNoteResultResponse] = Field(default_factory=list)
    entities: list[SearchEntityResultResponse] = Field(default_factory=list)
    events: list[SearchEventResultResponse] = Field(default_factory=list)
    similar_notes: list[SimilarNoteResultResponse] = Field(default_factory=list)
    stats: UnifiedSearchStatsResponse


class SimilarNoteListResponse(BaseModel):
    items: list[SimilarNoteResultResponse] = Field(default_factory=list)


class SearchMergeCandidateItemResponse(BaseModel):
    id: str
    object_type: str
    source_id: str
    source_label: str | None = None
    candidate_id: str
    candidate_label: str | None = None
    score: float
    status: str
    reason: dict = Field(default_factory=dict)


class SearchMergeCandidateListResponse(BaseModel):
    items: list[SearchMergeCandidateItemResponse] = Field(default_factory=list)
