from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    id: str
    relation_id: str | None = None
    fact_type: str = "inferred"
    source_id: str
    target_id: str
    source_type: str | None = None
    target_type: str | None = None
    edge_type: str
    label: str
    weight: float
    evidence_count: int = 0
    is_editable: bool = False


class GraphWorkspaceConflictActionResponse(BaseModel):
    label: str
    action_type: str
    relation_id: str
    owner_type: str
    owner_id: str


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
    conflict_count: int = 0
    low_confidence_edge_count: int = 0
    orphan_node_count: int = 0


class GraphWorkspaceConflictResponse(BaseModel):
    id: str
    severity: str
    conflict_type: str
    title: str
    summary: str
    node_ids: list[str] = Field(default_factory=list)
    edge_label: str | None = None
    href: str
    actions: list[GraphWorkspaceConflictActionResponse] = Field(default_factory=list)
    disposition: str = "open"
    disposition_note: str | None = None
    is_active: bool = True


class GraphConflictDispositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: Literal["open", "keep", "snooze"]
    note: str | None = None
    conflict_type: str | None = None
    title: str | None = None
    summary: str | None = None
    node_ids: list[str] = Field(default_factory=list)
    edge_label: str | None = None


class GraphConflictDispositionResponse(BaseModel):
    id: str
    conflict_id: str
    disposition: str
    note: str | None = None
    updated_at: str | None = None


class GraphPathNodeResponse(BaseModel):
    id: str
    node_type: str
    label: str
    href: str


class GraphPathEdgeResponse(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    label: str
    fact_type: str
    relation_id: str | None = None
    evidence_count: int = 0
    confidence: float | None = None
    traversal_direction: str
    explanation: str


class GraphPathResponse(BaseModel):
    found: bool
    max_depth: int
    total_hops: int
    source: GraphPathNodeResponse
    target: GraphPathNodeResponse
    nodes: list[GraphPathNodeResponse] = Field(default_factory=list)
    edges: list[GraphPathEdgeResponse] = Field(default_factory=list)
    explanation: str


class GraphWorkspaceActionLogResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    action_type: str
    status_before: str | None = None
    status_after: str | None = None
    created_at: str | None = None
    summary: str
    diff_summary: str | None = None


class GraphWorkspaceAppliedFiltersResponse(BaseModel):
    node_types: list[str] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)
    start: str | None = None
    end: str | None = None
    min_weight: float = 0.0
    depth: int = 0


class GraphWorkspaceAvailableFiltersResponse(BaseModel):
    node_types: list[str] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)


class GraphWorkspaceFiltersResponse(BaseModel):
    applied: GraphWorkspaceAppliedFiltersResponse
    available: GraphWorkspaceAvailableFiltersResponse


class GraphWorkspaceConnectedNodeResponse(BaseModel):
    id: str
    node_type: str
    label: str
    subtitle: str
    href: str
    meta: list[str] = Field(default_factory=list)
    relation_label: str | None = None
    is_anchor: bool = False


class GraphWorkspaceNodeDetailResponse(BaseModel):
    node: GraphWorkspaceNodeResponse
    connected_nodes: list[GraphWorkspaceConnectedNodeResponse] = Field(default_factory=list)
    connected_edges: list[GraphWorkspaceEdgeResponse] = Field(default_factory=list)
    timeline_context: list[GraphWorkspaceTimelineItemResponse] = Field(default_factory=list)
    anchor_actions: list[GraphWorkspaceActionResponse] = Field(default_factory=list)


class GraphWorkspaceResponse(BaseModel):
    scope: str
    title: str
    description: str
    anchor: GraphWorkspaceAnchorResponse | None = None
    nodes: list[GraphWorkspaceNodeResponse] = Field(default_factory=list)
    edges: list[GraphWorkspaceEdgeResponse] = Field(default_factory=list)
    timeline_focus: list[GraphWorkspaceTimelineItemResponse] = Field(default_factory=list)
    stats: GraphWorkspaceStatsResponse
    filters: GraphWorkspaceFiltersResponse
    conflicts: list[GraphWorkspaceConflictResponse] = Field(default_factory=list)
    recent_actions: list[GraphWorkspaceActionLogResponse] = Field(default_factory=list)
