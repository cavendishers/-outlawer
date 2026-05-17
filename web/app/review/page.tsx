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
      <main className="space-y-4">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <h1 className="workbench-title">审核队列</h1>
              <p className="workbench-lede">
                把自动抽取的合并候选转成可追责的图谱决策，优先处理高相似、共享人物或时间接近的记录。
              </p>
            </div>
            <div className="flex flex-wrap justify-start gap-2 md:justify-end">
              <span className="workbench-stamp bg-canvas">候选 {items.length}</span>
              <span className="workbench-stamp bg-gold">待处理 {pendingCount}</span>
              <span className="workbench-stamp bg-aqua">人物 {entityCount}</span>
              <span className="workbench-stamp bg-peach">事件 {eventCount}</span>
            </div>
          </div>
        </section>

        <section className="border-4 border-ink bg-canvas px-4 py-3 shadow-brutalSoft">
          <div className="grid gap-3 md:grid-cols-[minmax(12rem,16rem)_minmax(12rem,16rem)_1fr] md:items-end">
            <label htmlFor="review-status" className="grid gap-1 text-xs font-black tracking-[0.12em]">
              队列状态
              <select
                id="review-status"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
                className="brutal-input px-3 py-2 text-sm font-black"
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label htmlFor="review-object-type" className="grid gap-1 text-xs font-black tracking-[0.12em]">
              对象类型
              <select
                id="review-object-type"
                value={objectType}
                onChange={(event) => setObjectType(event.target.value)}
                className="brutal-input px-3 py-2 text-sm font-black"
              >
                <option value="">全部对象</option>
                <option value="entity">人物</option>
                <option value="event">事件</option>
              </select>
            </label>

            <p className="text-sm font-bold leading-relaxed text-ink/60 md:text-right">
              这里展示当前筛选下的候选，不用额外大数字抢占审核内容。
            </p>
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
