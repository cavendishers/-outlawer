"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type JourneyFragment = {
  event_id: string;
  title: string;
  summary: string | null;
  time_text: string | null;
  event_type: string | null;
  location_text: string | null;
  role: string | null;
  relation_type: string | null;
  chapter_label: string;
  source_note_title: string | null;
  position: number;
  total: number;
};

type EntityJourneyMapProps = {
  displayName: string;
  entityType: string;
  fragments: JourneyFragment[];
};

export function EntityJourneyMap({ displayName, entityType, fragments }: EntityJourneyMapProps) {
  const visibleFragments = fragments.slice(0, 6);
  const [activeEventId, setActiveEventId] = useState<string | null>(visibleFragments[0]?.event_id ?? null);

  const graphNodes = useMemo(
    () =>
      visibleFragments.map((fragment, index) => ({
        ...fragment,
        x: 22 + (index * 14),
        y: 50 + (index % 2 === 0 ? -18 : 18),
      })),
    [visibleFragments]
  );

  const activeNode = graphNodes.find((node) => node.event_id === activeEventId) ?? graphNodes[0] ?? null;

  useEffect(() => {
    if (!graphNodes.length) {
      setActiveEventId(null);
      return;
    }
    if (!activeEventId || !graphNodes.some((node) => node.event_id === activeEventId)) {
      setActiveEventId(graphNodes[0].event_id);
    }
  }, [activeEventId, graphNodes]);

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:hidden">
        {graphNodes.map((node) => (
          <Link
            key={node.event_id}
            href={`/events/${node.event_id}`}
            className={`graph-node block ${activeEventId === node.event_id ? "bg-gold" : "bg-bone"}`}
            onMouseEnter={() => setActiveEventId(node.event_id)}
            onFocus={() => setActiveEventId(node.event_id)}
          >
            <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.chapter_label}</p>
            <p className="mt-2 text-base font-black leading-tight">{node.title}</p>
            <p className="mt-2 text-[11px] font-black uppercase tracking-[0.14em]">{node.time_text ?? "待校时"}</p>
          </Link>
        ))}
      </div>

      <div className="hidden md:block">
        <div className="graph-canvas relative overflow-hidden">
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <rect x="0" y="0" width="100" height="100" fill="#fff9ee" />
            <line x1="12" y1="50" x2="92" y2="50" stroke="#0f172a" strokeWidth="0.45" strokeDasharray="2 1.6" />
            <circle cx="12" cy="50" r="5.8" fill="#0f172a" />
            {graphNodes.map((node, index) => {
              const prevX = index === 0 ? 12 : graphNodes[index - 1].x;
              const prevY = index === 0 ? 50 : graphNodes[index - 1].y;
              return (
                <g key={node.event_id}>
                  <line
                    x1={prevX}
                    y1={prevY}
                    x2={node.x}
                    y2={node.y}
                    stroke="#0f172a"
                    strokeWidth={activeEventId === node.event_id ? "0.72" : "0.45"}
                    opacity={activeEventId && activeEventId !== node.event_id ? 0.42 : 0.95}
                  />
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={activeEventId === node.event_id ? "4.3" : "3.5"}
                    fill="#fff"
                    stroke="#0f172a"
                    strokeWidth="0.6"
                  />
                </g>
              );
            })}
          </svg>

          <div className="relative z-10 px-5 py-6">
            <div className="absolute left-[4%] top-1/2 w-36 -translate-y-1/2 border-4 border-ink bg-aqua px-4 py-4 shadow-brutalSoft">
              <p className="text-xs font-black uppercase tracking-[0.16em]">{entityType}</p>
              <p className="mt-3 text-2xl font-black">{displayName}</p>
            </div>

            {graphNodes.map((node) => (
              <div
                key={node.event_id}
                className="absolute -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${node.x}%`, top: `${node.y}%` }}
              >
                <Link
                  href={`/events/${node.event_id}`}
                  onMouseEnter={() => setActiveEventId(node.event_id)}
                  onFocus={() => setActiveEventId(node.event_id)}
                  className={`graph-node block w-40 ${
                    activeEventId === node.event_id ? "bg-gold" : "bg-paper"
                  }`}
                >
                  <p className="text-[11px] font-black uppercase tracking-[0.14em]">{node.chapter_label}</p>
                  <p className="mt-2 text-sm font-black leading-tight">{node.title}</p>
                  <p className="mt-2 text-[11px] font-black uppercase tracking-[0.14em]">
                    {node.time_text ?? "待校时"}
                  </p>
                </Link>
              </div>
            ))}

            <div className="h-[28rem]" />
          </div>
        </div>
      </div>

      {activeNode ? (
        <div className="border-4 border-ink bg-bone p-5 shadow-brutalSoft">
          <div className="flex flex-wrap gap-2">
            {[
              activeNode.chapter_label,
              activeNode.role || activeNode.relation_type,
              activeNode.event_type,
              activeNode.location_text,
            ]
              .filter(Boolean)
              .map((item) => (
                <span key={`${activeNode.event_id}-${item}`} className="brutal-chip">
                  {item}
                </span>
              ))}
          </div>
          <p className="mt-4 text-2xl font-black">{activeNode.title}</p>
          <p className="body-copy mt-3">
            {activeNode.summary ?? "暂无事件摘要。"}
          </p>
          {activeNode.source_note_title ? (
            <p className="mt-4 text-sm font-black uppercase tracking-[0.16em]">
              来源卷宗 {activeNode.source_note_title}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
