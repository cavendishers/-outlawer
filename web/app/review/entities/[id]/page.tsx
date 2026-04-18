"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, startTransition, useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { ReviewCandidateCard } from "@/components/review-candidate-card";
import { apiFetch } from "@/lib/api";
import { EntityTimelineFragment, MergeCandidateItem } from "@/lib/review";

type EntityReviewContext = {
  entity: {
    id: string;
    entity_type: string;
    canonical_name: string;
    display_name: string;
    description: string | null;
    aliases: string[];
    confidence_score: number | null;
    first_seen_at: string | null;
    last_seen_at: string | null;
  };
  aliases: Array<{
    id: string;
    alias: string;
    normalized_alias: string;
    alias_type: string;
    created_at: string | null;
  }>;
  stats: {
    related_event_count: number;
    related_note_count: number;
    alias_count: number;
    candidate_count: number;
  };
  timeline_fragments: EntityTimelineFragment[];
  candidates: MergeCandidateItem[];
};

export default function EntityReviewPage() {
  const params = useParams<{ id: string }>();
  const entityId = params?.id;
  const [context, setContext] = useState<EntityReviewContext | null>(null);
  const [aliasInput, setAliasInput] = useState("");
  const [busyId, setBusyId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!entityId) return;
    apiFetch<EntityReviewContext>(`/review/entities/${entityId}/context`)
      .then((data) => {
        startTransition(() => {
          setContext(data);
          setError("");
        });
      })
      .catch((err) => {
        startTransition(() => {
          setContext(null);
          setError(err instanceof Error ? err.message : "人物审核上下文加载失败");
        });
      });
  }, [entityId]);

  async function refreshContext() {
    if (!entityId) return;
    const data = await apiFetch<EntityReviewContext>(`/review/entities/${entityId}/context`);
    startTransition(() => {
      setContext(data);
    });
  }

  async function handleAccept(candidateId: string, survivorId: string, resolution: "merge" | "alias_only") {
    const note = window.prompt("可选备注：说明这次处理原因", "")?.trim() || undefined;
    setBusyId(candidateId);
    try {
      await apiFetch(`/review/merge-candidates/${candidateId}/accept`, {
        method: "POST",
        body: JSON.stringify({ resolution, survivor_id: survivorId, note }),
      });
      await refreshContext();
      startTransition(() => {
        setMessage(resolution === "alias_only" ? "别名已确认。" : "人物候选已合并。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "处理人物候选失败");
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
        setMessage("人物候选已驳回。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "驳回人物候选失败");
      });
    } finally {
      setBusyId("");
    }
  }

  async function handleAliasSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const alias = aliasInput.trim();
    if (!alias || !entityId) return;
    setBusyId("alias");
    try {
      await apiFetch(`/review/entities/${entityId}/aliases`, {
        method: "POST",
        body: JSON.stringify({ alias }),
      });
      setAliasInput("");
      await refreshContext();
      startTransition(() => {
        setMessage("手动别名已登记。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "新增别名失败");
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
            <p className="text-sm font-black uppercase tracking-[0.2em]">Entity Review</p>
            <h1 className="mt-3 font-display text-[clamp(2.4rem,5vw,4.8rem)] leading-[0.9]">
              {context?.entity.display_name ?? "人物审核中"}
            </h1>
            <p className="mt-4 text-lg font-bold leading-relaxed">
              {context?.entity.description ?? "这里用于校对人物别名、时间线片段，以及与其他同名节点的合并决策。"}
            </p>
            {context ? (
              <div className="mt-6 flex flex-wrap gap-3">
                <Link href={`/curation/entities/${context.entity.id}`} className="brutal-action brutal-action-primary text-lg">
                  进入校对台
                </Link>
                <Link href={`/story/entity/${context.entity.id}`} className="brutal-action brutal-action-secondary text-lg">
                  查看人物故事页
                </Link>
              </div>
            ) : null}
          </Panel>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <Panel className="p-5" tone="info">
              <p className="text-xs font-black uppercase tracking-[0.16em]">关联事件</p>
              <p className="mt-3 text-5xl font-black">{context?.stats.related_event_count ?? 0}</p>
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
            <p className="text-sm font-black uppercase tracking-[0.16em]">别名索引</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {(context?.aliases ?? []).map((alias) => (
                <span key={alias.id} className="brutal-chip">
                  {alias.alias}
                </span>
              ))}
              {context && context.aliases.length === 0 ? <p className="text-base font-bold">暂无别名。</p> : null}
            </div>
            <form className="mt-6 space-y-3" onSubmit={handleAliasSubmit}>
              <label htmlFor="manual-alias" className="text-xs font-black uppercase tracking-[0.16em]">
                手动确认别名
              </label>
              <input
                id="manual-alias"
                value={aliasInput}
                onChange={(event) => setAliasInput(event.target.value)}
                className="brutal-input w-full text-lg font-semibold"
                placeholder="输入新的可信别名"
              />
              <button
                type="submit"
                disabled={busyId === "alias"}
                className="brutal-action brutal-action-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                写入别名
              </button>
            </form>
          </Panel>

          <Panel className="p-6" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.16em]">人物轨迹片段</p>
            <div className="mt-5 space-y-4">
              {(context?.timeline_fragments ?? []).map((fragment) => (
                <Link key={fragment.event_id} href={`/events/${fragment.event_id}`} className="block transition-transform hover:-translate-y-1">
                  <div className="grid gap-4 lg:grid-cols-[160px_1fr]">
                    <div className="border-4 border-ink bg-gold p-4">
                      <p className="text-xs font-black uppercase tracking-[0.16em]">{fragment.chapter_label}</p>
                      <p className="mt-4 text-2xl font-black">{fragment.time_text ?? "待校时"}</p>
                    </div>
                    <Panel className="p-5" tone="default">
                      <p className="text-xs font-black uppercase tracking-[0.16em]">
                        {fragment.role || fragment.event_type || "事件片段"}
                      </p>
                      <p className="mt-3 text-2xl font-black">{fragment.title}</p>
                      <p className="mt-3 text-sm font-bold leading-relaxed">{fragment.summary ?? "暂无摘要。"}</p>
                    </Panel>
                  </div>
                </Link>
              ))}
              {context && context.timeline_fragments.length === 0 ? (
                <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
                  当前人物还没有时间线片段，后续可通过更多事件挂接补全。
                </div>
              ) : null}
            </div>
          </Panel>
        </section>

        <Panel className="p-6" tone="story">
          <p className="text-sm font-black uppercase tracking-[0.16em]">人物候选队列</p>
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
                当前人物没有待处理合并候选。
              </div>
            ) : null}
          </div>
        </Panel>
      </main>
    </AuthGate>
  );
}
