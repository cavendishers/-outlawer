"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

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

export default function GraphPage() {
  const searchParams = useSearchParams();
  const eventId = searchParams?.get("event_id") ?? null;
  const entityId = searchParams?.get("entity_id") ?? null;
  const [workspace, setWorkspace] = useState<GraphWorkspaceData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (eventId) params.set("event_id", eventId);
    if (entityId) params.set("entity_id", entityId);
    const query = params.toString();

    apiFetch<GraphWorkspaceData>(`/graph/workspace${query ? `?${query}` : ""}`)
      .then((data) => {
        setWorkspace(data);
        setError("");
      })
      .catch((err) => {
        setWorkspace(null);
        setError(err instanceof Error ? err.message : "图谱工作台加载失败");
      });
  }, [entityId, eventId]);

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
          />
        ) : (
          <Panel className="p-6 md:p-8" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.2em]">Graph Workspace</p>
            <p className="mt-4 text-3xl font-black">图谱工作台载入中</p>
            <p className="mt-4 text-base font-semibold leading-relaxed">
              系统正在组合事件、人物和时间线邻域，准备进入统一工作台。
            </p>
          </Panel>
        )}
      </main>
    </AuthGate>
  );
}
