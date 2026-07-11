"use client";

import { FormEvent, startTransition, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { AuthGate } from "@/components/auth-gate";
import { AddToCollectionControl } from "@/components/add-to-collection-control";
import { GraphWorkspaceShell } from "@/components/graph-workspace-shell";
import { ManualEvidencePanel } from "@/components/manual-evidence-panel";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type GraphWorkspaceData = {
  scope: string;
  title: string;
  description: string;
  anchor: {
    id: string;
    node_type: string;
    label: string;
    subtitle: string;
    href: string;
  } | null;
  nodes: Array<{
    id: string;
    node_type: string;
    label: string;
    subtitle: string;
    href: string;
    importance: number;
    meta: string[];
    is_anchor: boolean;
    inspector: {
      id: string;
      node_type: string;
      title: string;
      summary: string | null;
      chips: string[];
      context_lines: string[];
      actions: Array<{
        label: string;
        href: string;
        action_type: string;
        variant: string;
      }>;
    };
  }>;
  edges: Array<{
    id: string;
    relation_id: string | null;
    fact_type: string;
    source_id: string;
    target_id: string;
    source_type: string | null;
    target_type: string | null;
    edge_type: string;
    label: string;
    weight: number;
    evidence_count: number;
    is_editable: boolean;
  }>;
  timeline_focus: Array<{
    id: string;
    event_id: string | null;
    title: string;
    display_time: string | null;
    href: string;
    kind: string;
  }>;
  stats: {
    node_count: number;
    edge_count: number;
    event_count: number;
    entity_count: number;
    timeline_count: number;
    conflict_count: number;
    low_confidence_edge_count: number;
    orphan_node_count: number;
  };
  filters: GraphWorkspaceFilters;
  conflicts: GraphConflict[];
  recent_actions: GraphActionLog[];
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

type GraphNodeDetail = {
  node: GraphWorkspaceData["nodes"][number];
  connected_nodes: Array<{
    id: string;
    node_type: string;
    label: string;
    subtitle: string;
    href: string;
    meta: string[];
    relation_label: string | null;
    is_anchor: boolean;
  }>;
  connected_edges: Array<{
    id: string;
    relation_id: string | null;
    fact_type: string;
    source_id: string;
    target_id: string;
    source_type: string | null;
    target_type: string | null;
    edge_type: string;
    label: string;
    weight: number;
    evidence_count: number;
    is_editable: boolean;
  }>;
  timeline_context: GraphWorkspaceData["timeline_focus"];
  anchor_actions: Array<{
    label: string;
    href: string;
    action_type: string;
    variant: string;
  }>;
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

type EventParticipantItem = {
  id: string;
  display_name: string;
  entity_type: string;
  role: string | null;
  relation_type: string | null;
};

type EventNodeCurationContext = {
  kind: "event";
  event: {
    id: string;
    title: string;
    summary: string | null;
    event_type: string | null;
    status: string | null;
  };
  participants: EventParticipantItem[];
  relations: GraphRelationItem[];
  stats: {
    participant_count: number;
    relation_count: number;
  };
};

type EntityNodeCurationContext = {
  kind: "entity";
  entity: {
    id: string;
    display_name: string;
    entity_type: string;
    description: string | null;
    status: string;
  };
  relations: GraphRelationItem[];
  stats: {
    relation_count: number;
  };
};

type GraphNodeCurationContext = EventNodeCurationContext | EntityNodeCurationContext;

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

type GraphNodeUpdatePayload = {
  title?: string;
  summary?: string | null;
  type?: string | null;
  status?: string | null;
};

type GraphConflict = {
  id: string;
  severity: string;
  conflict_type: string;
  title: string;
  summary: string;
  node_ids: string[];
  edge_label: string | null;
  href: string;
  disposition: "open" | "keep" | "snooze";
  disposition_note: string | null;
  is_active: boolean;
  actions: Array<{
    label: string;
    action_type: string;
    relation_id: string;
    owner_type: "event" | "entity";
    owner_id: string;
  }>;
};

type GraphActionLog = {
  id: string;
  target_type: string;
  target_id: string;
  action_type: string;
  status_before: string | null;
  status_after: string | null;
  created_at: string | null;
  summary: string;
  diff_summary: string | null;
};

type GraphViewpoint = {
  id: string;
  name: string;
  description: string | null;
  scope: string;
  anchor_type: string | null;
  anchor_id: string | null;
  filters_json: Record<string, unknown>;
  layout_json: Record<string, unknown>;
  href: string;
  created_at: string | null;
  updated_at: string | null;
};

type GraphPath = {
  found: boolean;
  max_depth: number;
  total_hops: number;
  source: { id: string; node_type: string; label: string; href: string };
  target: { id: string; node_type: string; label: string; href: string };
  nodes: Array<{ id: string; node_type: string; label: string; href: string }>;
  edges: Array<{
    source_type: string;
    source_id: string;
    target_type: string;
    target_id: string;
    label: string;
    fact_type: string;
    relation_id: string | null;
    evidence_count: number;
    confidence: number | null;
    traversal_direction: string;
    explanation: string;
  }>;
  explanation: string;
};

type GraphManualNodeResult = {
  node_type: "entity" | "event";
  node_id: string;
  label: string;
  connection_type: string;
  graph_href: string;
};

export function GraphPageClient() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const eventId = searchParams?.get("event_id") ?? null;
  const entityId = searchParams?.get("entity_id") ?? null;
  const collectionId = searchParams?.get("collection_id") ?? null;
  const activeNodeIdFromUrl = searchParams?.get("active_node_id") ?? null;
  const nodeTypesFilter = searchParams?.get("node_types") ?? "";
  const relationTypesFilter = searchParams?.get("relation_types") ?? "";
  const startFilter = searchParams?.get("start") ?? "";
  const endFilter = searchParams?.get("end") ?? "";
  const minWeightFilter = searchParams?.get("min_weight") ?? "";
  const depthFilter = searchParams?.get("depth") ?? "";
  const [workspace, setWorkspace] = useState<GraphWorkspaceData | null>(null);
  const [nodeDetail, setNodeDetail] = useState<GraphNodeDetail | null>(null);
  const [nodeDetailLoading, setNodeDetailLoading] = useState(false);
  const [curationContext, setCurationContext] = useState<GraphNodeCurationContext | null>(null);
  const [curationLoading, setCurationLoading] = useState(false);
  const [mutationBusyKey, setMutationBusyKey] = useState("");
  const [mutationMessage, setMutationMessage] = useState("");
  const [mutationError, setMutationError] = useState("");
  const [viewpoints, setViewpoints] = useState<GraphViewpoint[]>([]);
  const [viewpointName, setViewpointName] = useState("");
  const [viewpointBusy, setViewpointBusy] = useState(false);
  const [viewpointActionBusyKey, setViewpointActionBusyKey] = useState("");
  const [viewpointMessage, setViewpointMessage] = useState("");
  const [graphPath, setGraphPath] = useState<GraphPath | null>(null);
  const [graphPathBusy, setGraphPathBusy] = useState(false);
  const [graphPathError, setGraphPathError] = useState("");
  const [error, setError] = useState("");

  function buildScopeParams() {
    const params = new URLSearchParams();
    if (eventId) params.set("event_id", eventId);
    if (entityId) params.set("entity_id", entityId);
    if (collectionId) params.set("collection_id", collectionId);
    if (nodeTypesFilter) params.set("node_types", nodeTypesFilter);
    if (relationTypesFilter) params.set("relation_types", relationTypesFilter);
    if (startFilter) params.set("start", startFilter);
    if (endFilter) params.set("end", endFilter);
    if (minWeightFilter) params.set("min_weight", minWeightFilter);
    if (depthFilter) params.set("depth", depthFilter);
    return params;
  }

  async function fetchWorkspaceData(): Promise<GraphWorkspaceData> {
    const query = buildScopeParams().toString();
    return apiFetch<GraphWorkspaceData>(`/graph/workspace${query ? `?${query}` : ""}`);
  }

  async function fetchGraphViewpoints(): Promise<GraphViewpoint[]> {
    const data = await apiFetch<{ items: GraphViewpoint[]; total: number }>("/graph-viewpoints");
    return data.items;
  }

  async function fetchNodeDetailData(node: GraphWorkspaceData["nodes"][number]): Promise<GraphNodeDetail> {
    const query = buildScopeParams().toString();
    return apiFetch<GraphNodeDetail>(`/graph/nodes/${node.node_type}/${node.id}${query ? `?${query}` : ""}`);
  }

  async function fetchCurationContextData(
    node: GraphWorkspaceData["nodes"][number]
  ): Promise<GraphNodeCurationContext | null> {
    if (node.node_type === "event") {
      const data = await apiFetch<{
        event: { id: string; title: string; summary: string | null; event_type: string | null; status: string | null };
        participants: EventParticipantItem[];
        relations: GraphRelationItem[];
        stats: { participant_count: number; relation_count: number };
      }>(`/curation/events/${node.id}`);
      return {
        kind: "event",
        event: data.event,
        participants: data.participants,
        relations: data.relations,
        stats: data.stats,
      };
    }
    if (node.node_type === "entity") {
      const data = await apiFetch<{
        entity: { id: string; display_name: string; entity_type: string; description: string | null; status: string };
        relations: GraphRelationItem[];
        stats: { relation_count: number };
      }>(`/curation/entities/${node.id}`);
      return {
        kind: "entity",
        entity: data.entity,
        relations: data.relations,
        stats: data.stats,
      };
    }
    return null;
  }

  async function refreshGraphStateForNode(nodeType: string, nodeId: string) {
    const refreshedWorkspace = await fetchWorkspaceData();
    const refreshedNode =
      refreshedWorkspace.nodes.find((node) => node.id === nodeId && node.node_type === nodeType) ?? null;

    startTransition(() => {
      setWorkspace(refreshedWorkspace);
      setNodeDetail(null);
      setCurationContext(null);
    });

    if (!refreshedNode) {
      return;
    }

    const [detail, curation] = await Promise.all([
      fetchNodeDetailData(refreshedNode).catch(() => null),
      fetchCurationContextData(refreshedNode).catch(() => null),
    ]);
    startTransition(() => {
      setNodeDetail(detail);
      setCurationContext(curation);
    });
  }

  useEffect(() => {
    Promise.all([fetchWorkspaceData(), fetchGraphViewpoints().catch(() => [])])
      .then(([data, viewpointData]) => {
        startTransition(() => {
          setWorkspace(data);
          setViewpoints(viewpointData);
          setNodeDetail(null);
          setCurationContext(null);
          setError("");
        });
      })
      .catch((err) => {
        startTransition(() => {
          setWorkspace(null);
          setNodeDetail(null);
          setCurationContext(null);
          setError(err instanceof Error ? err.message : "图谱工作台加载失败");
        });
      });
  }, [collectionId, depthFilter, endFilter, entityId, eventId, minWeightFilter, nodeTypesFilter, relationTypesFilter, startFilter]);

  const activeNode = useMemo(() => {
    if (!workspace?.nodes.length) return null;
    if (activeNodeIdFromUrl) {
      return workspace.nodes.find((node) => node.id === activeNodeIdFromUrl) ?? null;
    }
    return workspace.nodes.find((node) => node.is_anchor) ?? workspace.nodes[0] ?? null;
  }, [activeNodeIdFromUrl, workspace]);

  useEffect(() => {
    if (!workspace?.nodes.length || !activeNode) return;

    const params = new URLSearchParams(searchParams?.toString() ?? "");
    if (params.get("active_node_id") !== activeNode.id) {
      params.set("active_node_id", activeNode.id);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    }
  }, [activeNode, pathname, router, searchParams, workspace]);

  useEffect(() => {
    if (!activeNode) {
      startTransition(() => {
        setNodeDetail(null);
        setCurationContext(null);
      });
      return;
    }

    setNodeDetailLoading(true);
    fetchNodeDetailData(activeNode)
      .then((data) => {
        startTransition(() => {
          setNodeDetail(data);
        });
      })
      .catch(() => {
        startTransition(() => {
          setNodeDetail(null);
        });
      })
      .finally(() => {
        setNodeDetailLoading(false);
      });
  }, [activeNode, collectionId, depthFilter, endFilter, entityId, eventId, minWeightFilter, nodeTypesFilter, relationTypesFilter, startFilter]);

  useEffect(() => {
    if (!activeNode) {
      startTransition(() => {
        setCurationContext(null);
      });
      return;
    }

    setCurationLoading(true);
    fetchCurationContextData(activeNode)
      .then((data) => {
        startTransition(() => {
          setCurationContext(data);
        });
      })
      .catch(() => {
        startTransition(() => {
          setCurationContext(null);
        });
      })
      .finally(() => {
        setCurationLoading(false);
      });
  }, [activeNode]);

  function handleSelectNode(nodeId: string) {
    setGraphPath(null);
    setGraphPathError("");
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    params.set("active_node_id", nodeId);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  function handleUpdateFilters(updates: Partial<GraphWorkspaceAppliedFilters>, reset = false) {
    const params = new URLSearchParams(reset ? "" : (searchParams?.toString() ?? ""));
    if (eventId) params.set("event_id", eventId);
    if (entityId) params.set("entity_id", entityId);
    if (collectionId) params.set("collection_id", collectionId);
    params.delete("active_node_id");

    const nextFilters: GraphWorkspaceAppliedFilters = {
      node_types: updates.node_types ?? (reset ? [] : workspace?.filters.applied.node_types ?? []),
      relation_types: updates.relation_types ?? (reset ? [] : workspace?.filters.applied.relation_types ?? []),
      start: updates.start ?? (reset ? null : workspace?.filters.applied.start ?? null),
      end: updates.end ?? (reset ? null : workspace?.filters.applied.end ?? null),
      min_weight: updates.min_weight ?? (reset ? 0 : workspace?.filters.applied.min_weight ?? 0),
      depth: updates.depth ?? (reset ? 0 : workspace?.filters.applied.depth ?? 0),
    };

    if (nextFilters.node_types.length) params.set("node_types", nextFilters.node_types.join(","));
    else params.delete("node_types");
    if (nextFilters.relation_types.length) params.set("relation_types", nextFilters.relation_types.join(","));
    else params.delete("relation_types");
    if (nextFilters.start) params.set("start", nextFilters.start.slice(0, 10));
    else params.delete("start");
    if (nextFilters.end) params.set("end", nextFilters.end.slice(0, 10));
    else params.delete("end");
    if (nextFilters.min_weight > 0) params.set("min_weight", String(nextFilters.min_weight));
    else params.delete("min_weight");
    if (nextFilters.depth > 0) params.set("depth", String(nextFilters.depth));
    else params.delete("depth");

    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  async function handleUpsertEventParticipant(eventNodeId: string, payload: GraphParticipantPayload) {
    setMutationBusyKey(`participant-submit-${eventNodeId}`);
    try {
      await apiFetch(`/curation/events/${eventNodeId}/participants`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await refreshGraphStateForNode("event", eventNodeId);
      startTransition(() => {
        setMutationMessage("事件参与者已在图谱工作台内更新。");
        setMutationError("");
      });
    } catch (err) {
      startTransition(() => {
        setMutationError(err instanceof Error ? err.message : "事件参与者更新失败");
      });
    } finally {
      setMutationBusyKey("");
    }
  }

  async function handleRemoveEventParticipant(eventNodeId: string, relatedEntityId: string) {
    setMutationBusyKey(`participant-remove-${eventNodeId}-${relatedEntityId}`);
    try {
      await apiFetch(`/curation/events/${eventNodeId}/participants/${relatedEntityId}`, {
        method: "DELETE",
      });
      await refreshGraphStateForNode("event", eventNodeId);
      startTransition(() => {
        setMutationMessage("事件参与者已从图谱里移除。");
        setMutationError("");
      });
    } catch (err) {
      startTransition(() => {
        setMutationError(err instanceof Error ? err.message : "移除事件参与者失败");
      });
    } finally {
      setMutationBusyKey("");
    }
  }

  async function handleUpsertRelation(
    nodeType: "event" | "entity",
    nodeId: string,
    payload: GraphRelationPayload,
    relationId?: string
  ) {
    setMutationBusyKey(`relation-submit-${nodeType}-${nodeId}`);
    const basePath = nodeType === "event" ? `/curation/events/${nodeId}/relations` : `/curation/entities/${nodeId}/relations`;
    try {
      await apiFetch(relationId ? `${basePath}/${relationId}` : basePath, {
        method: relationId ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      await refreshGraphStateForNode(nodeType, nodeId);
      startTransition(() => {
        setMutationMessage(relationId ? "图谱关系已在当前工作台更新。" : "新的图谱关系已写入当前工作台。");
        setMutationError("");
      });
    } catch (err) {
      startTransition(() => {
        setMutationError(err instanceof Error ? err.message : relationId ? "图谱关系更新失败" : "图谱关系写入失败");
      });
    } finally {
      setMutationBusyKey("");
    }
  }

  async function handleRemoveRelation(nodeType: "event" | "entity", nodeId: string, relationId: string) {
    setMutationBusyKey(`relation-remove-${relationId}`);
    const basePath = nodeType === "event" ? `/curation/events/${nodeId}/relations` : `/curation/entities/${nodeId}/relations`;
    try {
      await apiFetch(`${basePath}/${relationId}`, { method: "DELETE" });
      await refreshGraphStateForNode(nodeType, nodeId);
      startTransition(() => {
        setMutationMessage("图谱关系已删除。");
        setMutationError("");
      });
    } catch (err) {
      startTransition(() => {
        setMutationError(err instanceof Error ? err.message : "图谱关系删除失败");
      });
    } finally {
      setMutationBusyKey("");
    }
  }

  async function handleUpdateNode(nodeType: "event" | "entity", nodeId: string, payload: GraphNodeUpdatePayload) {
    const normalized =
      nodeType === "event"
        ? {
            title: payload.title,
            summary: payload.summary,
            event_type: payload.type,
            status: payload.status,
          }
        : {
            display_name: payload.title,
            description: payload.summary,
            entity_type: payload.type,
            status: payload.status,
          };
    setMutationBusyKey(`node-update-${nodeType}-${nodeId}`);
    try {
      await apiFetch(`/curation/${nodeType === "event" ? "events" : "entities"}/${nodeId}`, {
        method: "PATCH",
        body: JSON.stringify(normalized),
      });
      await refreshGraphStateForNode(nodeType, nodeId);
      startTransition(() => {
        setMutationMessage("节点基础信息已更新，图谱工作台已刷新。");
        setMutationError("");
      });
    } catch (err) {
      startTransition(() => {
        setMutationError(err instanceof Error ? err.message : "节点基础信息更新失败");
      });
    } finally {
      setMutationBusyKey("");
    }
  }

  async function handleSaveViewpoint() {
    if (!workspace) return;
    const name = viewpointName.trim() || `${workspace.title} ${new Date().toLocaleString("zh-CN")}`;
    const filtersJson = {
      ...workspace.filters.applied,
      active_node_id: activeNode?.id ?? null,
    };
    setViewpointBusy(true);
    try {
      const created = await apiFetch<GraphViewpoint>("/graph-viewpoints", {
        method: "POST",
        body: JSON.stringify({
          name,
          description: workspace.description,
          scope: workspace.scope,
          anchor_type: workspace.anchor?.node_type ?? null,
          anchor_id: workspace.anchor?.id ?? null,
          filters_json: filtersJson,
          layout_json: {
            active_node_id: activeNode?.id ?? null,
          },
        }),
      });
      startTransition(() => {
        setViewpoints((current) => [created, ...current.filter((item) => item.id !== created.id)].slice(0, 20));
        setViewpointName("");
        setViewpointMessage("当前图谱视角已保存。");
      });
    } catch (err) {
      startTransition(() => {
        setViewpointMessage(err instanceof Error ? err.message : "保存图谱视角失败");
      });
    } finally {
      setViewpointBusy(false);
    }
  }

  async function handleRenameViewpoint(viewpointId: string, name: string) {
    const cleanedName = name.trim();
    if (!cleanedName) return;
    setViewpointActionBusyKey(`viewpoint-rename-${viewpointId}`);
    try {
      const updated = await apiFetch<GraphViewpoint>(`/graph-viewpoints/${viewpointId}`, {
        method: "PATCH",
        body: JSON.stringify({ name: cleanedName }),
      });
      startTransition(() => {
        setViewpoints((current) => current.map((item) => (item.id === viewpointId ? updated : item)));
        setViewpointMessage("保存视角已重命名。");
      });
    } catch (err) {
      setViewpointMessage(err instanceof Error ? err.message : "重命名保存视角失败");
    } finally {
      setViewpointActionBusyKey("");
    }
  }

  async function handleDeleteViewpoint(viewpointId: string) {
    setViewpointActionBusyKey(`viewpoint-delete-${viewpointId}`);
    try {
      await apiFetch(`/graph-viewpoints/${viewpointId}`, { method: "DELETE" });
      startTransition(() => {
        setViewpoints((current) => current.filter((item) => item.id !== viewpointId));
        setViewpointMessage("保存视角已删除。");
      });
    } catch (err) {
      setViewpointMessage(err instanceof Error ? err.message : "删除保存视角失败");
    } finally {
      setViewpointActionBusyKey("");
    }
  }

  async function handleSetConflictDisposition(
    conflict: GraphConflict,
    disposition: "open" | "keep" | "snooze",
    note?: string
  ) {
    setMutationBusyKey(`conflict-disposition-${conflict.id}`);
    try {
      await apiFetch(`/graph/conflicts/${encodeURIComponent(conflict.id)}/disposition`, {
        method: "POST",
        body: JSON.stringify({
          disposition,
          note: note?.trim() || null,
          conflict_type: conflict.conflict_type,
          title: conflict.title,
          summary: conflict.summary,
          node_ids: conflict.node_ids,
          edge_label: conflict.edge_label,
        }),
      });
      const refreshed = await fetchWorkspaceData();
      startTransition(() => {
        setWorkspace(refreshed);
        setMutationMessage(
          disposition === "keep" ? "冲突已确认保留，不会修改原关系。" : disposition === "snooze" ? "冲突已稍后处理。" : "冲突已重新打开。"
        );
        setMutationError("");
      });
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "冲突处置失败");
    } finally {
      setMutationBusyKey("");
    }
  }

  async function handleFindPath(
    source: GraphWorkspaceData["nodes"][number],
    target: GraphWorkspaceData["nodes"][number],
    maxDepth: number
  ) {
    const params = new URLSearchParams({
      source_type: source.node_type,
      source_id: source.id,
      target_type: target.node_type,
      target_id: target.id,
      max_depth: String(maxDepth),
    });
    setGraphPathBusy(true);
    setGraphPathError("");
    try {
      setGraphPath(await apiFetch<GraphPath>(`/graph/path?${params.toString()}`));
    } catch (err) {
      setGraphPath(null);
      setGraphPathError(err instanceof Error ? err.message : "关系路径发现失败");
    } finally {
      setGraphPathBusy(false);
    }
  }

  async function handleCreateManualNode(payload: {
    node_type: "entity" | "event";
    name: string;
    subtype: string | null;
    description: string | null;
    relation_type: string | null;
    role: string | null;
  }): Promise<GraphManualNodeResult> {
    if (!activeNode || (activeNode.node_type !== "entity" && activeNode.node_type !== "event")) {
      throw new Error("请先选择一个人物或事件节点");
    }
    const result = await apiFetch<GraphManualNodeResult>("/graph/manual-nodes", {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        anchor_type: activeNode.node_type,
        anchor_id: activeNode.id,
      }),
    });
    setMutationMessage(`已创建并连接：${result.label}`);
    router.push(result.graph_href);
    return result;
  }

  return (
    <AuthGate>
      <main className="space-y-6">
        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        {workspace ? (
          <>
            <GraphManualCreatePanel activeNode={activeNode} onCreate={handleCreateManualNode} />
            {activeNode && (activeNode.node_type === "entity" || activeNode.node_type === "event") ? (
              <div className="grid gap-4 xl:grid-cols-[1fr_auto]">
                <ManualEvidencePanel targetType={activeNode.node_type} targetId={activeNode.id} compact />
                <div className="flex items-start justify-end">
                  <AddToCollectionControl itemType={activeNode.node_type} itemId={activeNode.id} label={activeNode.label} />
                </div>
              </div>
            ) : null}
            <GraphWorkspaceShell
            title={workspace.title}
            description={workspace.description}
            scope={workspace.scope}
            nodes={workspace.nodes}
            edges={workspace.edges}
            timelineFocus={workspace.timeline_focus}
            stats={workspace.stats}
            filters={workspace.filters}
            conflicts={workspace.conflicts}
            recentActions={workspace.recent_actions}
            viewpoints={viewpoints}
            viewpointName={viewpointName}
            viewpointBusy={viewpointBusy}
            viewpointActionBusyKey={viewpointActionBusyKey}
            viewpointMessage={viewpointMessage}
            activeNodeId={activeNode?.id ?? null}
            onViewpointNameChange={setViewpointName}
            onSaveViewpoint={handleSaveViewpoint}
            onRenameViewpoint={handleRenameViewpoint}
            onDeleteViewpoint={handleDeleteViewpoint}
            onDismissViewpointMessage={() => setViewpointMessage("")}
            onSelectNode={handleSelectNode}
            onUpdateFilters={handleUpdateFilters}
            nodeDetail={nodeDetail}
            nodeDetailLoading={nodeDetailLoading}
            curationContext={curationContext}
            curationLoading={curationLoading}
            mutationBusyKey={mutationBusyKey}
            mutationMessage={mutationMessage}
            mutationError={mutationError}
            onDismissMutationMessage={() => setMutationMessage("")}
            onDismissMutationError={() => setMutationError("")}
            onUpsertEventParticipant={handleUpsertEventParticipant}
            onRemoveEventParticipant={handleRemoveEventParticipant}
            onUpsertRelation={handleUpsertRelation}
            onRemoveRelation={handleRemoveRelation}
            onUpdateNode={handleUpdateNode}
            onSetConflictDisposition={handleSetConflictDisposition}
            graphPath={graphPath}
            graphPathBusy={graphPathBusy}
            graphPathError={graphPathError}
            onFindPath={handleFindPath}
            />
          </>
        ) : (
          <GraphPageLoadingPanel />
        )}
      </main>
    </AuthGate>
  );
}

function GraphManualCreatePanel({
  activeNode,
  onCreate,
}: {
  activeNode: GraphWorkspaceData["nodes"][number] | null;
  onCreate: (payload: {
    node_type: "entity" | "event";
    name: string;
    subtype: string | null;
    description: string | null;
    relation_type: string | null;
    role: string | null;
  }) => Promise<GraphManualNodeResult>;
}) {
  const [open, setOpen] = useState(false);
  const [nodeType, setNodeType] = useState<"entity" | "event">("entity");
  const [name, setName] = useState("");
  const [subtype, setSubtype] = useState("");
  const [description, setDescription] = useState("");
  const [relationType, setRelationType] = useState("");
  const [role, setRole] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onCreate({ node_type: nodeType, name, subtype: subtype || null, description: description || null, relation_type: relationType || null, role: role || null });
      setName("");
      setDescription("");
      setOpen(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建并连接失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="border-4 border-ink bg-aqua p-4 shadow-brutal">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><p className="section-kicker">补齐图谱</p><p className="mt-1 font-bold">从当前节点“{activeNode?.label ?? "未选择"}”创建缺失知识，并在一个事务中完成连接。</p></div>
        <button type="button" onClick={() => setOpen((value) => !value)} disabled={!activeNode} className="tool-action bg-neon disabled:opacity-50">{open ? "收起" : "创建缺失节点"}</button>
      </div>
      {open ? (
        <form onSubmit={submit} className="mt-4 grid gap-3 border-2 border-ink bg-canvas p-4 md:grid-cols-2 xl:grid-cols-3">
          <select value={nodeType} onChange={(event) => setNodeType(event.target.value as "entity" | "event")} className="brutal-input"><option value="entity">人物 / 实体</option><option value="event">事件</option></select>
          <input required value={name} onChange={(event) => setName(event.target.value)} className="brutal-input" placeholder="节点名称" />
          <input value={subtype} onChange={(event) => setSubtype(event.target.value)} className="brutal-input" placeholder={nodeType === "entity" ? "person" : "meeting"} />
          <input value={relationType} onChange={(event) => setRelationType(event.target.value)} className="brutal-input" placeholder={activeNode?.node_type !== nodeType ? "participates_in" : "related_to"} />
          <input value={role} onChange={(event) => setRole(event.target.value)} className="brutal-input" placeholder="参与角色（可选）" />
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} className="brutal-input min-h-20 md:col-span-2 xl:col-span-3" placeholder="节点说明" />
          {error ? <p className="border-2 border-ink bg-ember p-3 font-bold text-red-950 md:col-span-2 xl:col-span-3">{error}</p> : null}
          <button disabled={busy} className="brutal-action brutal-action-primary md:col-span-2 xl:col-span-3 disabled:opacity-50">{busy ? "创建中…" : "创建并连接"}</button>
        </form>
      ) : null}
    </section>
  );
}

export function GraphPageLoadingPanel() {
  return (
    <Panel className="p-6 md:p-8" tone="default">
      <p className="text-sm font-black uppercase tracking-[0.2em]">Graph Workspace</p>
      <p className="mt-4 text-3xl font-black">图谱工作台载入中</p>
      <p className="mt-4 text-base font-semibold leading-relaxed">
        系统正在组合事件、人物和时间线邻域，准备进入统一工作台。
      </p>
      <div className="mt-6 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="border-4 border-ink bg-white p-4 shadow-brutal">
          <div className="h-5 w-32 animate-pulse bg-paper" />
          <div className="mt-4 h-64 animate-pulse border-4 border-dashed border-ink bg-paper" />
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="h-20 animate-pulse border-4 border-ink bg-paper" />
            <div className="h-20 animate-pulse border-4 border-ink bg-paper" />
            <div className="h-20 animate-pulse border-4 border-ink bg-paper" />
          </div>
        </div>
        <div className="border-4 border-ink bg-white p-4 shadow-brutal">
          <div className="h-5 w-28 animate-pulse bg-paper" />
          <div className="mt-4 h-8 w-40 animate-pulse bg-paper" />
          <div className="mt-4 space-y-3">
            <div className="h-16 animate-pulse border-4 border-ink bg-paper" />
            <div className="h-16 animate-pulse border-4 border-ink bg-paper" />
            <div className="h-16 animate-pulse border-4 border-ink bg-paper" />
          </div>
        </div>
      </div>
    </Panel>
  );
}
