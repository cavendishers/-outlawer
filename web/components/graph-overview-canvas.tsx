"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type GraphNode = {
  id: string;
  node_type: string;
  label: string;
  subtitle: string;
  href: string;
  importance: number;
  meta: string[];
};

type GraphEdge = {
  source_id: string;
  target_id: string;
  edge_type: string;
  label: string;
  weight: number;
};

type GraphOverviewCanvasProps = {
  title: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

type PositionedNode = GraphNode & {
  x: number;
  y: number;
  tone: "paper" | "aqua" | "peach";
};

export function GraphOverviewCanvas({ title, nodes, edges }: GraphOverviewCanvasProps) {
  const positionedNodes = useMemo<PositionedNode[]>(() => {
    const eventNodes = nodes.filter((node) => node.node_type === "event").slice(0, 6);
    const entityNodes = nodes.filter((node) => node.node_type !== "event").slice(0, 4);

    const spread = (index: number, columns: number, min: number, max: number) => {
      if (columns <= 1) return 50;
      return min + (index * ((max - min) / (columns - 1)));
    };

    const positionedEvents = eventNodes.map((node, index, list) => ({
      ...node,
      x: spread(index % Math.min(3, list.length), Math.min(3, list.length), 24, 76),
      y: 56 + (Math.floor(index / 3) * 20),
      tone: "peach" as const,
    }));

    const positionedEntities = entityNodes.map((node, index, list) => ({
      ...node,
      x: spread(index % Math.min(4, list.length), Math.min(4, list.length), 16, 84),
      y: 20 + (Math.floor(index / 4) * 14),
      tone: "aqua" as const,
    }));

    return [...positionedEvents, ...positionedEntities];
  }, [nodes]);

  const [activeNodeId, setActiveNodeId] = useState<string | null>(positionedNodes[0]?.id ?? null);

  useEffect(() => {
    if (!positionedNodes.length) {
      setActiveNodeId(null);
      return;
    }
    if (!activeNodeId || !positionedNodes.some((node) => node.id === activeNodeId)) {
      setActiveNodeId(positionedNodes[0].id);
    }
  }, [activeNodeId, positionedNodes]);

  const activeNode = positionedNodes.find((node) => node.id === activeNodeId) ?? null;
  const nodeMap = new Map(positionedNodes.map((node) => [node.id, node]));

  return (
    <div className="space-y-5">
      <div className="graph-canvas">
        <div className="border-b-4 border-ink bg-paper px-4 py-5 text-center md:px-6">
          <p className="section-kicker">Overview Graph</p>
          <p className="mt-2 text-3xl font-black leading-tight md:text-4xl">{title}</p>
          <p className="mx-auto mt-3 max-w-3xl text-sm font-semibold leading-relaxed text-muted md:text-base">
            事件节点负责串起时间，人物节点负责提供交叉连接。把鼠标移到任意节点上，就能快速读出这张网的重心。
          </p>
        </div>

        <div className="grid gap-3 p-4 md:hidden">
          {positionedNodes.map((node) => (
            <Link
              key={node.id}
              href={node.href}
              className={`graph-node block ${
                node.node_type === "event" ? "bg-peach" : "bg-aqua"
              }`}
            >
              <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.subtitle}</p>
              <p className="mt-2 text-base font-black leading-tight">{node.label}</p>
            </Link>
          ))}
        </div>

        <div className="relative hidden h-[34rem] w-full overflow-hidden md:block">
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <rect x="0" y="0" width="100" height="100" fill="#fffdf5" />
            <circle cx="50" cy="50" r="24" fill="#fff3c2" opacity="0.46" />
            <line x1="10" y1="50" x2="90" y2="50" stroke="#0f172a" strokeWidth="0.3" strokeDasharray="2.5 2" opacity="0.25" />
            {edges.map((edge) => {
              const source = nodeMap.get(edge.source_id);
              const target = nodeMap.get(edge.target_id);
              if (!source || !target) return null;
              const isActive = activeNodeId === source.id || activeNodeId === target.id;
              return (
                <line
                  key={`${edge.source_id}-${edge.target_id}-${edge.edge_type}`}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="#0f172a"
                  strokeWidth={Math.max(0.18, edge.weight * (edge.edge_type === "relates_to" ? 0.7 : 0.9))}
                  strokeDasharray={edge.edge_type === "relates_to" ? "1.5 1.1" : undefined}
                  opacity={activeNodeId ? (isActive ? 0.95 : 0.22) : 0.65}
                />
              );
            })}
            {positionedNodes.map((node) => (
              <circle
                key={`${node.id}-dot`}
                cx={node.x}
                cy={node.y}
                r={activeNodeId === node.id ? Math.max(4.1, node.importance * 5) : Math.max(3, node.importance * 4)}
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
                <Link
                  href={node.href}
                  onMouseEnter={() => setActiveNodeId(node.id)}
                  onFocus={() => setActiveNodeId(node.id)}
                  className={`graph-node block w-32 xl:w-36 ${
                    node.tone === "aqua" ? "bg-aqua" : node.tone === "peach" ? "bg-peach" : "bg-paper"
                  }`}
                >
                  <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.subtitle}</p>
                  <p className="mt-2 text-sm font-black leading-tight">{node.label}</p>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </div>

      {activeNode ? (
        <div className="border-4 border-ink bg-bone p-5 shadow-brutalSoft">
          <div className="flex flex-wrap gap-2">
            <span className="brutal-chip">
              {activeNode.node_type === "event" ? "事件节点" : "角色节点"}
            </span>
            {activeNode.meta.slice(0, 4).map((item) => (
              <span key={`${activeNode.id}-${item}`} className="brutal-chip">
                {item}
              </span>
            ))}
          </div>
          <p className="mt-4 text-2xl font-black">{activeNode.label}</p>
          <p className="body-copy mt-3">
            当前节点共连接{" "}
            {
              edges.filter((edge) => edge.source_id === activeNode.id || edge.target_id === activeNode.id).length
            }{" "}
            条关系线。
          </p>
        </div>
      ) : null}
    </div>
  );
}
