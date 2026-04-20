"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { EventAssociationWorkspace } from "@/components/event-association-workspace";
import { EventConstellation } from "@/components/event-constellation";
import { Panel } from "@/components/panel";
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
        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <Panel className="p-6 md:p-8" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.2em]">Event Record</p>
            <h1 className="mt-3 font-display text-[clamp(2.3rem,5vw,4.6rem)] leading-[0.9]">
              {event?.title ?? "事件详情载入中"}
            </h1>
            <p className="mt-4 text-lg font-bold leading-relaxed">
              {event?.summary ?? "系统正在展开事件摘要。"}
            </p>
          </Panel>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <Panel className="p-5" tone="time">
              <p className="text-xs font-black uppercase tracking-[0.16em]">时间锚点</p>
              <p className="mt-3 text-2xl font-black">{event?.time_text ?? "待校准"}</p>
            </Panel>
            <Panel className="p-5" tone="info">
              <p className="text-xs font-black uppercase tracking-[0.16em]">地点 / 置信度</p>
              <p className="mt-3 text-2xl font-black">{event?.location_text ?? "未标注地点"}</p>
              {event?.confidence_score ? (
                <p className="mt-3 text-sm font-black uppercase tracking-[0.16em]">
                  {Math.round(event.confidence_score * 100)}% confidence
                </p>
              ) : null}
            </Panel>
          </div>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Panel className="p-6" tone="default">
            <div className="flex flex-wrap gap-2 text-xs font-black uppercase tracking-[0.12em]">
              {event?.event_type ? <span className="brutal-chip">{event.event_type}</span> : null}
              {event?.status ? <span className="brutal-chip">{event.status}</span> : null}
              {event?.time_precision ? (
                <span className="brutal-chip">{event.time_precision}</span>
              ) : null}
            </div>
            <p className="mt-5 text-sm font-black uppercase tracking-[0.16em]">事件描述</p>
            <p className="mt-4 whitespace-pre-wrap text-base font-semibold leading-relaxed">
              {event?.description ?? event?.summary ?? "暂无更长描述。"}
            </p>
          </Panel>

          <Panel className="p-6" tone="info">
            <p className="text-sm font-black uppercase tracking-[0.16em]">来源卷宗</p>
            {event?.source_note_id ? (
            <div className="mt-4 flex flex-wrap gap-3">
              <Link
                href={`/notes/${event.source_note_id}`}
                className="brutal-action brutal-action-secondary text-lg"
              >
                  {event.source_note_title ?? "查看来源笔记"}
                </Link>
                <Link
                  href={`/curation/events/${event.id}`}
                  className="brutal-action brutal-action-primary text-lg"
                >
                  进入校对台
                </Link>
              </div>
            ) : (
              <div className="mt-4 flex flex-wrap gap-3">
                <p className="text-base font-bold">当前事件未绑定来源卷宗。</p>
                {event ? (
                  <Link
                    href={`/curation/events/${event.id}`}
                    className="brutal-action brutal-action-primary text-lg"
                  >
                    进入校对台
                  </Link>
                ) : null}
              </div>
            )}
            {event ? (
              <div className="mt-4 flex flex-wrap gap-3">
                <Link
                  href={`/graph?event_id=${event.id}`}
                  className="brutal-action brutal-action-secondary text-lg"
                >
                  打开图谱工作台
                </Link>
              </div>
            ) : null}
          </Panel>
        </section>

        <Panel className="p-6" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.16em]">参与角色</p>
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {(event?.participants ?? []).map((participant) => (
              <Link key={participant.id} href={`/story/entity/${participant.id}`}>
                <Panel className="h-full p-5 transition-transform hover:-translate-y-1" tone="default">
                  <p className="text-xs font-black uppercase tracking-[0.16em]">{participant.entity_type}</p>
                  <p className="mt-3 text-2xl font-black">{participant.display_name}</p>
                  <p className="mt-3 text-sm font-bold">
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

        <Panel className="p-6 md:p-8" tone="story">
          <p className="text-sm font-black uppercase tracking-[0.16em]">事件关联视图</p>
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
