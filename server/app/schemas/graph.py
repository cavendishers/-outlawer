from pydantic import BaseModel, Field


class GraphWorkspaceActionResponse(BaseModel):
    label: str
    href: str
    action_type: str
    variant: str


class GraphWorkspaceInspectorResponse(BaseModel):
    id: str
    node_type: str
    title: str
    summary: str | None = None
    chips: list[str] = Field(default_factory=list)
    context_lines: list[str] = Field(default_factory=list)
    actions: list[GraphWorkspaceActionResponse] = Field(default_factory=list)


class GraphWorkspaceNodeResponse(BaseModel):
    id: str
    node_type: str
    label: str
    subtitle: str
    href: str
    importance: float
    meta: list[str] = Field(default_factory=list)
    is_anchor: bool = False
    inspector: GraphWorkspaceInspectorResponse


class GraphWorkspaceEdgeResponse(BaseModel):
    source_id: str
    target_id: str
    edge_type: str
    label: str
    weight: float


class GraphWorkspaceTimelineItemResponse(BaseModel):
    id: str
    event_id: str | None = None
    title: str
    display_time: str | None = None
    href: str
    kind: str


class GraphWorkspaceAnchorResponse(BaseModel):
    id: str
    node_type: str
    label: str
    subtitle: str
    href: str


class GraphWorkspaceStatsResponse(BaseModel):
    node_count: int
    edge_count: int
    event_count: int
    entity_count: int
    timeline_count: int


class GraphWorkspaceResponse(BaseModel):
    scope: str
    title: str
    description: str
    anchor: GraphWorkspaceAnchorResponse | None = None
    nodes: list[GraphWorkspaceNodeResponse] = Field(default_factory=list)
    edges: list[GraphWorkspaceEdgeResponse] = Field(default_factory=list)
    timeline_focus: list[GraphWorkspaceTimelineItemResponse] = Field(default_factory=list)
    stats: GraphWorkspaceStatsResponse
