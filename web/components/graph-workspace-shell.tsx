"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/panel";

type GraphAction = {
  label: string;
  href: string;
  action_type: string;
  variant: string;
};

type GraphInspector = {
  id: string;
  node_type: string;
  title: string;
  summary: string | null;
  chips: string[];
  context_lines: string[];
  actions: GraphAction[];
};

type GraphNode = {
  id: string;
  node_type: string;
  label: string;
  subtitle: string;
  href: string;
  importance: number;
  meta: string[];
  is_anchor: boolean;
  inspector: GraphInspector;
};

type GraphEdge = {
  source_id: string;
  target_id: string;
  edge_type: string;
  label: string;
  weight: number;
};

type TimelineFocusItem = {
  id: string;
  event_id: string | null;
  title: string;
  display_time: string | null;
  href: string;
  kind: string;
};

type GraphWorkspaceAppliedFilters = {
  node_types: string[];
  relation_types: string[];
  start: string | null;
  end: string | null;
  min_weight: number;
  depth: number;
};

type GraphWorkspaceFilters = {
  applied: GraphWorkspaceAppliedFilters;
  available: {
    node_types: string[];
    relation_types: string[];
  };
};

type GraphConnectedNode = {
  id: string;
  node_type: string;
  label: string;
  subtitle: string;
  href: string;
  meta: string[];
  relation_label: string | null;
  is_anchor: boolean;
};

type GraphNodeDetail = {
  node: GraphNode;
  connected_nodes: GraphConnectedNode[];
  connected_edges: GraphEdge[];
  timeline_context: TimelineFocusItem[];
  anchor_actions: GraphAction[];
};

type GraphRelationItem = {
  id: string;
  direction: string;
  relation_type: string;
  peer: {
    id: string;
    object_type: string;
    label: string;
    subtitle: string | null;
    href: string;
  };
  source_type: string;
  source_id: string;
  target_type: string;
  target_id: string;
};

type GraphEventParticipant = {
  id: string;
  display_name: string;
  entity_type: string;
  role: string | null;
  relation_type: string | null;
};

type GraphEventCurationContext = {
  kind: "event";
  event: {
    id: string;
    title: string;
  };
  participants: GraphEventParticipant[];
  relations: GraphRelationItem[];
  stats: {
    participant_count: number;
    relation_count: number;
  };
};

type GraphEntityCurationContext = {
  kind: "entity";
  entity: {
    id: string;
    display_name: string;
    entity_type: string;
  };
  relations: GraphRelationItem[];
  stats: {
    relation_count: number;
  };
};

type GraphNodeCurationContext = GraphEventCurationContext | GraphEntityCurationContext;

type GraphRelationPayload = {
  direction: string;
  related_type: string;
  related_id: string;
  relation_type: string;
};

type GraphParticipantPayload = {
  entity_id: string;
  role: string | null;
  relation_type: string | null;
};

type GraphWorkspaceShellProps = {
  title: string;
  description: string;
  scope: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  timelineFocus: TimelineFocusItem[];
  stats: {
    node_count: number;
    edge_count: number;
    event_count: number;
    entity_count: number;
    timeline_count: number;
  };
  filters: GraphWorkspaceFilters;
  activeNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  onUpdateFilters: (updates: Partial<GraphWorkspaceAppliedFilters>, reset?: boolean) => void;
  nodeDetail: GraphNodeDetail | null;
  nodeDetailLoading?: boolean;
  curationContext: GraphNodeCurationContext | null;
  curationLoading?: boolean;
  mutationBusyKey?: string;
  mutationMessage?: string;
  mutationError?: string;
  onDismissMutationMessage: () => void;
  onDismissMutationError: () => void;
  onUpsertEventParticipant: (eventNodeId: string, payload: GraphParticipantPayload) => Promise<void>;
  onRemoveEventParticipant: (eventNodeId: string, relatedEntityId: string) => Promise<void>;
  onUpsertRelation: (
    nodeType: "event" | "entity",
    nodeId: string,
    payload: GraphRelationPayload,
    relationId?: string
  ) => Promise<void>;
  onRemoveRelation: (nodeType: "event" | "entity", nodeId: string, relationId: string) => Promise<void>;
};

type PositionedNode = GraphNode & {
  x: number;
  y: number;
  tone: "paper" | "aqua" | "peach" | "neon";
};

type GraphWorkspaceViewMode = "all" | "events" | "people" | "timeline";

function edgeKey(edge: GraphEdge): string {
  return `${edge.source_id}-${edge.target_id}-${edge.edge_type}-${edge.label}`;
}

function toneForNode(node: GraphNode): PositionedNode["tone"] {
  if (node.is_anchor) return "neon";
  if (node.node_type === "event") return "peach";
  if (node.node_type === "entity") return "aqua";
  return "paper";
}

const EVENT_RELATION_TYPE_OPTIONS = [
  "related_to",
  "occurs_before",
  "occurs_after",
  "source_of",
  "located_in",
  "blocks",
  "supports",
];

const ENTITY_RELATION_TYPE_OPTIONS = [
  "related_to",
  "supports",
  "blocks",
  "source_of",
  "located_in",
  "member_of",
  "mentions",
];

const NODE_TYPE_LABELS: Record<string, string> = {
  event: "事件",
  entity: "人物",
};

function dateInputValue(value: string | null): string {
  return value ? value.slice(0, 10) : "";
}

function toggleListValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function defaultRelatedTypeForNode(activeNode: GraphNode, nodes: GraphNode[]): "event" | "entity" {
  const candidateTypes = nodes
    .filter((node) => node.id !== activeNode.id)
    .map((node) => node.node_type)
    .filter((value): value is "event" | "entity" => value === "event" || value === "entity");
  if (activeNode.node_type === "event" && candidateTypes.includes("entity")) return "entity";
  if (activeNode.node_type === "entity" && candidateTypes.includes("event")) return "event";
  return candidateTypes[0] ?? "event";
}

type GraphFilterPanelProps = {
  filters: GraphWorkspaceFilters;
  hasBackendFilters: boolean;
  onUpdateFilters: (updates: Partial<GraphWorkspaceAppliedFilters>, reset?: boolean) => void;
};

function GraphFilterPanel({ filters, hasBackendFilters, onUpdateFilters }: GraphFilterPanelProps) {
  const nodeTypeOptions = filters.available.node_types.length ? filters.available.node_types : ["event", "entity"];
  const relationTypeOptions = filters.available.relation_types;

  return (
    <div className="mb-5 border-4 border-ink bg-white p-4 shadow-brutalSoft">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="section-kicker">图谱过滤</p>
          <p className="mt-2 text-sm font-bold leading-relaxed text-muted">
            用结构条件缩小工作台范围。过滤会写入地址栏，方便回看同一张图。
          </p>
        </div>
        <button
          type="button"
          onClick={() => onUpdateFilters({}, true)}
          disabled={!hasBackendFilters}
          className="brutal-action brutal-action-secondary disabled:cursor-not-allowed disabled:opacity-50"
        >
          重置
        </button>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr_1.2fr_0.8fr_0.8fr_1.2fr]">
        <div>
          <p className="text-xs font-black tracking-[0.14em]">节点类型</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {nodeTypeOptions.map((nodeType) => {
              const active = filters.applied.node_types.includes(nodeType);
              return (
                <button
                  key={nodeType}
                  type="button"
                  onClick={() => onUpdateFilters({ node_types: toggleListValue(filters.applied.node_types, nodeType) })}
                  className={`border-2 border-ink px-3 py-2 text-xs font-black shadow-brutalTiny ${
                    active ? "bg-neon" : "bg-canvas"
                  }`}
                >
                  {NODE_TYPE_LABELS[nodeType] ?? nodeType}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <p className="text-xs font-black tracking-[0.14em]">关系类型</p>
          <div className="mt-2 flex max-h-24 flex-wrap gap-2 overflow-y-auto pr-1">
            {relationTypeOptions.length ? (
              relationTypeOptions.map((relationType) => {
                const active = filters.applied.relation_types.includes(relationType);
                return (
                  <button
                    key={relationType}
                    type="button"
                    onClick={() =>
                      onUpdateFilters({ relation_types: toggleListValue(filters.applied.relation_types, relationType) })
                    }
                    className={`border-2 border-ink px-3 py-2 text-xs font-black shadow-brutalTiny ${
                      active ? "bg-neon" : "bg-canvas"
                    }`}
                  >
                    {relationType}
                  </button>
                );
              })
            ) : (
              <span className="brutal-chip">暂无关系</span>
            )}
          </div>
        </div>

        <label className="block">
          <span className="text-xs font-black tracking-[0.14em]">最小权重</span>
          <select
            value={String(filters.applied.min_weight)}
            onChange={(event) => onUpdateFilters({ min_weight: Number(event.target.value) })}
            className="mt-2 w-full border-4 border-ink bg-canvas px-3 py-2 text-sm font-black shadow-brutalTiny"
          >
            {[0, 0.5, 0.7, 0.9].map((weight) => (
              <option key={weight} value={weight}>
                {weight === 0 ? "不限" : `≥ ${weight.toFixed(1)}`}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs font-black tracking-[0.14em]">跳数</span>
          <select
            value={String(filters.applied.depth)}
            onChange={(event) => onUpdateFilters({ depth: Number(event.target.value) })}
            className="mt-2 w-full border-4 border-ink bg-canvas px-3 py-2 text-sm font-black shadow-brutalTiny"
          >
            <option value="0">不限</option>
            <option value="1">1 跳</option>
            <option value="2">2 跳</option>
          </select>
        </label>

        <div>
          <p className="text-xs font-black tracking-[0.14em]">时间范围</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
            <input
              type="date"
              value={dateInputValue(filters.applied.start)}
              onChange={(event) => onUpdateFilters({ start: event.target.value || null })}
              className="min-w-0 border-4 border-ink bg-canvas px-3 py-2 text-sm font-black shadow-brutalTiny"
              aria-label="开始时间"
            />
            <input
              type="date"
              value={dateInputValue(filters.applied.end)}
              onChange={(event) => onUpdateFilters({ end: event.target.value || null })}
              className="min-w-0 border-4 border-ink bg-canvas px-3 py-2 text-sm font-black shadow-brutalTiny"
              aria-label="结束时间"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export function GraphWorkspaceShell({
  title,
  description,
  scope,
  nodes,
  edges,
  timelineFocus,
  stats,
  filters,
  activeNodeId,
  onSelectNode,
  onUpdateFilters,
  nodeDetail,
  nodeDetailLoading = false,
  curationContext,
  curationLoading = false,
  mutationBusyKey = "",
  mutationMessage = "",
  mutationError = "",
  onDismissMutationMessage,
  onDismissMutationError,
  onUpsertEventParticipant,
  onRemoveEventParticipant,
  onUpsertRelation,
  onRemoveRelation,
}: GraphWorkspaceShellProps) {
  const [viewMode, setViewMode] = useState<GraphWorkspaceViewMode>("all");
  const [selectedEdgeKey, setSelectedEdgeKey] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [focusNeighborhoodOnly, setFocusNeighborhoodOnly] = useState(false);
  const appliedFilterChips = [
    filters.applied.node_types.length
      ? `节点：${filters.applied.node_types.map((item) => NODE_TYPE_LABELS[item] ?? item).join("、")}`
      : "节点：全部",
    filters.applied.relation_types.length ? `关系：${filters.applied.relation_types.join("、")}` : "关系：全部",
    filters.applied.min_weight > 0 ? `权重 ≥ ${filters.applied.min_weight.toFixed(1)}` : "权重：全部",
    filters.applied.depth > 0 ? `跳数：${filters.applied.depth}` : "跳数：不限",
    filters.applied.start || filters.applied.end
      ? `时间：${dateInputValue(filters.applied.start) || "不限"} 至 ${dateInputValue(filters.applied.end) || "不限"}`
      : "时间：不限",
  ];
  const hasBackendFilters =
    filters.applied.node_types.length > 0 ||
    filters.applied.relation_types.length > 0 ||
    Boolean(filters.applied.start) ||
    Boolean(filters.applied.end) ||
    filters.applied.min_weight > 0 ||
    filters.applied.depth > 0;

  const allPositionedNodes = useMemo<PositionedNode[]>(() => {
    const anchorNodes = nodes.filter((node) => node.is_anchor);
    const eventNodes = nodes.filter((node) => node.node_type === "event" && !node.is_anchor);
    const entityNodes = nodes.filter((node) => node.node_type === "entity" && !node.is_anchor);

    const positioned: PositionedNode[] = [];
    if (anchorNodes[0]) {
      positioned.push({
        ...anchorNodes[0],
        x: 50,
        y: 48,
        tone: toneForNode(anchorNodes[0]),
      });
    }

    eventNodes.slice(0, 8).forEach((node, index, list) => {
      const columns = Math.min(4, list.length || 1);
      const row = Math.floor(index / columns);
      const column = index % columns;
      const x = columns === 1 ? 50 : 18 + column * (64 / Math.max(1, columns - 1));
      const y = 18 + row * 22;
      positioned.push({
        ...node,
        x,
        y,
        tone: toneForNode(node),
      });
    });

    entityNodes.slice(0, 8).forEach((node, index, list) => {
      const columns = Math.min(4, list.length || 1);
      const row = Math.floor(index / columns);
      const column = index % columns;
      const x = columns === 1 ? 50 : 14 + column * (72 / Math.max(1, columns - 1));
      const y = 76 + row * 16;
      positioned.push({
        ...node,
        x,
        y,
        tone: toneForNode(node),
      });
    });

    return positioned;
  }, [nodes]);

  const timelineEventIds = useMemo(
    () => new Set(timelineFocus.map((item) => item.event_id).filter((value): value is string => Boolean(value))),
    [timelineFocus]
  );

  const modePositionedNodes = useMemo(() => {
    return allPositionedNodes.filter((node) => {
      if (node.is_anchor) return true;
      if (viewMode === "all") return true;
      if (viewMode === "events") return node.node_type === "event";
      if (viewMode === "people") return node.node_type === "entity";
      if (viewMode === "timeline") {
        return node.node_type === "event" ? timelineEventIds.has(node.id) : false;
      }
      return true;
    });
  }, [allPositionedNodes, timelineEventIds, viewMode]);

  const normalizedSearchQuery = searchQuery.trim().toLowerCase();
  const searchMatchedNodes = useMemo(() => {
    if (!normalizedSearchQuery) return modePositionedNodes;
    return modePositionedNodes.filter((node) => {
      if (node.is_anchor) return true;
      const searchable = [node.label, node.subtitle, node.node_type, ...node.meta, ...node.inspector.chips]
        .join(" ")
        .toLowerCase();
      return searchable.includes(normalizedSearchQuery);
    });
  }, [modePositionedNodes, normalizedSearchQuery]);

  const activeNodeBeforeNeighborhood =
    searchMatchedNodes.find((node) => node.id === activeNodeId) ?? searchMatchedNodes[0] ?? null;
  const activeNeighborhoodNodeIds = useMemo(() => {
    if (!activeNodeBeforeNeighborhood) return new Set<string>();
    const ids = new Set<string>([activeNodeBeforeNeighborhood.id]);
    edges.forEach((edge) => {
      if (edge.source_id === activeNodeBeforeNeighborhood.id) ids.add(edge.target_id);
      if (edge.target_id === activeNodeBeforeNeighborhood.id) ids.add(edge.source_id);
    });
    return ids;
  }, [activeNodeBeforeNeighborhood, edges]);

  const positionedNodes = useMemo(() => {
    if (!focusNeighborhoodOnly || !activeNodeBeforeNeighborhood) return searchMatchedNodes;
    return searchMatchedNodes.filter((node) => activeNeighborhoodNodeIds.has(node.id));
  }, [activeNeighborhoodNodeIds, activeNodeBeforeNeighborhood, focusNeighborhoodOnly, searchMatchedNodes]);

  const visibleNodeIds = useMemo(() => new Set(positionedNodes.map((node) => node.id)), [positionedNodes]);
  const visibleEdges = useMemo(
    () => edges.filter((edge) => visibleNodeIds.has(edge.source_id) && visibleNodeIds.has(edge.target_id)),
    [edges, visibleNodeIds]
  );
  const visibleDensity = useMemo(() => {
    const possibleEdgeCount = (visibleNodeIds.size * (visibleNodeIds.size - 1)) / 2;
    if (possibleEdgeCount <= 0) return 0;
    return Math.min(1, visibleEdges.length / possibleEdgeCount);
  }, [visibleEdges.length, visibleNodeIds]);

  useEffect(() => {
    if (activeNodeId && visibleNodeIds.has(activeNodeId)) return;
    if (!positionedNodes[0]) return;
    onSelectNode(positionedNodes[0].id);
  }, [activeNodeId, onSelectNode, positionedNodes, visibleNodeIds]);

  const activeNode = positionedNodes.find((node) => node.id === activeNodeId) ?? positionedNodes[0] ?? null;
  const nodeMap = new Map(positionedNodes.map((node) => [node.id, node]));
  const selectedEdge = visibleEdges.find((edge) => edgeKey(edge) === selectedEdgeKey) ?? null;
  const selectedEdgeSource = selectedEdge ? nodeMap.get(selectedEdge.source_id) ?? null : null;
  const selectedEdgeTarget = selectedEdge ? nodeMap.get(selectedEdge.target_id) ?? null : null;
  const relatedEdges = activeNode
    ? visibleEdges.filter((edge) => edge.source_id === activeNode.id || edge.target_id === activeNode.id)
    : [];
  const filterSummary = [
    viewMode === "all"
      ? "全部节点"
      : viewMode === "events"
        ? "仅事件"
        : viewMode === "people"
          ? "仅人物"
          : "时间主干",
    focusNeighborhoodOnly ? "焦点邻域" : "全局可见",
            normalizedSearchQuery ? `搜索：${searchQuery.trim()}` : "未搜索",
  ];
  const canvasStatusSummary = [...appliedFilterChips, ...filterSummary].join(" · ");
  const effectiveTimelineContext = nodeDetail?.timeline_context?.length ? nodeDetail.timeline_context : timelineFocus;
  const backboneTimeline = effectiveTimelineContext.length ? effectiveTimelineContext : timelineFocus;
  const effectiveConnectedNodes = nodeDetail?.connected_nodes ?? [];
  const effectiveActions = nodeDetail?.anchor_actions?.length
    ? [...(activeNode?.inspector.actions ?? []), ...nodeDetail.anchor_actions]
    : activeNode?.inspector.actions ?? [];

  useEffect(() => {
    if (!selectedEdgeKey) return;
    if (!visibleEdges.some((edge) => edgeKey(edge) === selectedEdgeKey)) {
      setSelectedEdgeKey("");
    }
  }, [selectedEdgeKey, visibleEdges]);

  if (!nodes.length) {
    return (
      <div className="space-y-4">
        <Panel className="workbench-header" tone="quiet">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <h1 className="workbench-title">图谱工作台</h1>
              <p className="workbench-lede">
                当前没有足够的事件或人物节点形成图谱。先补充档案、人物或事件，再回到这里编辑关系。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {hasBackendFilters ? (
                <button type="button" onClick={() => onUpdateFilters({}, true)} className="tool-action bg-neon">
                  清空过滤
                </button>
              ) : null}
              <Link href="/library" className="tool-action bg-canvas">
                返回档案库
              </Link>
              <Link href="/timeline" className="tool-action bg-neon">
                打开时间线
              </Link>
            </div>
          </div>
        </Panel>
        <GraphFilterPanel filters={filters} onUpdateFilters={onUpdateFilters} hasBackendFilters={hasBackendFilters} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="workbench-header">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <h1 className="workbench-title">{title}</h1>
            <p className="workbench-lede">{description}</p>
          </div>
          <div className="flex flex-wrap justify-start gap-2 md:justify-end">
            <span className="workbench-stamp bg-canvas">{scope}</span>
            <span className="workbench-stamp bg-peach">事件 {stats.event_count}</span>
            <span className="workbench-stamp bg-aqua">人物 {stats.entity_count}</span>
            <span className="workbench-stamp bg-canvas">节点 {stats.node_count}</span>
            <span className="workbench-stamp bg-gold">连线 {stats.edge_count}</span>
            <span className="workbench-stamp bg-mint">当前 {activeNode?.label ?? "未选择"}</span>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.22fr_0.78fr]">
        <Panel className="p-6 md:p-8" tone="quiet" intensity="quiet">
          <GraphFilterPanel filters={filters} onUpdateFilters={onUpdateFilters} hasBackendFilters={hasBackendFilters} />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="section-kicker">共享画布</p>
            <div className="flex flex-wrap gap-2">
              {[
                { id: "all", label: "全部" },
                { id: "events", label: "事件" },
                { id: "people", label: "人物" },
                { id: "timeline", label: "时间主干" },
              ].map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() => setViewMode(mode.id as GraphWorkspaceViewMode)}
                  className={`border-2 border-ink px-3 py-2 text-xs font-black uppercase tracking-[0.14em] shadow-brutalTiny ${
                    viewMode === mode.id ? "bg-neon" : "bg-canvas"
                  }`}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
            <label className="block">
              <span className="sr-only">搜索图谱节点</span>
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="搜索节点、标签或元信息，回车前即可过滤"
                className="min-w-0 w-full border-4 border-ink bg-canvas px-4 py-3 text-sm font-black shadow-brutalTiny outline-none focus:bg-neon"
              />
            </label>
            <button
              type="button"
              onClick={() => setFocusNeighborhoodOnly((current) => !current)}
              className={`border-4 border-ink px-4 py-3 text-left text-xs font-black uppercase tracking-[0.14em] shadow-brutalTiny ${
                focusNeighborhoodOnly ? "bg-neon" : "bg-canvas"
              }`}
            >
              {focusNeighborhoodOnly ? "仅焦点邻域" : "显示全局"}
            </button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {appliedFilterChips.map((item) => (
              <span key={item} className={hasBackendFilters ? "brutal-chip bg-neon" : "brutal-chip"}>
                {item}
              </span>
            ))}
            {filterSummary.map((item) => (
              <span key={item} className="brutal-chip">
                {item}
              </span>
            ))}
            <span className="brutal-chip">
              可见 {positionedNodes.length}/{allPositionedNodes.length} 节点
            </span>
            <span className="brutal-chip">密度 {(visibleDensity * 100).toFixed(0)}%</span>
          </div>
          <div className="mt-5 grid gap-3 md:hidden">
            {positionedNodes.map((node) => (
              <button
                key={node.id}
                type="button"
                onClick={() => onSelectNode(node.id)}
                className={`graph-node ${
                  activeNodeId === node.id ? "-translate-y-1" : ""
                } ${
                  node.is_anchor ? "bg-neon" : node.node_type === "event" ? "bg-peach" : "bg-aqua"
                }`}
              >
                <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.subtitle}</p>
                <p className="mt-2 text-xl font-black">{node.label}</p>
                {activeNodeId === node.id ? <p className="mt-2 text-xs font-black uppercase tracking-[0.14em]">当前焦点</p> : null}
              </button>
            ))}
            {positionedNodes.length === 0 ? (
              <div className="surface-inset border-4 border-dashed border-ink p-4 text-sm font-bold">
                当前过滤条件下没有可显示节点。清空搜索或切回全局视图即可恢复。
              </div>
            ) : null}
          </div>

          <div className="graph-canvas relative hidden h-[36rem] md:block">
            <div className="pointer-events-none absolute left-4 top-4 z-10 max-w-[calc(100%-2rem)] border-4 border-ink bg-canvas px-4 py-3 shadow-brutalSoft">
              <p className="text-[11px] font-black tracking-[0.16em]">画布状态</p>
              <p className="mt-1 text-sm font-black leading-tight">
                {positionedNodes.length} 节点 / {visibleEdges.length} 连线 / 密度 {(visibleDensity * 100).toFixed(0)}%
              </p>
              <p className="mt-1 break-words text-xs font-bold text-muted">{canvasStatusSummary}</p>
            </div>
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <rect x="0" y="0" width="100" height="100" fill="#fffdf5" />
              <circle cx="50" cy="48" r="18" fill="#fff3c2" opacity="0.42" />
              {visibleEdges.map((edge) => {
                const source = nodeMap.get(edge.source_id);
                const target = nodeMap.get(edge.target_id);
                if (!source || !target) return null;
                const active = activeNodeId ? edge.source_id === activeNodeId || edge.target_id === activeNodeId : false;
                const selected = selectedEdgeKey === edgeKey(edge);
                return (
                  <g key={edgeKey(edge)}>
                    <line
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={selected ? "#d8ff19" : "#0f172a"}
                      strokeWidth={selected ? Math.max(0.55, edge.weight * 1.2) : Math.max(0.22, edge.weight * 0.85)}
                      strokeDasharray={edge.edge_type === "relates_to" ? "1.8 1.2" : undefined}
                      opacity={selected ? 1 : activeNodeId ? (active ? 0.96 : 0.22) : 0.62}
                    />
                    <line
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke="transparent"
                      strokeWidth={6}
                      className="cursor-pointer"
                      onClick={() => setSelectedEdgeKey(edgeKey(edge))}
                    />
                  </g>
                );
              })}
              {positionedNodes.map((node) => (
                <circle
                  key={`${node.id}-dot`}
                  cx={node.x}
                  cy={node.y}
                  r={node.is_anchor ? 4.8 : Math.max(3.2, node.importance * 4.2)}
                  fill="#fff"
                  stroke="#0f172a"
                  strokeWidth="0.55"
                  opacity={activeNodeId && activeNodeId !== node.id ? 0.72 : 1}
                />
              ))}
            </svg>

            <div className="pointer-events-none absolute inset-0">
              {positionedNodes.map((node) => (
                <div
                  key={node.id}
                  className="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2"
                  style={{ left: `${node.x}%`, top: `${node.y}%` }}
                >
                  <button
                    type="button"
                    onClick={() => onSelectNode(node.id)}
                    className={`graph-node w-32 xl:w-36 ${
                      activeNodeId === node.id ? "-translate-y-1" : ""
                    } ${
                      node.tone === "neon" ? "bg-neon" : node.tone === "peach" ? "bg-peach" : node.tone === "aqua" ? "bg-aqua" : "bg-paper"
                    }`}
                  >
                    <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.subtitle}</p>
                    <p className="mt-2 text-sm font-black leading-tight">{node.label}</p>
                  </button>
                </div>
              ))}
              {positionedNodes.length === 0 ? (
                <div className="absolute inset-x-8 top-1/2 -translate-y-1/2 border-4 border-dashed border-ink bg-bone px-5 py-6 text-center shadow-brutalSoft">
                  <p className="text-lg font-black">没有命中过滤条件的节点</p>
                  <p className="mt-2 text-sm font-bold text-muted">清空搜索、关闭焦点邻域，或切回全部视图继续编辑。</p>
                </div>
              ) : null}
            </div>
          </div>

          <div className="mt-5 border-4 border-ink bg-bone p-4 shadow-brutalSoft">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs font-black uppercase tracking-[0.16em]">连线聚焦</p>
              <span className="brutal-chip">可见连线 {visibleEdges.length}</span>
            </div>
            {selectedEdge && selectedEdgeSource && selectedEdgeTarget ? (
              <div className="mt-4 border-4 border-ink bg-neon px-4 py-4 shadow-brutal">
                <p className="text-[11px] font-black uppercase tracking-[0.14em]">
                  {selectedEdge.edge_type} / 权重 {selectedEdge.weight.toFixed(2)}
                </p>
                <p className="mt-2 text-lg font-black leading-tight">
                  {selectedEdgeSource.label} → {selectedEdgeTarget.label}
                </p>
                <p className="mt-2 text-sm font-bold leading-relaxed">{selectedEdge.label}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button type="button" onClick={() => onSelectNode(selectedEdgeSource.id)} className="brutal-action brutal-action-secondary">
                    聚焦源节点
                  </button>
                  <button type="button" onClick={() => onSelectNode(selectedEdgeTarget.id)} className="brutal-action brutal-action-secondary">
                    聚焦目标节点
                  </button>
                  <button type="button" onClick={() => setSelectedEdgeKey("")} className="brutal-action brutal-action-secondary">
                    清除连线焦点
                  </button>
                </div>
              </div>
            ) : (
              <div className="empty-state mt-4">
                <p className="body-copy">
                  点击画布中的任意连线，或在下方列表里挑一条连线，就能快速查看这条关系串起了哪两个节点。
                </p>
              </div>
            )}
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {visibleEdges.map((edge) => {
                const source = nodeMap.get(edge.source_id);
                const target = nodeMap.get(edge.target_id);
                if (!source || !target) return null;
                const selected = selectedEdgeKey === edgeKey(edge);
                return (
                  <button
                    key={`${edgeKey(edge)}-card`}
                    type="button"
                    onClick={() => setSelectedEdgeKey(edgeKey(edge))}
                    className={`border-4 border-ink px-4 py-4 text-left shadow-brutalSoft transition-transform hover:-translate-y-1 ${
                      selected ? "bg-neon" : "bg-canvas"
                    }`}
                  >
                    <p className="text-[11px] font-black uppercase tracking-[0.14em]">
                      {edge.edge_type} / weight {edge.weight.toFixed(2)}
                    </p>
                    <p className="mt-2 text-base font-black leading-tight">
                      {source.label} → {target.label}
                    </p>
                    <p className="mt-2 text-sm font-bold leading-relaxed">{edge.label}</p>
                  </button>
                );
              })}
              {visibleEdges.length === 0 ? (
                <div className="empty-state">
                  当前视图模式下没有可聚焦的连线。
                </div>
              ) : null}
            </div>
          </div>

          <TimelineBackboneRail
            items={backboneTimeline}
            activeEventId={activeNode?.node_type === "event" ? activeNode.id : backboneTimeline[0]?.event_id ?? null}
            selectableEventIds={visibleNodeIds}
            onSelectNode={onSelectNode}
          />
        </Panel>

        <Panel className="p-6" tone="story" intensity="quiet">
          <p className="section-kicker">节点检查器</p>
          {activeNode ? (
            <>
              <p className="mt-4 text-3xl font-black leading-tight">{activeNode.inspector.title}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="brutal-chip">{activeNode.node_type}</span>
                {activeNode.inspector.chips.map((chip) => (
                  <span key={`${activeNode.id}-${chip}`} className="brutal-chip">
                    {chip}
                  </span>
                ))}
              </div>
              <p className="mt-5 text-base font-semibold leading-relaxed text-muted">
                {activeNode.inspector.summary ?? "当前节点还没有补充摘要。"}
              </p>
              <div className="mt-6 space-y-3">
                {activeNode.inspector.context_lines.map((line) => (
                  <div key={`${activeNode.id}-${line}`} className="border-4 border-ink bg-canvas px-4 py-3 shadow-brutalSoft">
                    <p className="text-sm font-bold leading-relaxed">{line}</p>
                  </div>
                ))}
                {nodeDetailLoading ? (
                  <>
                    <div className="border-4 border-ink bg-bone px-4 py-3 shadow-brutalSoft">
                      <div className="h-4 w-32 animate-pulse bg-canvas" />
                    </div>
                    <div className="border-4 border-ink bg-bone px-4 py-3 shadow-brutalSoft">
                      <div className="h-4 w-40 animate-pulse bg-canvas" />
                    </div>
                  </>
                ) : null}
                <div className="border-4 border-ink bg-bone px-4 py-3 shadow-brutalSoft">
                  <p className="text-xs font-black uppercase tracking-[0.16em]">邻接连线</p>
                  <p className="mt-2 text-3xl font-black">{relatedEdges.length}</p>
                </div>
              </div>
              <div className="mt-6 space-y-3">
                <p className="text-xs font-black uppercase tracking-[0.16em]">邻接节点</p>
                {effectiveConnectedNodes.length ? (
                  effectiveConnectedNodes.map((node) => (
                    <button
                      key={`${activeNode.id}-${node.id}`}
                      type="button"
                      onClick={() => onSelectNode(node.id)}
                      className="grid w-full gap-3 border-4 border-ink bg-canvas px-4 py-4 text-left shadow-brutalSoft transition-transform hover:-translate-y-1"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.subtitle}</p>
                          <p className="mt-2 text-xl font-black leading-tight">{node.label}</p>
                        </div>
                        {node.relation_label ? <span className="brutal-chip">{node.relation_label}</span> : null}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <span className="brutal-chip">{node.node_type}</span>
                        {node.meta.slice(0, 2).map((item) => (
                          <span key={`${node.id}-${item}`} className="brutal-chip">
                            {item}
                          </span>
                        ))}
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="surface-inset border-4 border-dashed border-ink p-4 text-sm font-bold">
                    当前节点在这个工作台范围内还没有可继续选中的邻接节点。
                  </div>
                )}
              </div>
              <div className="mt-6 space-y-3">
                <p className="text-xs font-black uppercase tracking-[0.16em]">时间上下文</p>
                {effectiveTimelineContext.length ? (
                  effectiveTimelineContext.map((item) => (
                    <Link
                      key={`${activeNode.id}-${item.kind}-${item.id}`}
                      href={item.href}
                      className="block border-4 border-ink bg-bone px-4 py-4 shadow-brutalSoft transition-transform hover:-translate-y-1"
                    >
                      <p className="text-[11px] font-black uppercase tracking-[0.14em]">{item.kind}</p>
                      <p className="mt-2 text-lg font-black leading-tight">{item.title}</p>
                      <p className="mt-2 text-sm font-bold">{item.display_time ?? "待校时"}</p>
                    </Link>
                  ))
                ) : (
                  <div className="surface-inset border-4 border-dashed border-ink p-4 text-sm font-bold">
                    当前节点还没有额外的时间上下文。
                  </div>
                )}
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                {effectiveActions.map((action) => (
                  <Link
                    key={`${activeNode.id}-${action.href}-${action.action_type}`}
                    href={action.href}
                    className={`brutal-action ${
                      action.variant === "primary"
                        ? "brutal-action-primary"
                        : action.variant === "info"
                          ? "brutal-action-info"
                          : "brutal-action-secondary"
                    }`}
                  >
                    {action.label}
                  </Link>
                ))}
              </div>
              <InlineGraphEditRail
                activeNode={activeNode}
                nodes={nodes}
                curationContext={curationContext}
                curationLoading={curationLoading}
                mutationBusyKey={mutationBusyKey}
                mutationMessage={mutationMessage}
                mutationError={mutationError}
                onDismissMutationMessage={onDismissMutationMessage}
                onDismissMutationError={onDismissMutationError}
                onUpsertEventParticipant={onUpsertEventParticipant}
                onRemoveEventParticipant={onRemoveEventParticipant}
                onUpsertRelation={onUpsertRelation}
                onRemoveRelation={onRemoveRelation}
              />
            </>
          ) : (
            <p className="mt-4 text-base font-bold">当前没有可用节点。</p>
          )}
        </Panel>
      </section>

      <Panel className="p-6" tone="time" intensity="quiet">
        <p className="section-kicker">时间主干展开</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {backboneTimeline.map((item) => (
            visibleNodeIds.has(item.event_id ?? "") ? (
              <button
                key={`${item.kind}-${item.id}`}
                type="button"
                onClick={() => {
                  if (item.event_id) onSelectNode(item.event_id);
                }}
                className="h-full border-4 border-ink bg-canvas px-4 py-4 text-left shadow-brutalSoft transition-transform hover:-translate-y-1"
              >
                <p className="text-[11px] font-black uppercase tracking-[0.14em]">{item.kind}</p>
                <p className="mt-2 text-lg font-black leading-tight">{item.title}</p>
                <p className="mt-2 text-sm font-bold">{item.display_time ?? "待校时"}</p>
              </button>
            ) : (
              <Link key={`${item.kind}-${item.id}`} href={item.href}>
                <div className="h-full border-4 border-ink bg-canvas px-4 py-4 shadow-brutalSoft transition-transform hover:-translate-y-1">
                  <p className="text-[11px] font-black uppercase tracking-[0.14em]">{item.kind}</p>
                  <p className="mt-2 text-lg font-black leading-tight">{item.title}</p>
                  <p className="mt-2 text-sm font-bold">{item.display_time ?? "待校时"}</p>
                </div>
              </Link>
            )
          ))}
          {backboneTimeline.length === 0 ? (
            <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
              当前工作台还没有时间焦点带，等更多事件进入后这里会形成一条可读骨架。
            </div>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}

type TimelineBackboneRailProps = {
  items: TimelineFocusItem[];
  activeEventId: string | null;
  selectableEventIds: Set<string>;
  onSelectNode: (nodeId: string) => void;
};

function TimelineBackboneRail({ items, activeEventId, selectableEventIds, onSelectNode }: TimelineBackboneRailProps) {
  return (
    <div className="mt-5 border-4 border-ink bg-bone px-4 py-4 shadow-brutalSoft">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em]">时间主干</p>
          <p className="mt-2 text-sm font-bold leading-relaxed">
            把时间骨架直接压进图谱工作台里，优先在这里选中事件节点，再决定是否离开当前工作区。
          </p>
        </div>
        <span className="brutal-chip">{items.length} segments</span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {items.length ? (
          items.map((item, index) => {
            const isActive = Boolean(item.event_id && activeEventId && item.event_id === activeEventId);
            const canSelect = Boolean(item.event_id && selectableEventIds.has(item.event_id));

            if (canSelect && item.event_id) {
              return (
                <button
                  key={`${item.kind}-${item.id}`}
                  type="button"
                  onClick={() => onSelectNode(item.event_id!)}
                  className={`border-4 border-ink px-4 py-4 text-left shadow-brutalSoft transition-transform hover:-translate-y-1 ${
                    isActive ? "bg-neon" : "bg-canvas"
                  }`}
                >
                  <p className="text-[11px] font-black uppercase tracking-[0.14em]">
                    #{index + 1} / {item.kind}
                  </p>
                  <p className="mt-2 text-lg font-black leading-tight">{item.title}</p>
                  <p className="mt-2 text-sm font-bold">{item.display_time ?? "待校时"}</p>
                </button>
              );
            }

            return (
              <Link key={`${item.kind}-${item.id}`} href={item.href}>
                <div className="border-4 border-ink bg-canvas px-4 py-4 shadow-brutalSoft transition-transform hover:-translate-y-1">
                  <p className="text-[11px] font-black uppercase tracking-[0.14em]">
                    #{index + 1} / {item.kind}
                  </p>
                  <p className="mt-2 text-lg font-black leading-tight">{item.title}</p>
                  <p className="mt-2 text-sm font-bold">{item.display_time ?? "待校时"}</p>
                </div>
              </Link>
            );
          })
        ) : (
          <div className="surface-inset border-4 border-dashed border-ink p-4 text-sm font-bold">
            当前工作台还没有形成可点击的时间主干。
          </div>
        )}
      </div>
    </div>
  );
}

type InlineGraphEditRailProps = {
  activeNode: GraphNode;
  nodes: GraphNode[];
  curationContext: GraphNodeCurationContext | null;
  curationLoading: boolean;
  mutationBusyKey: string;
  mutationMessage: string;
  mutationError: string;
  onDismissMutationMessage: () => void;
  onDismissMutationError: () => void;
  onUpsertEventParticipant: (eventNodeId: string, payload: GraphParticipantPayload) => Promise<void>;
  onRemoveEventParticipant: (eventNodeId: string, relatedEntityId: string) => Promise<void>;
  onUpsertRelation: (
    nodeType: "event" | "entity",
    nodeId: string,
    payload: GraphRelationPayload,
    relationId?: string
  ) => Promise<void>;
  onRemoveRelation: (nodeType: "event" | "entity", nodeId: string, relationId: string) => Promise<void>;
};

function InlineGraphEditRail({
  activeNode,
  nodes,
  curationContext,
  curationLoading,
  mutationBusyKey,
  mutationMessage,
  mutationError,
  onDismissMutationMessage,
  onDismissMutationError,
  onUpsertEventParticipant,
  onRemoveEventParticipant,
  onUpsertRelation,
  onRemoveRelation,
}: InlineGraphEditRailProps) {
  const [participantForm, setParticipantForm] = useState<GraphParticipantPayload>({
    entity_id: "",
    role: "参与者",
    relation_type: "participates_in",
  });
  const [relationForm, setRelationForm] = useState<GraphRelationPayload>({
    direction: "outgoing",
    related_type: defaultRelatedTypeForNode(activeNode, nodes),
    related_id: "",
    relation_type: activeNode.node_type === "event" ? EVENT_RELATION_TYPE_OPTIONS[0] : ENTITY_RELATION_TYPE_OPTIONS[0],
  });
  const [editingRelationId, setEditingRelationId] = useState("");

  const currentRelations = curationContext?.relations ?? [];
  const currentEditingRelation = currentRelations.find((relation) => relation.id === editingRelationId) ?? null;
  const participantIds =
    curationContext?.kind === "event" ? new Set(curationContext.participants.map((participant) => participant.id)) : new Set<string>();
  const participantOptions = nodes.filter((node) => node.node_type === "entity" && node.id !== activeNode.id && !participantIds.has(node.id));
  const relationTypeOptions = activeNode.node_type === "event" ? EVENT_RELATION_TYPE_OPTIONS : ENTITY_RELATION_TYPE_OPTIONS;
  const relationTargetTypeChoices = ["event", "entity"].filter((choice) => {
    if (choice === currentEditingRelation?.peer.object_type) return true;
    return nodes.some((node) => node.id !== activeNode.id && node.node_type === choice);
  });

  const relationTargetOptions = useMemo(() => {
    const baseOptions = nodes
      .filter((node) => node.id !== activeNode.id && node.node_type === relationForm.related_type)
      .map((node) => ({
        id: node.id,
        label: `${node.label} / ${node.subtitle}`,
      }));

    if (
      currentEditingRelation &&
      currentEditingRelation.peer.object_type === relationForm.related_type &&
      !baseOptions.some((option) => option.id === currentEditingRelation.peer.id)
    ) {
      baseOptions.unshift({
        id: currentEditingRelation.peer.id,
        label: [currentEditingRelation.peer.subtitle, currentEditingRelation.peer.label].filter(Boolean).join(" / "),
      });
    }

    return baseOptions;
  }, [activeNode.id, currentEditingRelation, nodes, relationForm.related_type]);

  useEffect(() => {
    setEditingRelationId("");
    setParticipantForm({
      entity_id: "",
      role: "参与者",
      relation_type: "participates_in",
    });
    setRelationForm({
      direction: "outgoing",
      related_type: defaultRelatedTypeForNode(activeNode, nodes),
      related_id: "",
      relation_type: activeNode.node_type === "event" ? EVENT_RELATION_TYPE_OPTIONS[0] : ENTITY_RELATION_TYPE_OPTIONS[0],
    });
  }, [activeNode.id, activeNode.node_type, nodes]);

  useEffect(() => {
    if (!relationTargetTypeChoices.includes(relationForm.related_type)) {
      setRelationForm((current) => ({
        ...current,
        related_type: relationTargetTypeChoices[0] ?? "event",
        related_id: "",
      }));
    }
  }, [relationForm.related_type, relationTargetTypeChoices]);

  useEffect(() => {
    if (participantOptions.length === 0) {
      if (participantForm.entity_id) {
        setParticipantForm((current) => ({ ...current, entity_id: "" }));
      }
      return;
    }
    if (!participantOptions.some((option) => option.id === participantForm.entity_id)) {
      setParticipantForm((current) => ({ ...current, entity_id: participantOptions[0]?.id ?? "" }));
    }
  }, [participantForm.entity_id, participantOptions]);

  useEffect(() => {
    if (relationTargetOptions.length === 0) {
      if (relationForm.related_id) {
        setRelationForm((current) => ({ ...current, related_id: "" }));
      }
      return;
    }
    if (!relationTargetOptions.some((option) => option.id === relationForm.related_id)) {
      setRelationForm((current) => ({ ...current, related_id: relationTargetOptions[0]?.id ?? "" }));
    }
  }, [relationForm.related_id, relationTargetOptions]);

  async function handleParticipantSubmit() {
    if (curationContext?.kind !== "event" || !participantForm.entity_id) return;
    await onUpsertEventParticipant(curationContext.event.id, participantForm);
    setParticipantForm({
      entity_id: "",
      role: "参与者",
      relation_type: "participates_in",
    });
  }

  async function handleRelationSubmit() {
    if (!curationContext || !relationForm.related_id) return;
    const nodeId = curationContext.kind === "event" ? curationContext.event.id : curationContext.entity.id;
    await onUpsertRelation(curationContext.kind, nodeId, relationForm, editingRelationId || undefined);
    setEditingRelationId("");
    setRelationForm({
      direction: "outgoing",
      related_type: defaultRelatedTypeForNode(activeNode, nodes),
      related_id: "",
      relation_type: activeNode.node_type === "event" ? EVENT_RELATION_TYPE_OPTIONS[0] : ENTITY_RELATION_TYPE_OPTIONS[0],
    });
  }

  function beginRelationEdit(relation: GraphRelationItem) {
    setEditingRelationId(relation.id);
    setRelationForm({
      direction: relation.direction,
      related_type: relation.peer.object_type,
      related_id: relation.peer.id,
      relation_type: relation.relation_type,
    });
  }

  function cancelRelationEdit() {
    setEditingRelationId("");
    setRelationForm({
      direction: "outgoing",
      related_type: defaultRelatedTypeForNode(activeNode, nodes),
      related_id: "",
      relation_type: activeNode.node_type === "event" ? EVENT_RELATION_TYPE_OPTIONS[0] : ENTITY_RELATION_TYPE_OPTIONS[0],
    });
  }

  const fullCurationHref = activeNode.node_type === "event" ? `/curation/events/${activeNode.id}` : `/curation/entities/${activeNode.id}`;

  return (
    <div className="mt-8 space-y-4 border-t-4 border-ink pt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em]">Inline Curation</p>
          <p className="mt-2 text-base font-bold leading-relaxed">
            在当前图谱节点下直接调整参与者和关系，提交后会立即刷新这个工作台。
          </p>
        </div>
        <Link href={fullCurationHref} className="brutal-action brutal-action-secondary">
          打开完整校对页
        </Link>
      </div>

      {mutationMessage ? (
        <div className="border-4 border-ink bg-green-200 px-4 py-3 shadow-brutal">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-bold leading-relaxed">{mutationMessage}</p>
            <button type="button" onClick={onDismissMutationMessage} className="text-sm font-black uppercase tracking-[0.14em]">
              关闭
            </button>
          </div>
        </div>
      ) : null}

      {mutationError ? (
        <div className="border-4 border-ink bg-red-200 px-4 py-3 shadow-brutal">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-bold leading-relaxed">{mutationError}</p>
            <button type="button" onClick={onDismissMutationError} className="text-sm font-black uppercase tracking-[0.14em]">
              关闭
            </button>
          </div>
        </div>
      ) : null}

      {curationLoading ? (
        <div className="border-4 border-ink bg-paper px-4 py-4 shadow-brutal">
          <div className="h-4 w-36 animate-pulse bg-white" />
          <div className="mt-3 h-16 animate-pulse border-4 border-dashed border-ink bg-white" />
        </div>
      ) : null}

      {!curationLoading && !curationContext ? (
        <div className="surface-inset border-4 border-dashed border-ink p-4 text-sm font-bold">
          当前节点暂时没有可用的内联治理上下文，你仍然可以先跳到完整校对页继续操作。
        </div>
      ) : null}

      {curationContext?.kind === "event" ? (
        <div className="space-y-4">
          <div className="border-4 border-ink bg-white px-4 py-4 shadow-brutal">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-black uppercase tracking-[0.16em]">参与者治理</p>
              <span className="brutal-chip">{curationContext.stats.participant_count} participants</span>
            </div>
            <div className="mt-4 space-y-3">
              {curationContext.participants.length ? (
                curationContext.participants.map((participant) => (
                  <div key={`${curationContext.event.id}-${participant.id}`} className="border-4 border-ink bg-paper px-4 py-4 shadow-brutal">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-[11px] font-black uppercase tracking-[0.14em]">{participant.entity_type}</p>
                        <p className="mt-2 text-lg font-black leading-tight">{participant.display_name}</p>
                        <p className="mt-2 text-sm font-bold">
                          {[participant.role ?? "未标注角色", participant.relation_type ?? "participates_in"].join(" / ")}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          if (window.confirm(`确认移除 ${participant.display_name} 吗？`)) {
                            void onRemoveEventParticipant(curationContext.event.id, participant.id);
                          }
                        }}
                        disabled={mutationBusyKey === `participant-remove-${curationContext.event.id}-${participant.id}`}
                        className="brutal-action brutal-action-secondary disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        移除
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="surface-inset border-4 border-dashed border-ink p-4 text-sm font-bold">
                  当前事件还没有参与者记录。
                </div>
              )}
            </div>
            <div className="mt-4 grid gap-3">
              <select
                value={participantForm.entity_id}
                onChange={(event) => setParticipantForm((current) => ({ ...current, entity_id: event.target.value }))}
                className="border-4 border-ink bg-paper px-3 py-3 text-sm font-bold"
              >
                {participantOptions.length ? (
                  participantOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label} / {option.subtitle}
                    </option>
                  ))
                ) : (
                  <option value="">当前工作台没有可补充的人物节点</option>
                )}
              </select>
              {participantOptions.length === 0 ? (
                <p className="text-sm font-bold leading-relaxed">
                  当前图谱邻域里没有更多人物节点可加为参与者。需要更大范围的补充时，请打开完整校对页。
                </p>
              ) : null}
              <input
                value={participantForm.role ?? ""}
                onChange={(event) => setParticipantForm((current) => ({ ...current, role: event.target.value }))}
                placeholder="角色，例如：主持人"
                className="border-4 border-ink bg-paper px-3 py-3 text-sm font-bold"
              />
              <input
                value={participantForm.relation_type ?? ""}
                onChange={(event) => setParticipantForm((current) => ({ ...current, relation_type: event.target.value }))}
                placeholder="关系类型，例如：participates_in"
                className="border-4 border-ink bg-paper px-3 py-3 text-sm font-bold"
              />
              <button
                type="button"
                onClick={() => void handleParticipantSubmit()}
                disabled={!participantOptions.length || !participantForm.entity_id || mutationBusyKey === `participant-submit-${curationContext.event.id}`}
                className="brutal-action brutal-action-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                {mutationBusyKey === `participant-submit-${curationContext.event.id}` ? "写入中..." : "添加参与者"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {curationContext ? (
        <div className="border-4 border-ink bg-white px-4 py-4 shadow-brutal">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-black uppercase tracking-[0.16em]">关系治理</p>
            <span className="brutal-chip">{curationContext.stats.relation_count} relations</span>
          </div>
          <div className="mt-4 space-y-3">
            {curationContext.relations.length ? (
              curationContext.relations.map((relation) => {
                const canEditInline = relation.peer.object_type === "event" || relation.peer.object_type === "entity";
                const nodeId = curationContext.kind === "event" ? curationContext.event.id : curationContext.entity.id;
                return (
                  <div key={relation.id} className="border-4 border-ink bg-paper px-4 py-4 shadow-brutal">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-[11px] font-black uppercase tracking-[0.14em]">
                          {relation.direction} / {relation.peer.object_type}
                        </p>
                        <p className="mt-2 text-lg font-black leading-tight">{relation.peer.label}</p>
                        <p className="mt-2 text-sm font-bold">
                          {[relation.relation_type, relation.peer.subtitle].filter(Boolean).join(" / ")}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {canEditInline ? (
                          <button
                            type="button"
                            onClick={() => beginRelationEdit(relation)}
                            className="brutal-action brutal-action-secondary"
                          >
                            编辑
                          </button>
                        ) : null}
                        <button
                          type="button"
                          onClick={() => {
                            if (window.confirm(`确认删除与 ${relation.peer.label} 的这条关系吗？`)) {
                              void onRemoveRelation(curationContext.kind, nodeId, relation.id);
                            }
                          }}
                          disabled={mutationBusyKey === `relation-remove-${relation.id}`}
                          className="brutal-action brutal-action-secondary disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="surface-inset border-4 border-dashed border-ink p-4 text-sm font-bold">
                当前节点还没有额外的治理关系。
              </div>
            )}
          </div>

          <div className="mt-4 grid gap-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <select
                value={relationForm.direction}
                onChange={(event) => setRelationForm((current) => ({ ...current, direction: event.target.value }))}
                className="border-4 border-ink bg-paper px-3 py-3 text-sm font-bold"
              >
                <option value="outgoing">outgoing</option>
                <option value="incoming">incoming</option>
              </select>
              <select
                value={relationForm.related_type}
                onChange={(event) =>
                  setRelationForm((current) => ({
                    ...current,
                    related_type: event.target.value,
                    related_id: "",
                  }))
                }
                className="border-4 border-ink bg-paper px-3 py-3 text-sm font-bold"
              >
                {relationTargetTypeChoices.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            <select
              value={relationForm.related_id}
              onChange={(event) => setRelationForm((current) => ({ ...current, related_id: event.target.value }))}
              className="border-4 border-ink bg-paper px-3 py-3 text-sm font-bold"
            >
              {relationTargetOptions.length ? (
                relationTargetOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))
              ) : (
                <option value="">当前工作台没有可选的关系目标</option>
              )}
            </select>
            {relationTargetOptions.length === 0 ? (
              <p className="text-sm font-bold leading-relaxed">
                当前视图模式下没有可写入的关系目标。你可以切回 `全部` 或 `事件 / 人物` 视图，或者进入完整校对页。
              </p>
            ) : null}

            <select
              value={relationForm.relation_type}
              onChange={(event) => setRelationForm((current) => ({ ...current, relation_type: event.target.value }))}
              className="border-4 border-ink bg-paper px-3 py-3 text-sm font-bold"
            >
              {relationTypeOptions.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => void handleRelationSubmit()}
                disabled={!relationForm.related_id || mutationBusyKey === `relation-submit-${curationContext.kind}-${curationContext.kind === "event" ? curationContext.event.id : curationContext.entity.id}`}
                className="brutal-action brutal-action-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                {mutationBusyKey === `relation-submit-${curationContext.kind}-${curationContext.kind === "event" ? curationContext.event.id : curationContext.entity.id}`
                  ? "写入中..."
                  : editingRelationId
                    ? "更新关系"
                    : "添加关系"}
              </button>
              {editingRelationId ? (
                <button type="button" onClick={cancelRelationEdit} className="brutal-action brutal-action-secondary">
                  取消编辑
                </button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
