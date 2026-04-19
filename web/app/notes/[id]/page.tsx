"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type NoteDetail = {
  id: string;
  title: string;
  summary: string | null;
  canonical_text: string | null;
  status: string;
  primary_time: string | null;
  category: string | null;
};

type ExtractionRunItem = {
  id: string;
  status: string;
  extractor_name: string;
  extractor_version: string;
  created_at: string | null;
  summary: {
    title: string;
    category: string;
    entity_count: number;
    event_count: number;
    relation_count: number;
    similarity_hint_count: number;
  };
};

type ExtractionRunList = {
  items: ExtractionRunItem[];
  total: number;
};

type ExtractionCompare = {
  base_run: ExtractionRunItem;
  candidate_run: ExtractionRunItem;
  diff: {
    changed: boolean;
    summary: {
      changed: boolean;
      fields: Array<{
        field: string;
        base: string | string[] | number | boolean | null;
        candidate: string | string[] | number | boolean | null;
        changed: boolean;
      }>;
    };
    entities: { changed: boolean; added: Array<{ name: string }>; removed: Array<{ name: string }>; changed_items: Array<{ key: string }> };
    events: { changed: boolean; added: Array<{ title: string }>; removed: Array<{ title: string }>; changed_items: Array<{ key: string }> };
    relations: { changed: boolean; added: Array<{ key: string }>; removed: Array<{ key: string }>; changed_items: Array<{ key: string }> };
    similarity_hints: { changed: boolean; added: Array<{ key: string }>; removed: Array<{ key: string }>; changed_items: Array<{ key: string }> };
    style_payload: { changed: boolean };
  };
};

export default function NotePage() {
  const params = useParams<{ id: string }>();
  const [note, setNote] = useState<NoteDetail | null>(null);
  const [noteId, setNoteId] = useState("");
  const [runs, setRuns] = useState<ExtractionRunItem[]>([]);
  const [compare, setCompare] = useState<ExtractionCompare | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!params?.id) return;
    setNoteId(params.id);
    apiFetch<NoteDetail>(`/notes/${params.id}`)
      .then((data) => {
        setNote(data);
        setError("");
      })
      .catch((err) => {
        setNote(null);
        setError(err instanceof Error ? err.message : "卷宗加载失败");
      });

    apiFetch<ExtractionRunList>(`/notes/${params.id}/extraction-runs`)
      .then((data) => {
        setRuns(data.items);
        if (data.items.length >= 2) {
          return apiFetch<ExtractionCompare>(
            `/notes/${params.id}/extraction-runs/compare?base_run_id=${data.items[1].id}&candidate_run_id=${data.items[0].id}`,
          ).then((compareData) => {
            setCompare(compareData);
          });
        }
        setCompare(null);
        return null;
      })
      .catch(() => {
        setRuns([]);
        setCompare(null);
      });
  }, [params]);

  return (
    <AuthGate>
      <main className="space-y-6">
        <Panel className="p-6" tone="default">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm font-black uppercase">{note?.status ?? "loading"}</p>
            {note?.primary_time ? (
              <p className="text-sm font-black uppercase">{note.primary_time.slice(0, 10)}</p>
            ) : null}
          </div>
          <h1 className="mt-2 text-5xl font-black">{note?.title ?? "卷宗载入中"}</h1>
          <p className="mt-4 text-lg font-semibold">{note?.summary ?? "暂无摘要"}</p>
          {note?.category ? <p className="mt-3 text-sm font-black uppercase tracking-[0.16em]">{note.category}</p> : null}
        </Panel>
        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}
        <Panel className="p-6" tone="default">
          <p className="text-sm font-black uppercase">Canonical Text</p>
          <p className="mt-4 whitespace-pre-wrap text-base font-medium">{note?.canonical_text}</p>
        </Panel>
        <Panel className="p-6" tone="paper">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.16em]">Extraction Runs</p>
              <h2 className="mt-2 text-3xl font-black">提取运行记录</h2>
            </div>
            <p className="text-sm font-black uppercase">{runs.length} 次</p>
          </div>
          {runs.length ? (
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {runs.map((run, index) => (
                <div key={run.id} className="border-4 border-ink bg-white/70 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs font-black uppercase tracking-[0.16em]">
                      {index === 0 ? "latest run" : `run ${runs.length - index}`}
                    </p>
                    <p className="text-xs font-black uppercase">{run.status}</p>
                  </div>
                  <p className="mt-3 text-2xl font-black">{run.summary.title || "未命名提取运行"}</p>
                  <p className="mt-2 text-sm font-semibold">
                    {run.extractor_name} / {run.extractor_version}
                  </p>
                  <p className="mt-2 text-xs font-black uppercase tracking-[0.12em]">
                    {run.created_at ? run.created_at.slice(0, 19).replace("T", " ") : "时间未知"}
                  </p>
                  <p className="mt-4 text-sm font-medium">
                    实体 {run.summary.entity_count} · 事件 {run.summary.event_count} · 关系 {run.summary.relation_count} · 相似提示{" "}
                    {run.summary.similarity_hint_count}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-base font-medium">当前还没有可展示的提取运行记录。</p>
          )}
          {compare ? (
            <div className="mt-6 border-4 border-ink bg-[var(--surface-signal-soft)] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-black uppercase tracking-[0.16em]">Diff Snapshot</p>
                  <h3 className="mt-2 text-2xl font-black">最近两次运行差异</h3>
                </div>
                <p className="text-sm font-black uppercase">
                  {compare.diff.changed ? "changed" : "unchanged"}
                </p>
              </div>
              <p className="mt-4 text-sm font-semibold">
                基准：{compare.base_run.extractor_name} / {compare.base_run.extractor_version}
              </p>
              <p className="text-sm font-semibold">
                当前：{compare.candidate_run.extractor_name} / {compare.candidate_run.extractor_version}
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="border-4 border-ink bg-white/70 p-4">
                  <p className="text-xs font-black uppercase tracking-[0.16em]">Summary</p>
                  {compare.diff.summary.fields.filter((field) => field.changed).length ? (
                    <div className="mt-3 space-y-3">
                      {compare.diff.summary.fields
                        .filter((field) => field.changed)
                        .map((field) => (
                          <div key={field.field}>
                            <p className="text-sm font-black uppercase">{field.field}</p>
                            <p className="mt-1 text-sm font-medium">旧：{formatDiffValue(field.base)}</p>
                            <p className="text-sm font-medium">新：{formatDiffValue(field.candidate)}</p>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm font-medium">摘要字段没有变化。</p>
                  )}
                </div>
                <div className="border-4 border-ink bg-white/70 p-4">
                  <p className="text-xs font-black uppercase tracking-[0.16em]">Graph Delta</p>
                  <div className="mt-3 space-y-3 text-sm font-medium">
                    <p>新增人物：{formatNamedItems(compare.diff.entities.added, "name")}</p>
                    <p>移除人物：{formatNamedItems(compare.diff.entities.removed, "name")}</p>
                    <p>变更事件：{compare.diff.events.changed_items.length}</p>
                    <p>新增关系：{compare.diff.relations.added.length}</p>
                    <p>移除关系：{compare.diff.relations.removed.length}</p>
                    <p>风格视图：{compare.diff.style_payload.changed ? "有变化" : "无变化"}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </Panel>
        {noteId ? (
          <Link
            href={`/story/note/${noteId}`}
            className="brutal-action brutal-action-primary text-lg"
          >
            查看中二风版本
          </Link>
        ) : null}
      </main>
    </AuthGate>
  );
}

function formatNamedItems<T extends Record<string, string>>(items: T[], key: keyof T): string {
  if (!items.length) return "无";
  return items.map((item) => item[key]).join("、");
}

function formatDiffValue(value: string | string[] | number | boolean | null): string {
  if (Array.isArray(value)) return value.join("、") || "无";
  if (value === null || value === "") return "无";
  return String(value);
}
