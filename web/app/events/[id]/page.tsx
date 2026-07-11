"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { AddToCollectionControl } from "@/components/add-to-collection-control";
import { EventAssociationWorkspace } from "@/components/event-association-workspace";
import { EventConstellation } from "@/components/event-constellation";
import { Panel } from "@/components/panel";
import { ManualEvidencePanel } from "@/components/manual-evidence-panel";
import { apiFetch } from "@/lib/api";

type EventDetail = {
  id: string;
  title: string;
  summary: string | null;
  description: string | null;
  event_type: string | null;
  status: string;
  start_time: string | null;
  end_time: string | null;
  time_precision: string | null;
  time_text: string | null;
  location_text: string | null;
  confidence_score: number | null;
  source_note_id: string | null;
  source_note_title: string | null;
  participants: Array<{
    id: string;
    display_name: string;
    entity_type: string;
    role?: string | null;
    relation_type?: string | null;
    confidence_score?: number | null;
  }>;
  related_events: Array<{
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
  }>;
};

export default function EventDetailPage() {
  const params = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!params?.id) return;
    apiFetch<EventDetail>(`/events/${params.id}`)
      .then((data) => {
        setEvent(data);
        setError("");
      })
      .catch((err) => {
        setEvent(null);
        setError(err instanceof Error ? err.message : "事件详情加载失败");
      });
  }, [params]);

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-4xl">
              <div className="flex flex-wrap gap-2">
                <span className="workbench-stamp bg-gold">{event?.time_text ?? "待校时"}</span>
                <span className="workbench-stamp bg-canvas">{event?.location_text ?? "未标注地点"}</span>
                {event?.event_type ? <span className="workbench-stamp bg-aqua">{event.event_type}</span> : null}
                {event?.confidence_score ? (
                  <span className="workbench-stamp bg-canvas">置信度 {Math.round(event.confidence_score * 100)}%</span>
                ) : null}
              </div>
              <h1 className="workbench-title mt-3">{event?.title ?? "事件详情载入中"}</h1>
              <p className="workbench-lede">{event?.summary ?? "系统正在展开事件摘要。"}</p>
            </div>
            {event ? (
              <div className="flex flex-wrap gap-2">
                <Link href={`/curation/events/${event.id}`} className="tool-action bg-neon">
                  校对事件
                </Link>
                <Link href={`/graph?event_id=${event.id}`} className="tool-action bg-canvas">
                  图谱视图
                </Link>
                <AddToCollectionControl itemType="event" itemId={event.id} label={event.title} />
              </div>
            ) : null}
          </div>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        {event ? <ManualEvidencePanel targetType="event" targetId={event.id} /> : null}

        <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <Panel className="p-6" tone="quiet" intensity="quiet">
            <div className="flex flex-wrap gap-2 text-xs font-black tracking-[0.12em]">
              {event?.event_type ? <span className="brutal-chip">{event.event_type}</span> : null}
              {event?.status ? <span className="brutal-chip">{event.status}</span> : null}
              {event?.time_precision ? (
                <span className="brutal-chip">{event.time_precision}</span>
              ) : null}
            </div>
            <p className="section-kicker mt-5">事件描述</p>
            <p className="body-copy mt-4 whitespace-pre-wrap">
              {event?.description ?? event?.summary ?? "暂无更长描述。"}
            </p>
          </Panel>

          <Panel className="p-6" tone="info" intensity="quiet">
            <p className="section-kicker">下一步</p>
            {event?.source_note_id ? (
              <div className="mt-4 grid gap-3">
                <Link href={`/notes/${event.source_note_id}`} className="tool-action bg-canvas">
                  {event.source_note_title ?? "查看来源笔记"}
                </Link>
                <Link href={`/curation/events/${event.id}`} className="tool-action bg-neon">
                  进入校对台
                </Link>
              </div>
            ) : (
              <div className="mt-4 grid gap-3">
                <p className="text-base font-bold">当前事件未绑定来源卷宗。</p>
                {event ? (
                  <Link href={`/curation/events/${event.id}`} className="tool-action bg-neon">
                    进入校对台
                  </Link>
                ) : null}
              </div>
            )}
            {event ? (
              <div className="mt-3 grid gap-3">
                <Link href={`/graph?event_id=${event.id}`} className="tool-action bg-canvas">
                  打开图谱工作台
                </Link>
              </div>
            ) : null}
          </Panel>
        </section>

        <Panel className="p-6" tone="quiet" intensity="quiet">
          <p className="section-kicker">参与角色</p>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {(event?.participants ?? []).map((participant) => (
              <Link key={participant.id} href={`/story/entity/${participant.id}`}>
                <Panel className="h-full p-5 transition-transform hover:-translate-y-1" tone="quiet" intensity="quiet">
                  <p className="meta-copy">{participant.entity_type}</p>
                  <p className="card-title mt-3">{participant.display_name}</p>
                  <p className="body-copy mt-3">
                    {participant.role || participant.relation_type || "关联角色"}
                  </p>
                </Panel>
              </Link>
            ))}
            {event && event.participants.length === 0 ? (
              <p className="text-base font-bold">当前事件还没有挂接参与角色。</p>
            ) : null}
          </div>
        </Panel>

        <Panel className="p-6 md:p-8" tone="story" intensity="quiet">
          <p className="section-kicker">事件关联视图</p>
          {event ? (
            <div className="mt-5">
              <EventConstellation
                eventTitle={event.title}
                eventSummary={event.summary ?? event.description ?? "等待事件摘要。"}
                participants={event.participants}
                relatedEvents={event.related_events}
              />
            </div>
          ) : null}
          {event && event.related_events.length === 0 ? (
            <div className="surface-inset mt-5 border-4 border-dashed border-ink p-5 text-base font-bold">
              当前还没有足够强的关联事件。随着更多卷宗进入，系统会基于共享人物、时间接近和语义相似度继续补全事件网络。
            </div>
          ) : null}
        </Panel>

        {event ? (
          <EventAssociationWorkspace
            eventId={event.id}
            eventTitle={event.title}
            eventSummary={event.summary ?? event.description ?? "等待事件摘要。"}
            timeText={event.time_text}
            locationText={event.location_text}
            participants={event.participants}
            relatedEvents={event.related_events}
          />
        ) : null}
      </main>
    </AuthGate>
  );
}
