"use client";

import Link from "next/link";

import { Panel } from "@/components/panel";
import {
  MergeCandidateItem,
  candidateTypeLabel,
  formatCandidateScore,
  summarizeCandidateReason,
  summaryStatTags,
} from "@/lib/review";

type ReviewCandidateCardProps = {
  candidate: MergeCandidateItem;
  busy?: boolean;
  onAccept?: (candidateId: string, survivorId: string, resolution: "merge" | "alias_only") => void;
  onReject?: (candidateId: string) => void;
};

export function ReviewCandidateCard({ candidate, busy = false, onAccept, onReject }: ReviewCandidateCardProps) {
  const reasonTags = summarizeCandidateReason(candidate.reason);
  const sourceStats = summaryStatTags(candidate.source);
  const candidateStats = summaryStatTags(candidate.candidate);
  const canAct = candidate.status === "pending" && candidate.source?.id && candidate.candidate?.id;

  return (
    <Panel className="p-5 md:p-6" tone={candidate.status === "accepted" ? "success" : "default"}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em]">{candidateTypeLabel(candidate.object_type)}</p>
          <p className="mt-3 text-3xl font-black">{formatCandidateScore(candidate.score)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="brutal-chip">{candidate.status}</span>
          {candidate.reviewed_at ? <span className="brutal-chip">{candidate.reviewed_at.slice(0, 10)}</span> : null}
        </div>
      </div>

      {reasonTags.length ? (
        <div className="mt-5 flex flex-wrap gap-2">
          {reasonTags.map((tag) => (
            <span key={tag} className="brutal-chip">
              {tag}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <Panel className="p-4" tone="default">
          <p className="text-xs font-black uppercase tracking-[0.16em]">源对象</p>
          <p className="mt-3 text-2xl font-black">{candidate.source?.label ?? "对象已不存在"}</p>
          {sourceStats.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {sourceStats.map((tag) => (
                <span key={tag} className="brutal-chip">
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
          {candidate.source?.href ? (
            <Link href={candidate.source.href} className="brutal-action brutal-action-secondary mt-5 text-sm">
              查看源对象
            </Link>
          ) : null}
        </Panel>

        <Panel className="p-4" tone="info">
          <p className="text-xs font-black uppercase tracking-[0.16em]">候选对象</p>
          <p className="mt-3 text-2xl font-black">{candidate.candidate?.label ?? "对象已不存在"}</p>
          {candidateStats.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {candidateStats.map((tag) => (
                <span key={tag} className="brutal-chip">
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
          {candidate.candidate?.href ? (
            <Link href={candidate.candidate.href} className="brutal-action brutal-action-secondary mt-5 text-sm">
              查看候选对象
            </Link>
          ) : null}
        </Panel>
      </div>

      {candidate.review_note ? (
        <p className="mt-5 text-sm font-bold leading-relaxed">审核备注：{candidate.review_note}</p>
      ) : null}

      {canAct && onAccept && onReject ? (
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            disabled={busy}
            className="brutal-action brutal-action-primary disabled:cursor-not-allowed disabled:opacity-60"
            onClick={() => candidate.source?.id && onAccept(candidate.id, candidate.source.id, "merge")}
          >
            保留左侧并合并
          </button>
          <button
            type="button"
            disabled={busy}
            className="brutal-action brutal-action-info disabled:cursor-not-allowed disabled:opacity-60"
            onClick={() => candidate.candidate?.id && onAccept(candidate.id, candidate.candidate.id, "merge")}
          >
            保留右侧并合并
          </button>
          {candidate.object_type === "entity" ? (
            <button
              type="button"
              disabled={busy}
              className="brutal-action brutal-action-secondary disabled:cursor-not-allowed disabled:opacity-60"
              onClick={() => candidate.source?.id && onAccept(candidate.id, candidate.source.id, "alias_only")}
            >
              只登记别名
            </button>
          ) : null}
          <button
            type="button"
            disabled={busy}
            className="brutal-action border-ember bg-ember text-ink disabled:cursor-not-allowed disabled:opacity-60"
            onClick={() => onReject(candidate.id)}
          >
            驳回候选
          </button>
        </div>
      ) : null}
    </Panel>
  );
}
