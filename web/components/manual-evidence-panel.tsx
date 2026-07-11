"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type ManualEvidence = {
  id: string;
  note_id: string | null;
  raw_asset_id: string | null;
  source_title: string;
  excerpt: string | null;
  curator_note: string | null;
  provenance_type: string;
  created_at: string | null;
};

export function ManualEvidencePanel({ targetType, targetId, compact = false }: { targetType: "entity" | "event"; targetId: string; compact?: boolean }) {
  const [items, setItems] = useState<ManualEvidence[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<{ items: ManualEvidence[] }>(`/manual-knowledge/evidence?target_type=${targetType}&target_id=${targetId}`)
      .then((data) => { setItems(data.items); setError(""); })
      .catch((caught) => { setItems([]); setError(caught instanceof Error ? caught.message : "证据加载失败"); });
  }, [targetId, targetType]);

  return (
    <section className={`border-4 border-ink bg-bone shadow-brutal ${compact ? "p-4" : "p-5"}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><p className="section-kicker">手工证据</p><h2 className={`${compact ? "mt-1 text-lg" : "mt-2 text-2xl"} font-black`}>来源与策展依据</h2></div>
        <span className="workbench-stamp bg-aqua">{items.length} 条</span>
      </div>
      {error ? <p className="mt-3 border-2 border-ink bg-ember p-3 text-sm font-bold text-red-950">{error}</p> : null}
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <article key={item.id} className="border-2 border-ink bg-canvas p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <Link href={item.note_id ? `/notes/${item.note_id}` : "/operations"} className="font-black underline decoration-2">{item.source_title}</Link>
              <span className="brutal-chip">{item.note_id ? "笔记" : "原始素材"}</span>
            </div>
            {item.excerpt ? <blockquote className="mt-3 border-l-4 border-ink pl-3 text-sm font-bold leading-relaxed">{item.excerpt}</blockquote> : null}
            {item.curator_note ? <p className="mt-2 text-sm font-bold text-muted">说明：{item.curator_note}</p> : null}
            <p className="mt-2 text-xs font-black text-muted">{formatDate(item.created_at)} · {item.provenance_type}</p>
          </article>
        ))}
        {!items.length && !error ? <p className="text-sm font-bold text-muted">当前对象还没有手工绑定的来源证据。</p> : null}
      </div>
    </section>
  );
}

function formatDate(value: string | null) {
  if (!value) return "时间未知";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}
