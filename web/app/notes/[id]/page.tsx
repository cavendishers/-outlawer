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
  is_applied: boolean;
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

type ApplyExtractionRunResponse = {
  note: NoteDetail;
  applied_run: ExtractionRunItem;
  replay_actions: ReplayAction[];
};

type ReplayAction = {
  id: string;
  action_type: string;
  created_at: string | null;
  run_id: string;
  previous_run_id: string | null;
  extractor_name: string;
  extractor_version: string;
  note: string | null;
};

type ReplayActionList = {
  items: ReplayAction[];
  total: number;
};

export default function NotePage() {
  const params = useParams<{ id: string }>();
  const [note, setNote] = useState<NoteDetail | null>(null);
  const [noteId, setNoteId] = useState("");
  const [runs, setRuns] = useState<ExtractionRunItem[]>([]);
  const [compare, setCompare] = useState<ExtractionCompare | null>(null);
  const [replayActions, setReplayActions] = useState<ReplayAction[]>([]);
  const [applyingRunId, setApplyingRunId] = useState("");
  const [applyNote, setApplyNote] = useState("");
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

    loadExtractionRuns(params.id)
      .catch(() => {
        setRuns([]);
        setCompare(null);
      });
  }, [params]);

  const loadExtractionRuns = async (targetNoteId: string) => {
    const data = await apiFetch<ExtractionRunList>(`/notes/${targetNoteId}/extraction-runs`);
    const replayActionData = await apiFetch<ReplayActionList>(`/notes/${targetNoteId}/replay-actions`);
    const orderedItems = [...data.items].sort((left, right) => {
      if (left.is_applied !== right.is_applied) {
        return left.is_applied ? -1 : 1;
      }
      const leftTime = left.created_at ? Date.parse(left.created_at) : 0;
      const rightTime = right.created_at ? Date.parse(right.created_at) : 0;
      return rightTime - leftTime;
    });
    setRuns(orderedItems);
    setReplayActions(replayActionData.items);

    const appliedRun = orderedItems.find((item) => item.is_applied) ?? null;
    const latestDifferentRun = orderedItems.find((item) => !item.is_applied) ?? null;
    if (appliedRun && latestDifferentRun) {
      const compareData = await apiFetch<ExtractionCompare>(
        `/notes/${targetNoteId}/extraction-runs/compare?base_run_id=${latestDifferentRun.id}&candidate_run_id=${appliedRun.id}`,
      );
      setCompare(compareData);
      return;
    }

    if (orderedItems.length >= 2) {
      const compareData = await apiFetch<ExtractionCompare>(
        `/notes/${targetNoteId}/extraction-runs/compare?base_run_id=${orderedItems[1].id}&candidate_run_id=${orderedItems[0].id}`,
      );
      setCompare(compareData);
      return;
    }

    setCompare(null);
  };

  const handleApplyRun = async (runId: string) => {
    if (!noteId) return;
    setApplyingRunId(runId);
    try {
      const result = await apiFetch<ApplyExtractionRunResponse>(`/notes/${noteId}/extraction-runs/${runId}/apply`, {
        method: "POST",
        body: JSON.stringify({ note: applyNote }),
      });
      setNote(result.note);
      setReplayActions(result.replay_actions);
      setApplyNote("");
      await loadExtractionRuns(noteId);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "版本应用失败");
    } finally {
      setApplyingRunId("");
    }
  };

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
                      {run.is_applied ? "current projection" : index === 0 ? "latest run" : `run ${runs.length - index}`}
                    </p>
                    <p className="text-xs font-black uppercase">{run.is_applied ? "applied" : run.status}</p>
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
                  <div className="mt-4 flex flex-wrap gap-3">
                    {run.is_applied ? (
                      <span className="border-4 border-ink bg-[var(--surface-success-soft)] px-3 py-2 text-xs font-black uppercase tracking-[0.14em]">
                        当前生效
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="brutal-action brutal-action-primary text-sm"
                        disabled={applyingRunId === run.id}
                        onClick={() => handleApplyRun(run.id)}
                      >
                        {applyingRunId === run.id ? "应用中..." : "回滚到此版本"}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-base font-medium">当前还没有可展示的提取运行记录。</p>
          )}
          <div className="mt-6 border-4 border-ink bg-white/70 p-4">
            <p className="text-xs font-black uppercase tracking-[0.16em]">Replay Note</p>
            <label className="mt-3 block text-sm font-black uppercase tracking-[0.12em]">
              本次回滚备注
            </label>
            <textarea
              value={applyNote}
              onChange={(event) => setApplyNote(event.target.value)}
              className="mt-2 min-h-24 w-full border-4 border-ink bg-white px-3 py-2 text-sm font-medium outline-none"
              placeholder="例如：恢复到上一版提取结果，保留更稳定的人物识别。"
            />
          </div>
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
          <div className="mt-6 border-4 border-ink bg-[var(--surface-info-soft)] p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em]">Replay Audit</p>
                <h3 className="mt-2 text-2xl font-black">重放操作日志</h3>
              </div>
              <p className="text-sm font-black uppercase">{replayActions.length} 条</p>
            </div>
            {replayActions.length ? (
              <div className="mt-4 space-y-3">
                {replayActions.map((action) => (
                  <div key={action.id} className="border-4 border-ink bg-white/70 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs font-black uppercase tracking-[0.16em]">{formatReplayActionType(action.action_type)}</p>
                      <p className="text-xs font-black uppercase">
                        {action.created_at ? action.created_at.slice(0, 19).replace("T", " ") : "时间未知"}
                      </p>
                    </div>
                    <p className="mt-3 text-sm font-semibold">
                      run: {action.run_id} · {action.extractor_name} / {action.extractor_version}
                    </p>
                    <p className="mt-2 text-sm font-medium">
                      上一版本：{action.previous_run_id ?? "无"}
                    </p>
                    <p className="mt-2 text-sm font-medium">
                      备注：{action.note ?? "无"}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm font-medium">当前还没有重放或回滚操作日志。</p>
            )}
          </div>
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

function formatReplayActionType(value: string): string {
  if (value === "apply_extraction_run") return "manual replay";
  if (value === "auto_apply_extraction_run") return "auto apply";
  return value;
}
