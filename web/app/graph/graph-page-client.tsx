"use client";

import { startTransition, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { AuthGate } from "@/components/auth-gate";
import { GraphWorkspaceShell } from "@/components/graph-workspace-shell";
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
    source_id: string;
    target_id: string;
    edge_type: string;
    label: string;
    weight: number;
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
    source_id: string;
    target_id: string;
    edge_type: string;
    label: string;
    weight: number;
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

export function GraphPageClient() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const eventId = searchParams?.get("event_id") ?? null;
  const entityId = searchParams?.get("entity_id") ?? null;
  const activeNodeIdFromUrl = searchParams?.get("active_node_id") ?? null;
  const [workspace, setWorkspace] = useState<GraphWorkspaceData | null>(null);
  const [nodeDetail, setNodeDetail] = useState<GraphNodeDetail | null>(null);
  const [nodeDetailLoading, setNodeDetailLoading] = useState(false);
  const [curationContext, setCurationContext] = useState<GraphNodeCurationContext | null>(null);
  const [curationLoading, setCurationLoading] = useState(false);
  const [mutationBusyKey, setMutationBusyKey] = useState("");
  const [mutationMessage, setMutationMessage] = useState("");
  const [mutationError, setMutationError] = useState("");
  const [error, setError] = useState("");

  function buildScopeParams() {
    const params = new URLSearchParams();
    if (eventId) params.set("event_id", eventId);
    if (entityId) params.set("entity_id", entityId);
    return params;
  }

  async function fetchWorkspaceData(): Promise<GraphWorkspaceData> {
    const query = buildScopeParams().toString();
    return apiFetch<GraphWorkspaceData>(`/graph/workspace${query ? `?${query}` : ""}`);
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
        event: { id: string; title: string };
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
        entity: { id: string; display_name: string; entity_type: string };
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
    fetchWorkspaceData()
      .then((data) => {
        startTransition(() => {
          setWorkspace(data);
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
  }, [entityId, eventId]);

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
  }, [activeNode, entityId, eventId]);

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
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    params.set("active_node_id", nodeId);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
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

  return (
    <AuthGate>
      <main className="space-y-6">
        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        {workspace ? (
          <GraphWorkspaceShell
            title={workspace.title}
            description={workspace.description}
            scope={workspace.scope}
            nodes={workspace.nodes}
            edges={workspace.edges}
            timelineFocus={workspace.timeline_focus}
            stats={workspace.stats}
            activeNodeId={activeNode?.id ?? null}
            onSelectNode={handleSelectNode}
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
          />
        ) : (
          <GraphPageLoadingPanel />
        )}
      </main>
    </AuthGate>
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
