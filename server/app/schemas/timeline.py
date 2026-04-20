from pydantic import BaseModel, Field


class TimelineItemResponse(BaseModel):
    id: str
    event_id: str | None
    note_id: str | None
    title: str
    summary: str | None
    display_time: str | None
    sort_time: str | None
    time_precision: str


class TimelineOverviewStatsResponse(BaseModel):
    event_count: int
    entity_count: int
    timeline_count: int
    edge_count: int


class TimelineOverviewNodeResponse(BaseModel):
    id: str
    node_type: str
    label: str
    subtitle: str
    href: str
    importance: float
    meta: list[str] = Field(default_factory=list)


class TimelineOverviewEdgeResponse(BaseModel):
    source_id: str
    target_id: str
    edge_type: str
    label: str
    weight: float


class TimelineOverviewResponse(BaseModel):
    stats: TimelineOverviewStatsResponse
    nodes: list[TimelineOverviewNodeResponse] = Field(default_factory=list)
    edges: list[TimelineOverviewEdgeResponse] = Field(default_factory=list)
    timeline_focus: list[TimelineItemResponse] = Field(default_factory=list)


class TimelineRangeResponse(BaseModel):
    items: list[TimelineItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    start: str | None = None
    end: str | None = None
