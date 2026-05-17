"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/panel";

type Participant = {
  id: string;
  display_name: string;
  entity_type: string;
  role?: string | null;
  relation_type?: string | null;
};

type RelatedEvent = {
  id: string;
  title: string;
  summary: string | null;
  time_text: string | null;
  event_type: string | null;
  connection_score: number;
  connection_reasons: string[];
  shared_participants: string[];
  distance_days: number | null;
  source_note_title: string | null;
};

type EventAssociationWorkspaceProps = {
  eventId: string;
  eventTitle: string;
  eventSummary: string;
  timeText: string | null;
  locationText: string | null;
  participants: Participant[];
  relatedEvents: RelatedEvent[];
};

export function EventAssociationWorkspace({
  eventId,
  eventTitle,
  eventSummary,
  timeText,
  locationText,
  participants,
  relatedEvents,
}: EventAssociationWorkspaceProps) {
  const sortedRelatedEvents = useMemo(
    () => [...relatedEvents].sort((left, right) => right.connection_score - left.connection_score),
    [relatedEvents]
  );
  const [activeRelatedId, setActiveRelatedId] = useState<string | null>(sortedRelatedEvents[0]?.id ?? null);

  useEffect(() => {
    if (!sortedRelatedEvents.length) {
      setActiveRelatedId(null);
      return;
    }
    if (!activeRelatedId || !sortedRelatedEvents.some((item) => item.id === activeRelatedId)) {
      setActiveRelatedId(sortedRelatedEvents[0].id);
    }
  }, [activeRelatedId, sortedRelatedEvents]);

  const activeRelatedEvent =
    sortedRelatedEvents.find((item) => item.id === activeRelatedId) ?? sortedRelatedEvents[0] ?? null;

  return (
    <section className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr_0.92fr]">
      <Panel className="p-6" tone="quiet" intensity="quiet">
        <p className="section-kicker">事件锚点</p>
        <p className="mt-4 text-3xl font-black leading-tight">{eventTitle}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {timeText ? <span className="brutal-chip">{timeText}</span> : null}
          {locationText ? <span className="brutal-chip">{locationText}</span> : null}
          <span className="brutal-chip">{participants.length} 位参与角色</span>
        </div>
        <p className="body-copy mt-5">{eventSummary}</p>

        <div className="mt-6 space-y-3">
          <p className="text-xs font-black uppercase tracking-[0.16em]">角色交叉点</p>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            {participants.slice(0, 6).map((participant) => (
              <Link key={participant.id} href={`/story/entity/${participant.id}`}>
                <div className="graph-node bg-aqua">
                  <p className="text-[11px] font-black uppercase tracking-[0.14em]">
                    {participant.role || participant.relation_type || participant.entity_type}
                  </p>
                  <p className="mt-2 text-xl font-black">{participant.display_name}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link href={`/review/events/${eventId}`} className="brutal-action brutal-action-secondary">
            审核关联
          </Link>
          <Link href={`/curation/events/${eventId}`} className="brutal-action brutal-action-primary">
            编辑事件
          </Link>
        </div>
      </Panel>

      <Panel className="p-6" tone="time" intensity="quiet">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="section-kicker">关联轨道</p>
            <p className="mt-2 text-base font-semibold leading-relaxed text-muted">
              用一条纵向轨把当前事件和最强关联节点串起来，方便直接看出图谱里的“下一跳”。
            </p>
          </div>
          <div className="border-4 border-ink bg-canvas px-4 py-3 shadow-brutalSoft">
            <p className="text-xs font-black uppercase tracking-[0.16em]">相关事件</p>
            <p className="mt-2 text-3xl font-black">{sortedRelatedEvents.length}</p>
          </div>
        </div>

        <div className="mt-6 space-y-3">
          {sortedRelatedEvents.length ? (
            sortedRelatedEvents.map((item, index) => {
              const active = item.id === activeRelatedEvent?.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveRelatedId(item.id)}
                  className={`grid w-full gap-4 border-4 border-ink px-4 py-4 text-left shadow-brutalSoft transition-transform hover:-translate-y-1 md:grid-cols-[96px_1fr_auto] ${
                    active ? "bg-canvas" : "bg-bone"
                  }`}
                >
                  <div className="flex flex-col justify-between">
                    <p className="text-[11px] font-black uppercase tracking-[0.14em]">Link {index + 1}</p>
                    <p className="text-xl font-black">{Math.round(item.connection_score * 100)}%</p>
                  </div>
                  <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.14em]">
                      {item.time_text ?? item.event_type ?? "关联事件"}
                    </p>
                    <p className="mt-2 text-xl font-black leading-tight">{item.title}</p>
                    <p className="mt-2 line-clamp-2 text-sm font-semibold leading-relaxed text-muted">
                      {item.summary ?? "暂无关联摘要。"}
                    </p>
                  </div>
                  <div className="flex flex-wrap content-start justify-end gap-2">
                    {item.connection_reasons.slice(0, 2).map((reason) => (
                      <span key={`${item.id}-${reason}`} className="brutal-chip">
                        {reason}
                      </span>
                    ))}
                  </div>
                </button>
              );
            })
          ) : (
            <div className="empty-state">
              当前还没有足够强的事件连接。后续可以从审核页或校对页继续补全图谱边。
            </div>
          )}
        </div>
      </Panel>

      <Panel className="p-6" tone="story" intensity="quiet">
        <p className="section-kicker">焦点节点</p>
        {activeRelatedEvent ? (
          <>
            <p className="mt-4 text-3xl font-black leading-tight">{activeRelatedEvent.title}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {activeRelatedEvent.time_text ? <span className="brutal-chip">{activeRelatedEvent.time_text}</span> : null}
              {activeRelatedEvent.event_type ? <span className="brutal-chip">{activeRelatedEvent.event_type}</span> : null}
              {activeRelatedEvent.distance_days !== null ? (
                <span className="brutal-chip">
                  {activeRelatedEvent.distance_days === 0 ? "同日" : `${activeRelatedEvent.distance_days} 天间隔`}
                </span>
              ) : null}
            </div>
            <p className="mt-5 text-base font-semibold leading-relaxed text-muted">
              {activeRelatedEvent.summary ?? "暂无关联事件的详细摘要。"}
            </p>

            <div className="mt-6 space-y-4">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em]">连接原因</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {activeRelatedEvent.connection_reasons.map((reason) => (
                    <span key={`${activeRelatedEvent.id}-${reason}`} className="brutal-chip">
                      {reason}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em]">共享人物</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {activeRelatedEvent.shared_participants.length ? (
                    activeRelatedEvent.shared_participants.map((name) => (
                      <span key={`${activeRelatedEvent.id}-${name}`} className="brutal-chip">
                        {name}
                      </span>
                    ))
                  ) : (
                    <p className="text-sm font-bold">这条边更多来自时间或语义相似，而不是共享人物。</p>
                  )}
                </div>
              </div>
            </div>

            {activeRelatedEvent.source_note_title ? (
              <p className="mt-6 text-sm font-black uppercase tracking-[0.16em]">
                来源卷宗 {activeRelatedEvent.source_note_title}
              </p>
            ) : null}

            <div className="mt-6 flex flex-wrap gap-3">
              <Link href={`/events/${activeRelatedEvent.id}`} className="brutal-action brutal-action-secondary">
                打开事件
              </Link>
              <Link href={`/review/events/${activeRelatedEvent.id}`} className="brutal-action brutal-action-info">
                进入审核
              </Link>
            </div>
          </>
        ) : (
          <div className="mt-4 text-base font-bold leading-relaxed">
            暂无焦点节点。等更多卷宗进入之后，这里会形成可追踪的事件链路。
          </div>
        )}
      </Panel>
    </section>
  );
}
