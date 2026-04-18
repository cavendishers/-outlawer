"use client";

import { startTransition, useEffect, useMemo, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { ReviewCandidateCard } from "@/components/review-candidate-card";
import { apiFetch } from "@/lib/api";
import { MergeCandidateItem } from "@/lib/review";

type MergeCandidateListResponse = {
  items: MergeCandidateItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

const statusOptions = [
  { value: "pending", label: "待审核" },
  { value: "accepted", label: "已接受" },
  { value: "rejected", label: "已驳回" },
  { value: "superseded", label: "已失效" },
];

export default function ReviewPage() {
  const [items, setItems] = useState<MergeCandidateItem[]>([]);
  const [status, setStatus] = useState("pending");
  const [objectType, setObjectType] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (objectType) params.set("object_type", objectType);

    setLoading(true);
    apiFetch<MergeCandidateListResponse>(`/review/merge-candidates?${params.toString()}`)
      .then((data) => {
        startTransition(() => {
          setItems(data.items);
          setError("");
          setLoading(false);
        });
      })
      .catch((err) => {
        startTransition(() => {
          setItems([]);
          setError(err instanceof Error ? err.message : "审核队列加载失败");
          setLoading(false);
        });
      });
  }, [objectType, status]);

  const pendingCount = useMemo(() => items.filter((item) => item.status === "pending").length, [items]);
  const entityCount = useMemo(() => items.filter((item) => item.object_type === "entity").length, [items]);
  const eventCount = useMemo(() => items.filter((item) => item.object_type === "event").length, [items]);

  async function handleAccept(candidateId: string, survivorId: string, resolution: "merge" | "alias_only") {
    const note = window.prompt("可选备注：说明这次接受的原因", "")?.trim() || undefined;
    setBusyId(candidateId);
    try {
      await apiFetch(`/review/merge-candidates/${candidateId}/accept`, {
        method: "POST",
        body: JSON.stringify({ resolution, survivor_id: survivorId, note }),
      });
      startTransition(() => {
        setItems((current) =>
          current.map((item) =>
            item.id === candidateId
              ? {
                  ...item,
                  status: "accepted",
                  review_note: note ?? item.review_note,
                  reviewed_at: new Date().toISOString(),
                }
              : item,
          ),
        );
        setMessage(resolution === "alias_only" ? "候选已作为别名关系确认。" : "候选已完成合并。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "接受候选失败");
      });
    } finally {
      setBusyId("");
    }
  }

  async function handleReject(candidateId: string) {
    const reason = window.prompt("请输入驳回原因", "manual_reject")?.trim();
    if (!reason) return;
    const note = window.prompt("可选备注：补充为什么不合并", "")?.trim() || undefined;
    setBusyId(candidateId);
    try {
      await apiFetch(`/review/merge-candidates/${candidateId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason, note }),
      });
      startTransition(() => {
        setItems((current) =>
          current.map((item) =>
            item.id === candidateId
              ? {
                  ...item,
                  status: "rejected",
                  review_note: note ?? reason,
                  reviewed_at: new Date().toISOString(),
                }
              : item,
          ),
        );
        setMessage("候选已驳回。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "驳回候选失败");
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
            <p className="text-sm font-black uppercase tracking-[0.2em]">Review Queue</p>
            <h1 className="mt-3 font-display text-[clamp(2.5rem,6vw,5rem)] leading-[0.9]">实体与事件审核台</h1>
            <p className="mt-4 max-w-3xl text-lg font-bold leading-relaxed">
              这里负责把自动抽取的候选关系变成可追责的图谱决策。每次操作都会留下审核记录，后续可以继续扩展成多人协作校对流。
            </p>
          </Panel>

          <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
            <Panel className="p-5" tone="signal">
              <p className="text-xs font-black uppercase tracking-[0.16em]">当前候选</p>
              <p className="mt-3 text-5xl font-black">{items.length}</p>
            </Panel>
            <Panel className="p-5" tone="info">
              <p className="text-xs font-black uppercase tracking-[0.16em]">人物候选</p>
              <p className="mt-3 text-5xl font-black">{entityCount}</p>
            </Panel>
            <Panel className="p-5" tone="time">
              <p className="text-xs font-black uppercase tracking-[0.16em]">事件候选</p>
              <p className="mt-3 text-5xl font-black">{eventCount}</p>
            </Panel>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1fr_0.8fr_0.8fr]">
          <Panel className="p-5" tone="default">
            <label htmlFor="review-status" className="text-xs font-black uppercase tracking-[0.16em]">
              队列状态
            </label>
            <select
              id="review-status"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="brutal-input mt-3 w-full text-lg font-semibold"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Panel>

          <Panel className="p-5" tone="info">
            <label htmlFor="review-object-type" className="text-xs font-black uppercase tracking-[0.16em]">
              对象类型
            </label>
            <select
              id="review-object-type"
              value={objectType}
              onChange={(event) => setObjectType(event.target.value)}
              className="brutal-input mt-3 w-full text-lg font-semibold"
            >
              <option value="">全部对象</option>
              <option value="entity">人物</option>
              <option value="event">事件</option>
            </select>
          </Panel>

          <Panel className="p-5" tone="story">
            <p className="text-xs font-black uppercase tracking-[0.16em]">待处理数量</p>
            <p className="mt-3 text-5xl font-black">{pendingCount}</p>
            <p className="mt-4 text-sm font-bold leading-relaxed">
              推荐优先清理高分候选，尤其是共享人物和时间高度接近的事件对。
            </p>
          </Panel>
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

        {loading ? (
          <Panel className="p-6 text-lg font-bold" tone="default">
            审核队列载入中...
          </Panel>
        ) : items.length ? (
          <div className="space-y-4">
            {items.map((candidate) => (
              <ReviewCandidateCard
                key={candidate.id}
                candidate={candidate}
                busy={busyId === candidate.id}
                onAccept={handleAccept}
                onReject={handleReject}
              />
            ))}
          </div>
        ) : (
          <Panel className="p-6 text-lg font-bold" tone="default">
            当前筛选条件下没有候选。先继续导入内容，或者切换状态查看已处理记录。
          </Panel>
        )}
      </main>
    </AuthGate>
  );
}
