"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/panel";

type TimelineFragment = {
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

type RelatedEvent = {
  id: string;
  title: string;
  summary: string | null;
  time_text: string | null;
  event_type: string | null;
  location_text?: string | null;
  role?: string | null;
  relation_type?: string | null;
  start_time?: string | null;
};

type EntityTimelineWorkspaceProps = {
  entityId: string;
  displayName: string;
  entityType: string;
  aliases: string[];
  fragments: TimelineFragment[];
  relatedEvents: RelatedEvent[];
};

export function EntityTimelineWorkspace({
  entityId,
  displayName,
  entityType,
  aliases,
  fragments,
  relatedEvents,
}: EntityTimelineWorkspaceProps) {
  const visibleFragments = useMemo(() => fragments.slice(0, 8), [fragments]);
  const [activeEventId, setActiveEventId] = useState<string | null>(visibleFragments[0]?.event_id ?? null);

  useEffect(() => {
    if (!visibleFragments.length) {
      setActiveEventId(null);
      return;
    }
    if (!activeEventId || !visibleFragments.some((fragment) => fragment.event_id === activeEventId)) {
      setActiveEventId(visibleFragments[0].event_id);
    }
  }, [activeEventId, visibleFragments]);

  const activeIndex = visibleFragments.findIndex((fragment) => fragment.event_id === activeEventId);
  const activeFragment = visibleFragments[activeIndex] ?? visibleFragments[0] ?? null;
  const previousFragment = activeIndex > 0 ? visibleFragments[activeIndex - 1] : null;
  const nextFragment =
    activeIndex >= 0 && activeIndex < visibleFragments.length - 1 ? visibleFragments[activeIndex + 1] : null;

  return (
    <section className="grid gap-6 xl:grid-cols-[0.78fr_1.06fr_0.9fr]">
      <Panel className="p-6" tone="time" intensity="quiet">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="section-kicker">时间轴工作台</p>
            <p className="mt-2 text-base font-semibold leading-relaxed text-muted">
              先选中一个片段，再往前后两端追踪它在图谱里的回声。
            </p>
          </div>
          <div className="border-4 border-ink bg-canvas px-4 py-3 shadow-brutalSoft">
            <p className="text-xs font-black uppercase tracking-[0.16em]">片段数</p>
            <p className="mt-2 text-3xl font-black">{fragments.length}</p>
          </div>
        </div>

        <div className="mt-6 space-y-3">
          {visibleFragments.length ? (
            visibleFragments.map((fragment) => {
              const active = fragment.event_id === activeFragment?.event_id;
              return (
                <button
                  key={fragment.event_id}
                  type="button"
                  onClick={() => setActiveEventId(fragment.event_id)}
                  className={`grid w-full gap-4 border-4 border-ink px-4 py-4 text-left shadow-brutalSoft md:grid-cols-[88px_1fr] ${
                    active ? "bg-canvas" : "bg-bone"
                  }`}
                >
                  <div className="flex flex-col justify-between">
                    <p className="text-[11px] font-black uppercase tracking-[0.14em]">{fragment.chapter_label}</p>
                    <p className="text-lg font-black">{fragment.position}</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.14em]">
                      {fragment.time_text ?? fragment.event_type ?? "事件片段"}
                    </p>
                    <p className="mt-2 text-xl font-black leading-tight">{fragment.title}</p>
                    <p className="mt-2 line-clamp-2 text-sm font-semibold leading-relaxed text-muted">
                      {fragment.summary ?? "暂无事件摘要。"}
                    </p>
                  </div>
                </button>
              );
            })
          ) : (
            <div className="empty-state">
              当前人物还没有可用片段，暂时无法展开时间线工作台。
            </div>
          )}
        </div>
      </Panel>

      <Panel className="p-6" tone="quiet" intensity="quiet">
        <p className="section-kicker">当前焦点</p>
        {activeFragment ? (
          <>
            <p className="mt-4 text-3xl font-black leading-tight">{activeFragment.title}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="brutal-chip">{entityType}</span>
              {activeFragment.chapter_label ? <span className="brutal-chip">{activeFragment.chapter_label}</span> : null}
              {activeFragment.role ? <span className="brutal-chip">{activeFragment.role}</span> : null}
              {activeFragment.location_text ? <span className="brutal-chip">{activeFragment.location_text}</span> : null}
            </div>
            <p className="body-copy mt-5">
              {activeFragment.summary ?? "暂无片段摘要。"}
            </p>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="border-4 border-ink bg-aqua p-4 shadow-brutalSoft">
                <p className="text-xs font-black uppercase tracking-[0.16em]">上一跳</p>
                <p className="mt-3 text-xl font-black">{previousFragment?.title ?? "已到起点"}</p>
                <p className="mt-2 text-sm font-bold">{previousFragment?.time_text ?? "无"}</p>
              </div>
              <div className="border-4 border-ink bg-peach p-4 shadow-brutalSoft">
                <p className="text-xs font-black uppercase tracking-[0.16em]">下一跳</p>
                <p className="mt-3 text-xl font-black">{nextFragment?.title ?? "已到当前尾声"}</p>
                <p className="mt-2 text-sm font-bold">{nextFragment?.time_text ?? "无"}</p>
              </div>
            </div>

            {activeFragment.source_note_title ? (
              <p className="mt-6 text-sm font-black uppercase tracking-[0.16em]">
                来源卷宗 {activeFragment.source_note_title}
              </p>
            ) : null}

            <div className="mt-6 flex flex-wrap gap-3">
              <Link href={`/events/${activeFragment.event_id}`} className="brutal-action brutal-action-secondary">
                打开事件
              </Link>
              <Link href={`/review/entities/${entityId}`} className="brutal-action brutal-action-info">
                返回审核
              </Link>
              <Link href={`/curation/entities/${entityId}`} className="brutal-action brutal-action-primary">
                编辑人物
              </Link>
            </div>
          </>
        ) : (
          <p className="mt-4 text-base font-bold leading-relaxed">还没有可选的时间片段。</p>
        )}
      </Panel>

      <Panel className="p-6" tone="story" intensity="quiet">
        <p className="section-kicker">图谱回声</p>
        <p className="mt-3 text-base font-semibold leading-relaxed text-muted">
          把角色的别名、侧向关联事件、以及非主干线的节点放在一起看，方便继续扩展人物索引。
        </p>

        <div className="mt-5">
          <p className="text-xs font-black uppercase tracking-[0.16em]">别名云</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {aliases.length ? (
              aliases.map((alias) => (
                <span key={alias} className="brutal-chip">
                  {alias}
                </span>
              ))
            ) : (
              <p className="text-sm font-bold">当前没有额外别名。</p>
            )}
          </div>
        </div>

        <div className="mt-6 space-y-3">
          <p className="text-xs font-black uppercase tracking-[0.16em]">侧向事件</p>
          {relatedEvents.slice(0, 6).map((item) => (
            <Link key={item.id} href={`/events/${item.id}`}>
              <div className="border-4 border-ink bg-canvas px-4 py-4 shadow-brutalSoft transition-transform hover:-translate-y-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.14em]">
                      {item.time_text ?? item.event_type ?? "关联事件"}
                    </p>
                    <p className="mt-2 text-xl font-black leading-tight">{item.title}</p>
                  </div>
                  {item.role || item.relation_type ? (
                    <span className="brutal-chip">{item.role || item.relation_type}</span>
                  ) : null}
                </div>
                <p className="mt-3 line-clamp-2 text-sm font-semibold leading-relaxed text-muted">
                  {item.summary ?? "暂无摘要。"}
                </p>
              </div>
            </Link>
          ))}
          {relatedEvents.length === 0 ? (
            <div className="empty-state">
              目前还没有主时间轴之外的侧向事件。
            </div>
          ) : null}
        </div>

        <div className="mt-6 border-4 border-ink bg-aqua p-4 shadow-brutalSoft">
          <p className="text-xs font-black uppercase tracking-[0.16em]">角色核心</p>
          <p className="mt-3 text-2xl font-black">{displayName}</p>
          <p className="mt-2 text-sm font-bold">
            当前正在以 {entityType} 身份穿过 {fragments.length} 个时间片段。
          </p>
        </div>
      </Panel>
    </section>
  );
}
