"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type PersonNode = {
  id: string;
  display_name: string;
  entity_type: string;
  role?: string | null;
  relation_type?: string | null;
};

type RelatedEventNode = {
  id: string;
  title: string;
  summary: string | null;
  time_text: string | null;
  connection_score: number;
  connection_reasons: string[];
  shared_participants: string[];
  source_note_title: string | null;
};

type EventConstellationProps = {
  eventTitle: string;
  eventSummary: string;
  participants: PersonNode[];
  relatedEvents: RelatedEventNode[];
};

type LayoutNode = {
  key: string;
  href: string;
  label: string;
  eyebrow: string;
  x: number;
  y: number;
  tone: "paper" | "aqua" | "peach";
  kind: "participant" | "related";
  detail: string;
  meta: string[];
};

export function EventConstellation({
  eventTitle,
  eventSummary,
  participants,
  relatedEvents,
}: EventConstellationProps) {
  const graphNodes = useMemo<LayoutNode[]>(() => {
    const participantNodes = participants.slice(0, 5).map((participant, index, list) => {
      const angle = list.length === 1 ? -90 : -150 + (120 / Math.max(list.length - 1, 1)) * index;
      const radians = (angle * Math.PI) / 180;
      const radiusX = 32;
      const radiusY = 22;
      return {
        key: `participant-${participant.id}`,
        href: `/story/entity/${participant.id}`,
        label: participant.display_name,
        eyebrow: participant.role || participant.relation_type || participant.entity_type,
        x: 50 + (Math.cos(radians) * radiusX),
        y: 38 + (Math.sin(radians) * radiusY),
        tone: "aqua" as const,
        kind: "participant" as const,
        detail: `${participant.display_name} 作为 ${participant.role || participant.relation_type || "关联角色"} 出现在当前事件中。`,
        meta: [participant.entity_type],
      };
    });

    const relatedNodes = relatedEvents.slice(0, 6).map((related, index, list) => {
      const columns = Math.min(3, Math.max(list.length, 1));
      const column = index % columns;
      const row = Math.floor(index / columns);
      return {
        key: `related-${related.id}`,
        href: `/events/${related.id}`,
        label: related.title,
        eyebrow: `${Math.round(related.connection_score * 100)}% 连接`,
        x: 18 + (column * 32),
        y: 68 + (row * 18),
        tone: "peach" as const,
        kind: "related" as const,
        detail: related.summary || "暂无关联事件摘要。",
        meta: [...related.connection_reasons, ...related.shared_participants],
      };
    });

    return [...participantNodes, ...relatedNodes];
  }, [participants, relatedEvents]);

  const [activeKey, setActiveKey] = useState<string | null>(graphNodes[0]?.key ?? null);
  const activeNode = graphNodes.find((node) => node.key === activeKey) ?? null;

  useEffect(() => {
    if (!graphNodes.length) {
      setActiveKey(null);
      return;
    }
    if (!activeKey || !graphNodes.some((node) => node.key === activeKey)) {
      setActiveKey(graphNodes[0].key);
    }
  }, [activeKey, graphNodes]);

  return (
    <div className="space-y-5">
      <div className="graph-canvas">
        <div className="border-b-4 border-ink bg-paper px-4 py-5 text-center md:px-6">
          <div className="mx-auto max-w-3xl text-center">
            <p className="section-kicker">事件图谱</p>
            <p className="mt-2 text-3xl font-black leading-tight md:text-4xl">{eventTitle}</p>
            <p className="mt-3 text-sm font-semibold leading-relaxed text-muted md:text-base">{eventSummary}</p>
          </div>
        </div>

        <div className="grid gap-3 p-4 md:hidden">
          {graphNodes.map((node) => (
            <Link
              key={node.key}
              href={node.href}
              className={`graph-node block ${
                node.kind === "participant" ? "bg-aqua" : "bg-peach"
              }`}
            >
              <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.eyebrow}</p>
              <p className="mt-2 text-base font-black leading-tight">{node.label}</p>
            </Link>
          ))}
        </div>

        <div className="relative hidden h-[31rem] overflow-hidden md:block">
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="eventGraphGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#0f172a" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#0f172a" stopOpacity="0.2" />
              </linearGradient>
            </defs>
            <rect x="0" y="0" width="100" height="100" fill="#fffdf5" />
            <circle cx="50" cy="50" r="18" fill="#fff3c2" opacity="0.7" />
            {graphNodes.map((node) => (
              <line
                key={node.key}
                x1="50"
                y1="50"
                x2={node.x}
                y2={node.y}
                stroke={activeKey === node.key ? "#0f172a" : "url(#eventGraphGlow)"}
                strokeWidth={activeKey === node.key ? "0.65" : "0.4"}
                strokeDasharray={node.kind === "related" ? "1.5 1.3" : undefined}
                opacity={activeKey && activeKey !== node.key ? 0.42 : 1}
              />
            ))}
            <circle cx="50" cy="50" r="6.2" fill="#0f172a" />
            <circle cx="50" cy="50" r="8.4" fill="none" stroke="#0f172a" strokeWidth="0.5" opacity="0.3" />
            {graphNodes.map((node) => (
              <circle
                key={`${node.key}-dot`}
                cx={node.x}
                cy={node.y}
                r={activeKey === node.key ? "4.2" : "3.2"}
                fill="#fff"
                stroke="#0f172a"
                strokeWidth="0.55"
                opacity={activeKey && activeKey !== node.key ? 0.7 : 1}
              />
            ))}
          </svg>

          <div className="pointer-events-none absolute inset-0">
            {graphNodes.map((node) => (
              <div
                key={node.key}
                className="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${node.x}%`, top: `${node.y}%` }}
              >
                <Link
                  href={node.href}
                  onMouseEnter={() => setActiveKey(node.key)}
                  onFocus={() => setActiveKey(node.key)}
                  className={`graph-node block w-32 lg:w-36 ${
                    node.tone === "aqua" ? "bg-aqua" : node.tone === "peach" ? "bg-peach" : "bg-paper"
                  }`}
                >
                  <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.eyebrow}</p>
                  <p className="mt-2 text-sm font-black leading-tight">{node.label}</p>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </div>

      {activeNode ? (
        <div className="border-4 border-ink bg-bone p-5 shadow-brutalSoft">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-xs font-black uppercase tracking-[0.16em]">
              {activeNode.kind === "participant" ? "角色节点" : "关联事件"}
            </p>
            {activeNode.meta.slice(0, 4).map((item) => (
              <span key={`${activeNode.key}-${item}`} className="brutal-chip">
                {item}
              </span>
            ))}
          </div>
          <p className="mt-4 text-2xl font-black">{activeNode.label}</p>
          <p className="body-copy mt-3">{activeNode.detail}</p>
        </div>
      ) : null}
    </div>
  );
}
