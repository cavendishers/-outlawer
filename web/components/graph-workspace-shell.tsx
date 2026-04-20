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
};

type PositionedNode = GraphNode & {
  x: number;
  y: number;
  tone: "paper" | "aqua" | "peach" | "neon";
};

function toneForNode(node: GraphNode): PositionedNode["tone"] {
  if (node.is_anchor) return "neon";
  if (node.node_type === "event") return "peach";
  if (node.node_type === "entity") return "aqua";
  return "paper";
}

export function GraphWorkspaceShell({
  title,
  description,
  scope,
  nodes,
  edges,
  timelineFocus,
  stats,
}: GraphWorkspaceShellProps) {
  const positionedNodes = useMemo<PositionedNode[]>(() => {
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

  const [activeNodeId, setActiveNodeId] = useState<string | null>(positionedNodes.find((node) => node.is_anchor)?.id ?? positionedNodes[0]?.id ?? null);

  useEffect(() => {
    if (!positionedNodes.length) {
      setActiveNodeId(null);
      return;
    }
    if (!activeNodeId || !positionedNodes.some((node) => node.id === activeNodeId)) {
      setActiveNodeId(positionedNodes.find((node) => node.is_anchor)?.id ?? positionedNodes[0]?.id ?? null);
    }
  }, [activeNodeId, positionedNodes]);

  const activeNode = positionedNodes.find((node) => node.id === activeNodeId) ?? positionedNodes[0] ?? null;
  const nodeMap = new Map(positionedNodes.map((node) => [node.id, node]));
  const relatedEdges = activeNode
    ? edges.filter((edge) => edge.source_id === activeNode.id || edge.target_id === activeNode.id)
    : [];

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel className="p-6 md:p-8" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.2em]">Graph Workspace</p>
          <h1 className="mt-3 font-display text-[clamp(2.3rem,5vw,4.5rem)] leading-[0.92]">{title}</h1>
          <p className="mt-4 max-w-3xl text-lg font-bold leading-relaxed">{description}</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <span className="brutal-chip">{scope}</span>
            <span className="brutal-chip">{stats.node_count} nodes</span>
            <span className="brutal-chip">{stats.edge_count} edges</span>
            <span className="brutal-chip">{stats.timeline_count} timeline</span>
          </div>
        </Panel>

        <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
          <Panel className="p-5" tone="time">
            <p className="text-xs font-black uppercase tracking-[0.16em]">事件节点</p>
            <p className="mt-3 text-4xl font-black">{stats.event_count}</p>
          </Panel>
          <Panel className="p-5" tone="info">
            <p className="text-xs font-black uppercase tracking-[0.16em]">人物节点</p>
            <p className="mt-3 text-4xl font-black">{stats.entity_count}</p>
          </Panel>
          <Panel className="p-5" tone="story">
            <p className="text-xs font-black uppercase tracking-[0.16em]">当前焦点</p>
            <p className="mt-3 text-2xl font-black leading-tight">{activeNode?.label ?? "未选择节点"}</p>
          </Panel>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.22fr_0.78fr]">
        <Panel className="p-6 md:p-8" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.16em]">共享画布</p>
          <div className="mt-5 grid gap-3 md:hidden">
            {positionedNodes.map((node) => (
              <button
                key={node.id}
                type="button"
                onClick={() => setActiveNodeId(node.id)}
                className={`border-4 border-ink px-4 py-4 text-left shadow-brutal ${
                  node.is_anchor ? "bg-neon" : node.node_type === "event" ? "bg-peach" : "bg-aqua"
                }`}
              >
                <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.subtitle}</p>
                <p className="mt-2 text-xl font-black">{node.label}</p>
              </button>
            ))}
          </div>

          <div className="relative hidden h-[36rem] overflow-hidden border-4 border-ink bg-white md:block">
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
              <rect x="0" y="0" width="100" height="100" fill="#fffdf5" />
              <circle cx="50" cy="48" r="18" fill="#fff3c2" opacity="0.42" />
              {edges.map((edge) => {
                const source = nodeMap.get(edge.source_id);
                const target = nodeMap.get(edge.target_id);
                if (!source || !target) return null;
                const active = activeNodeId ? edge.source_id === activeNodeId || edge.target_id === activeNodeId : false;
                return (
                  <line
                    key={`${edge.source_id}-${edge.target_id}-${edge.edge_type}`}
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    stroke="#0f172a"
                    strokeWidth={Math.max(0.22, edge.weight * 0.85)}
                    strokeDasharray={edge.edge_type === "relates_to" ? "1.8 1.2" : undefined}
                    opacity={activeNodeId ? (active ? 0.96 : 0.22) : 0.62}
                  />
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
                    onClick={() => setActiveNodeId(node.id)}
                    className={`w-32 border-4 border-ink px-3 py-3 text-left shadow-brutal transition-transform hover:-translate-y-1 xl:w-36 ${
                      node.tone === "neon" ? "bg-neon" : node.tone === "peach" ? "bg-peach" : node.tone === "aqua" ? "bg-aqua" : "bg-paper"
                    }`}
                  >
                    <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.subtitle}</p>
                    <p className="mt-2 text-sm font-black leading-tight">{node.label}</p>
                  </button>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <Panel className="p-6" tone="story">
          <p className="text-sm font-black uppercase tracking-[0.16em]">节点检查器</p>
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
              <p className="mt-5 text-base font-semibold leading-relaxed">
                {activeNode.inspector.summary ?? "当前节点还没有补充摘要。"}
              </p>
              <div className="mt-6 space-y-3">
                {activeNode.inspector.context_lines.map((line) => (
                  <div key={`${activeNode.id}-${line}`} className="border-4 border-ink bg-white px-4 py-3 shadow-brutal">
                    <p className="text-sm font-bold leading-relaxed">{line}</p>
                  </div>
                ))}
                <div className="border-4 border-ink bg-paper px-4 py-3 shadow-brutal">
                  <p className="text-xs font-black uppercase tracking-[0.16em]">邻接连线</p>
                  <p className="mt-2 text-3xl font-black">{relatedEdges.length}</p>
                </div>
              </div>
              <div className="mt-6 flex flex-wrap gap-3">
                {activeNode.inspector.actions.map((action) => (
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
            </>
          ) : (
            <p className="mt-4 text-base font-bold">当前没有可用节点。</p>
          )}
        </Panel>
      </section>

      <Panel className="p-6" tone="time">
        <p className="text-sm font-black uppercase tracking-[0.16em]">时间焦点带</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {timelineFocus.map((item) => (
            <Link key={`${item.kind}-${item.id}`} href={item.href}>
              <div className="h-full border-4 border-ink bg-white px-4 py-4 shadow-brutal transition-transform hover:-translate-y-1">
                <p className="text-[11px] font-black uppercase tracking-[0.14em]">{item.kind}</p>
                <p className="mt-2 text-lg font-black leading-tight">{item.title}</p>
                <p className="mt-2 text-sm font-bold">{item.display_time ?? "待校时"}</p>
              </div>
            </Link>
          ))}
          {timelineFocus.length === 0 ? (
            <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
              当前工作台还没有时间焦点带，等更多事件进入后这里会形成一条可读骨架。
            </div>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}
