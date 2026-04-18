"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { startTransition, useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { ReviewCandidateCard } from "@/components/review-candidate-card";
import { apiFetch } from "@/lib/api";
import { MergeCandidateItem } from "@/lib/review";

type EventReviewContext = {
  event: {
    id: string;
    title: string;
    summary: string | null;
    description: string | null;
    event_type: string | null;
    status: string;
    time_text: string | null;
    location_text: string | null;
    confidence_score: number | null;
    source_note_id: string | null;
    source_note_title: string | null;
    participants: Array<{
      id: string;
      display_name: string;
      entity_type: string;
      role: string | null;
      relation_type: string | null;
      confidence_score: number | null;
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
  stats: {
    participant_count: number;
    linked_note_count: number;
    candidate_count: number;
  };
  candidates: MergeCandidateItem[];
};

export default function EventReviewPage() {
  const params = useParams<{ id: string }>();
  const eventId = params?.id;
  const [context, setContext] = useState<EventReviewContext | null>(null);
  const [busyId, setBusyId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!eventId) return;
    apiFetch<EventReviewContext>(`/review/events/${eventId}/context`)
      .then((data) => {
        startTransition(() => {
          setContext(data);
          setError("");
        });
      })
      .catch((err) => {
        startTransition(() => {
          setContext(null);
          setError(err instanceof Error ? err.message : "事件审核上下文加载失败");
        });
      });
  }, [eventId]);

  async function refreshContext() {
    if (!eventId) return;
    const data = await apiFetch<EventReviewContext>(`/review/events/${eventId}/context`);
    startTransition(() => {
      setContext(data);
    });
  }

  async function handleAccept(candidateId: string, survivorId: string, resolution: "merge" | "alias_only") {
    if (resolution !== "merge") return;
    const note = window.prompt("可选备注：说明这次事件合并原因", "")?.trim() || undefined;
    setBusyId(candidateId);
    try {
      await apiFetch(`/review/merge-candidates/${candidateId}/accept`, {
        method: "POST",
        body: JSON.stringify({ resolution, survivor_id: survivorId, note }),
      });
      await refreshContext();
      startTransition(() => {
        setMessage("事件候选已合并。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "处理事件候选失败");
      });
    } finally {
      setBusyId("");
    }
  }

  async function handleReject(candidateId: string) {
    const reason = window.prompt("请输入驳回原因", "manual_reject")?.trim();
    if (!reason) return;
    const note = window.prompt("可选备注：补充说明", "")?.trim() || undefined;
    setBusyId(candidateId);
    try {
      await apiFetch(`/review/merge-candidates/${candidateId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason, note }),
      });
      await refreshContext();
      startTransition(() => {
        setMessage("事件候选已驳回。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "驳回事件候选失败");
      });
    } finally {
      setBusyId("");
    }
  }

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Panel className="p-6 md:p-8" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.2em]">Event Review</p>
            <h1 className="mt-3 font-display text-[clamp(2.4rem,5vw,4.8rem)] leading-[0.9]">
              {context?.event.title ?? "事件审核中"}
            </h1>
            <p className="mt-4 text-lg font-bold leading-relaxed">
              {context?.event.summary ?? context?.event.description ?? "这里会显示事件上下文、参与角色和可疑重复项。"}
            </p>
          </Panel>

          <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
            <Panel className="p-5" tone="time">
              <p className="text-xs font-black uppercase tracking-[0.16em]">时间锚点</p>
              <p className="mt-3 text-3xl font-black">{context?.event.time_text ?? "待校准"}</p>
            </Panel>
            <Panel className="p-5" tone="info">
              <p className="text-xs font-black uppercase tracking-[0.16em]">参与角色</p>
              <p className="mt-3 text-5xl font-black">{context?.stats.participant_count ?? 0}</p>
            </Panel>
            <Panel className="p-5" tone="signal">
              <p className="text-xs font-black uppercase tracking-[0.16em]">待审候选</p>
              <p className="mt-3 text-5xl font-black">{context?.stats.candidate_count ?? 0}</p>
            </Panel>
          </div>
        </section>

        {message ? (
          <Panel className="p-5 text-lg font-bold" tone="success">
            {message}
          </Panel>
        ) : null}

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel className="p-6" tone="info">
            <p className="text-sm font-black uppercase tracking-[0.16em]">参与角色</p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {(context?.event.participants ?? []).map((participant) => (
                <Link key={participant.id} href={`/review/entities/${participant.id}`}>
                  <Panel className="h-full p-5 transition-transform hover:-translate-y-1" tone="default">
                    <p className="text-xs font-black uppercase tracking-[0.16em]">{participant.entity_type}</p>
                    <p className="mt-3 text-2xl font-black">{participant.display_name}</p>
                    <p className="mt-3 text-sm font-bold">
                      {participant.role || participant.relation_type || "关联角色"}
                    </p>
                  </Panel>
                </Link>
              ))}
              {context && context.event.participants.length === 0 ? (
                <p className="text-base font-bold">当前事件还没有参与角色。</p>
              ) : null}
            </div>

            {context?.event.source_note_id ? (
              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href={`/notes/${context.event.source_note_id}`}
                  className="brutal-action brutal-action-secondary"
                >
                  查看来源卷宗
                </Link>
                <Link
                  href={`/curation/events/${context.event.id}`}
                  className="brutal-action brutal-action-primary"
                >
                  进入校对台
                </Link>
              </div>
            ) : null}
          </Panel>

          <Panel className="p-6" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.16em]">关联事件提示</p>
            <div className="mt-5 space-y-4">
              {(context?.event.related_events ?? []).map((item) => (
                <Link key={item.id} href={`/review/events/${item.id}`} className="block transition-transform hover:-translate-y-1">
                  <Panel className="p-5" tone="default">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-black uppercase tracking-[0.16em]">
                          {item.time_text ?? item.event_type ?? "关联事件"}
                        </p>
                        <p className="mt-3 text-2xl font-black">{item.title}</p>
                      </div>
                      <span className="brutal-chip">{Math.round(item.connection_score * 100)}%</span>
                    </div>
                    <p className="mt-3 text-sm font-bold leading-relaxed">{item.summary ?? "暂无摘要。"}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {item.connection_reasons.map((reason) => (
                        <span key={reason} className="brutal-chip">
                          {reason}
                        </span>
                      ))}
                    </div>
                  </Panel>
                </Link>
              ))}
              {context && context.event.related_events.length === 0 ? (
                <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
                  当前事件还没有额外关联提示。
                </div>
              ) : null}
            </div>
          </Panel>
        </section>

        <Panel className="p-6" tone="story">
          <p className="text-sm font-black uppercase tracking-[0.16em]">事件候选队列</p>
          <div className="mt-5 space-y-4">
            {(context?.candidates ?? []).map((candidate) => (
              <ReviewCandidateCard
                key={candidate.id}
                candidate={candidate}
                busy={busyId === candidate.id}
                onAccept={handleAccept}
                onReject={handleReject}
              />
            ))}
            {context && context.candidates.length === 0 ? (
              <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
                当前事件没有待处理合并候选。
              </div>
            ) : null}
          </div>
        </Panel>
      </main>
    </AuthGate>
  );
}
