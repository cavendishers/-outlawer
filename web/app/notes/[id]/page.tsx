"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { AuthGate } from "@/components/auth-gate";
import { AddToCollectionControl } from "@/components/add-to-collection-control";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type NoteDetail = {
  id: string;
  title: string;
  summary: string | null;
  canonical_text: string | null;
  status: string;
  asset_id: string | null;
  active_projection_id: string | null;
  primary_time: string | null;
  category: string | null;
  processed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type ExtractionRunItem = {
  id: string;
  note_id: string;
  source_asset_id: string | null;
  status: string;
  is_applied: boolean;
  extractor_name: string;
  extractor_version: string;
  provider_name: string;
  model_name: string;
  prompt_version: string;
  schema_version: string;
  input_hash: string;
  parent_run_id: string | null;
  run_kind: string;
  projection_status: string;
  created_at: string | null;
  updated_at: string | null;
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

type ApproveExtractionRunResponse = {
  note: NoteDetail;
  approved_run: ExtractionRunItem;
  replay_actions: ReplayAction[];
};

type RejectExtractionRunResponse = {
  note: NoteDetail;
  rejected_run: ExtractionRunItem;
  replay_actions: ReplayAction[];
};

type ReplayAction = {
  id: string;
  action_type: string;
  created_at: string | null;
  status_before: string | null;
  status_after: string | null;
  run_id: string;
  previous_run_id: string | null;
  projection_version_id: string | null;
  previous_projection_version_id: string | null;
  extractor_name: string;
  extractor_version: string;
  provider_name: string | null;
  model_name: string | null;
  prompt_version: string | null;
  schema_version: string | null;
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
  const [reviewingRunId, setReviewingRunId] = useState("");
  const [reprocessing, setReprocessing] = useState(false);
  const [applyNote, setApplyNote] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!params?.id) return;
    setNoteId(params.id);
    apiFetch<NoteDetail>(`/notes/${params.id}`)
      .then((data) => {
        setNote(data);
        setNotice("");
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
      if (left.status === "ready_for_review" || right.status === "ready_for_review") {
        if (left.status === right.status) {
          return 0;
        }
        return left.status === "ready_for_review" ? -1 : 1;
      }
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
      setNotice("");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "版本应用失败");
    } finally {
      setApplyingRunId("");
    }
  };

  const handleApproveRun = async (runId: string) => {
    if (!noteId) return;
    setReviewingRunId(runId);
    try {
      const result = await apiFetch<ApproveExtractionRunResponse>(`/notes/${noteId}/extraction-runs/${runId}/approve`, {
        method: "POST",
        body: JSON.stringify({ note: applyNote }),
      });
      setNote(result.note);
      setReplayActions(result.replay_actions);
      setApplyNote("");
      await loadExtractionRuns(noteId);
      setNotice("");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "审批应用失败");
    } finally {
      setReviewingRunId("");
    }
  };

  const handleRejectRun = async (runId: string) => {
    if (!noteId) return;
    setReviewingRunId(runId);
    try {
      const result = await apiFetch<RejectExtractionRunResponse>(`/notes/${noteId}/extraction-runs/${runId}/reject`, {
        method: "POST",
        body: JSON.stringify({ note: applyNote }),
      });
      setNote(result.note);
      setReplayActions(result.replay_actions);
      setApplyNote("");
      await loadExtractionRuns(noteId);
      setNotice("");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "审批拒绝失败");
    } finally {
      setReviewingRunId("");
    }
  };

  const handleReprocess = async () => {
    if (!noteId) return;
    setReprocessing(true);
    try {
      const result = await apiFetch<{ note_id: string; job_id: string }>(`/notes/${noteId}/reprocess`, {
        method: "POST",
      });
      setNote((current) => (current ? { ...current, status: "processing" } : current));
      setNotice(`已创建重新处理任务：${result.job_id}`);
      setError("");
      await loadExtractionRuns(noteId);
    } catch (err) {
      setNotice("");
      setError(err instanceof Error ? err.message : "重新处理任务创建失败");
    } finally {
      setReprocessing(false);
    }
  };

  const appliedRun = runs.find((run) => run.is_applied) ?? null;
  const latestRun = runs[0] ?? null;
  const reviewableRuns = runs.filter((run) => run.status === "ready_for_review");
  const displayedSummary = appliedRun?.summary ?? latestRun?.summary ?? null;

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-4xl">
              <div className="flex flex-wrap gap-2">
                <span className="workbench-stamp bg-canvas">{formatRunStatus(note?.status ?? "loading")}</span>
                {note?.primary_time ? (
                  <span className="workbench-stamp bg-gold">{note.primary_time.slice(0, 10)}</span>
                ) : null}
                {note?.category ? <span className="workbench-stamp bg-aqua">{note.category}</span> : null}
              </div>
              <h1 className="workbench-title mt-3">{note?.title ?? "卷宗载入中"}</h1>
              <p className="workbench-lede">{note?.summary ?? "暂无摘要"}</p>
            </div>
            {noteId ? (
              <div className="flex flex-wrap gap-2">
                <Link href={`/story/note/${noteId}`} className="tool-action bg-neon">
                  中二风视图
                </Link>
                <Link href={`/notes/${noteId}/analysis`} className="tool-action bg-aqua">
                  分析过程
                </Link>
                <Link href="/review" className="tool-action bg-canvas">
                  审核队列
                </Link>
                {note ? <AddToCollectionControl itemType="note" itemId={note.id} label={note.title} /> : null}
              </div>
            ) : null}
          </div>
        </section>
        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}
        {notice ? (
          <Panel className="p-5 text-lg font-bold text-ink" tone="success">
            {notice}
          </Panel>
        ) : null}
        <Panel className="p-6" tone="info" intensity="quiet">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="section-kicker">分析闭环</p>
              <h2 className="mt-2 text-3xl font-black">AI 分析过程与结果</h2>
              <p className="mt-3 max-w-3xl text-sm font-bold leading-relaxed text-ink/70">
                当前卷宗使用已有抽取运行、投影版本和重放日志串起导入后的分析闭环，便于确认模型版本、结构化结果和人工审核动作。
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href="/operations" className="brutal-action brutal-action-secondary text-sm">
                运维台
              </Link>
              <Link href="/review" className="brutal-action brutal-action-info text-sm">
                审核队列
              </Link>
              <button
                type="button"
                className="brutal-action brutal-action-primary text-sm disabled:cursor-not-allowed disabled:opacity-60"
                disabled={reprocessing}
                onClick={handleReprocess}
              >
                {reprocessing ? "处理中..." : "重新处理"}
              </button>
            </div>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <MetricBlock label="当前应用版本" value={note?.active_projection_id ? shortId(note.active_projection_id) : "未投影"} detail={appliedRun ? shortId(appliedRun.id) : "无已应用运行"} />
            <MetricBlock label="模型 / 版本" value={appliedRun ? appliedRun.model_name : latestRun?.model_name ?? "未知"} detail={appliedRun ? `${appliedRun.provider_name} / ${appliedRun.extractor_version}` : latestRun ? `${latestRun.provider_name} / ${latestRun.extractor_version}` : "暂无运行"} />
            <MetricBlock label="运行状态" value={reviewableRuns.length ? `${reviewableRuns.length} 待审核` : formatRunStatus(appliedRun?.status ?? latestRun?.status ?? note?.status ?? "unknown")} detail={`卷宗 ${formatRunStatus(note?.status ?? "loading")}`} />
            <MetricBlock label="结构化结果" value={displayedSummary ? `${displayedSummary.entity_count}/${displayedSummary.event_count}/${displayedSummary.relation_count}` : "0/0/0"} detail="实体 / 事件 / 关系" />
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft md:col-span-2">
              <p className="text-xs font-black uppercase tracking-[0.16em]">主要摘要</p>
              <p className="mt-3 text-base font-bold leading-relaxed">
                {note?.summary ?? displayedSummary?.title ?? "暂无摘要，等待抽取或人工补充。"}
              </p>
              <p className="mt-3 text-sm font-semibold text-ink/65">
                处理时间：{formatStamp(note?.processed_at ?? note?.updated_at ?? null)} · 来源资产：{note?.asset_id ? shortId(note.asset_id) : "无"}
              </p>
            </div>
            <div className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
              <p className="text-xs font-black uppercase tracking-[0.16em]">证据 / 结果 JSON</p>
              <p className="mt-3 text-sm font-bold leading-relaxed text-ink/70">
                展开下方运行卡片可查看结果摘要 JSON、模型元数据和差异快照；运维台可追踪任务负载与执行结果。
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <a href="#extraction-runs" className="brutal-action text-xs">
                  运行 JSON
                </a>
                <a href="#replay-audit" className="brutal-action text-xs">
                  重放日志
                </a>
              </div>
            </div>
          </div>
        </Panel>
        <Panel className="p-6" tone="quiet" intensity="quiet">
          <p className="section-kicker">规范化正文</p>
          <p className="body-copy mt-4 whitespace-pre-wrap">{note?.canonical_text}</p>
        </Panel>
        <div id="extraction-runs">
        <Panel className="p-6" tone="quiet" intensity="quiet">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-black tracking-[0.16em]">抽取运行</p>
              <h2 className="mt-2 text-3xl font-black">提取运行记录</h2>
            </div>
            <p className="text-sm font-black uppercase">{runs.length} 次</p>
          </div>
          {runs.length ? (
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {runs.map((run, index) => (
                <div key={run.id} className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs font-black uppercase tracking-[0.16em]">
                      {run.status === "ready_for_review"
                        ? "待审核草稿"
                        : run.is_applied
                          ? "当前投影"
                          : index === 0
                            ? "最新运行"
                            : `第 ${runs.length - index} 次运行`}
                    </p>
                    <p className="text-xs font-black">{run.is_applied ? "已应用" : formatRunStatus(run.status)}</p>
                  </div>
                  <p className="mt-3 text-2xl font-black">{run.summary.title || "未命名提取运行"}</p>
                  <p className="mt-2 text-sm font-semibold text-muted">
                    {run.extractor_name} / {run.extractor_version}
                  </p>
                  <div className="mt-3 grid gap-2 text-xs font-black uppercase tracking-[0.1em] sm:grid-cols-2">
                    <p className="border-2 border-ink bg-white px-2 py-1">模型 {run.provider_name} / {run.model_name}</p>
                    <p className="border-2 border-ink bg-white px-2 py-1">提示词 {run.prompt_version}</p>
                    <p className="border-2 border-ink bg-white px-2 py-1">结构 {run.schema_version}</p>
                    <p className="border-2 border-ink bg-white px-2 py-1">投影 {formatRunStatus(run.projection_status)}</p>
                  </div>
                  <p className="mt-2 text-xs font-black uppercase tracking-[0.12em]">
                    {run.created_at ? run.created_at.slice(0, 19).replace("T", " ") : "时间未知"}
                  </p>
                  <p className="mt-4 text-sm font-medium text-muted">
                    实体 {run.summary.entity_count} · 事件 {run.summary.event_count} · 关系 {run.summary.relation_count} · 相似提示{" "}
                    {run.summary.similarity_hint_count}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    {run.status === "ready_for_review" ? (
                      <>
                        <button
                          type="button"
                          className="brutal-action brutal-action-primary text-sm"
                          disabled={reviewingRunId === run.id}
                          onClick={() => handleApproveRun(run.id)}
                        >
                          {reviewingRunId === run.id ? "审批中..." : "审批应用"}
                        </button>
                        <button
                          type="button"
                          className="brutal-action text-sm"
                          disabled={reviewingRunId === run.id}
                          onClick={() => handleRejectRun(run.id)}
                        >
                          {reviewingRunId === run.id ? "处理中..." : "拒绝草稿"}
                        </button>
                      </>
                    ) : run.is_applied ? (
                      <span className="border-4 border-ink bg-mint px-3 py-2 text-xs font-black uppercase tracking-[0.14em]">
                        当前生效
                      </span>
                    ) : run.status === "rejected" ? (
                      <span className="border-4 border-ink bg-ember px-3 py-2 text-xs font-black uppercase tracking-[0.14em]">
                        已拒绝
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
                  <details className="mt-4 border-4 border-ink bg-white p-3">
                    <summary className="cursor-pointer text-xs font-black uppercase tracking-[0.16em]">
                      结果 JSON / 版本元数据
                    </summary>
                    <JsonBlock
                      title="运行快照"
                      value={{
                        id: run.id,
                        note_id: run.note_id,
                        source_asset_id: run.source_asset_id,
                        status: run.status,
                        projection_status: run.projection_status,
                        is_applied: run.is_applied,
                        run_kind: run.run_kind,
                        extractor_name: run.extractor_name,
                        extractor_version: run.extractor_version,
                        provider_name: run.provider_name,
                        model_name: run.model_name,
                        prompt_version: run.prompt_version,
                        schema_version: run.schema_version,
                        input_hash: run.input_hash,
                        parent_run_id: run.parent_run_id,
                        created_at: run.created_at,
                        updated_at: run.updated_at,
                        summary: run.summary,
                      }}
                    />
                  </details>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-base font-medium">当前还没有可展示的提取运行记录。</p>
          )}
          <div className="mt-6 border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
            <p className="text-xs font-black tracking-[0.16em]">重放备注</p>
            <label className="mt-3 block text-sm font-black uppercase tracking-[0.12em]">
              本次审批或回滚备注
            </label>
            <textarea
              value={applyNote}
              onChange={(event) => setApplyNote(event.target.value)}
              className="brutal-input mt-2 min-h-24 w-full text-sm font-medium"
              placeholder="例如：审批通过新的抽取草稿，或恢复到上一版以保留更稳定的人物识别。"
            />
          </div>
          {compare ? (
            <div className="mt-6 border-4 border-ink bg-neon p-5 shadow-brutalSoft">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-black tracking-[0.16em]">差异快照</p>
                  <h3 className="mt-2 text-2xl font-black">最近两次运行差异</h3>
                </div>
                <p className="text-sm font-black uppercase">
                  {compare.diff.changed ? "有变化" : "无变化"}
                </p>
              </div>
              <p className="mt-4 text-sm font-semibold">
                基准：{compare.base_run.extractor_name} / {compare.base_run.extractor_version}
              </p>
              <p className="text-sm font-semibold">
                {compare.candidate_run.is_applied ? "当前" : "候选"}：{compare.candidate_run.extractor_name} / {compare.candidate_run.extractor_version}
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
                  <p className="text-xs font-black tracking-[0.16em]">摘要变化</p>
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
                <div className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
                  <p className="text-xs font-black tracking-[0.16em]">图谱变化</p>
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
              <details className="mt-4 border-4 border-ink bg-canvas p-3">
                <summary className="cursor-pointer text-xs font-black uppercase tracking-[0.16em]">
                  差异 JSON
                </summary>
                <JsonBlock title="差异负载" value={compare} />
              </details>
            </div>
          ) : null}
          <div id="replay-audit" className="mt-6 border-4 border-ink bg-aqua p-5 shadow-brutalSoft">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-black tracking-[0.16em]">重放审计</p>
                <h3 className="mt-2 text-2xl font-black">重放操作日志</h3>
              </div>
              <p className="text-sm font-black uppercase">{replayActions.length} 条</p>
            </div>
            {replayActions.length ? (
              <div className="mt-4 space-y-3">
                {replayActions.map((action) => (
                  <div key={action.id} className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs font-black uppercase tracking-[0.16em]">{formatReplayActionType(action.action_type)}</p>
                      <p className="text-xs font-black uppercase">
                        {action.created_at ? action.created_at.slice(0, 19).replace("T", " ") : "时间未知"}
                      </p>
                    </div>
                    <p className="mt-3 text-sm font-semibold">
                      运行：{action.run_id} · {action.extractor_name} / {action.extractor_version}
                    </p>
                    <p className="mt-2 text-sm font-medium">
                      状态：{formatRunStatus(action.status_before ?? "无")} → {formatRunStatus(action.status_after ?? "无")} · 模型：{action.provider_name ?? "未知"} / {action.model_name ?? "未知"}
                    </p>
                    <p className="mt-2 text-sm font-medium">
                      上一版本：{action.previous_run_id ?? "无"}
                    </p>
                    <p className="mt-2 text-sm font-medium">
                      投影版本：{action.projection_version_id ?? "无"}
                    </p>
                    <p className="mt-2 text-sm font-medium">
                      备注：{action.note ?? "无"}
                    </p>
                    <details className="mt-4 border-4 border-ink bg-white p-3">
                      <summary className="cursor-pointer text-xs font-black uppercase tracking-[0.16em]">
                        操作 JSON
                      </summary>
                      <JsonBlock title="重放操作" value={action} />
                    </details>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm font-medium">当前还没有重放或回滚操作日志。</p>
            )}
          </div>
        </Panel>
        </div>
        {noteId ? (
          <div className="flex flex-wrap gap-3">
            <Link
              href={`/story/note/${noteId}`}
              className="brutal-action brutal-action-primary text-lg"
            >
              查看中二风版本
            </Link>
            <Link href={`/notes/${noteId}/analysis`} className="brutal-action brutal-action-info text-lg">
              查看分析过程
            </Link>
            <Link href="/operations" className="brutal-action brutal-action-secondary text-lg">
              跳转运维台
            </Link>
            <Link href="/review" className="brutal-action brutal-action-info text-lg">
              跳转审核队列
            </Link>
          </div>
        ) : null}
      </main>
    </AuthGate>
  );
}

function MetricBlock({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
      <p className="text-xs font-black uppercase tracking-[0.16em]">{label}</p>
      <p className="mt-3 break-words text-2xl font-black">{value}</p>
      <p className="mt-2 text-xs font-bold uppercase tracking-[0.12em] text-ink/60">{detail}</p>
    </div>
  );
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <div className="mt-3">
      <p className="text-xs font-black uppercase tracking-[0.14em]">{title}</p>
      <pre className="mt-2 max-h-72 overflow-auto border-4 border-ink bg-white p-3 text-xs font-bold leading-relaxed">
        {JSON.stringify(value ?? {}, null, 2)}
      </pre>
    </div>
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
  if (value === "apply_extraction_run") return "手动重放";
  if (value === "auto_apply_extraction_run") return "自动应用";
  if (value === "approve_extraction_run") return "审批通过";
  if (value === "reject_extraction_run") return "审批拒绝";
  return value;
}

function formatRunStatus(value: string): string {
  if (value === "loading") return "加载中";
  if (value === "unknown") return "未知";
  if (value === "processing") return "处理中";
  if (value === "completed") return "已完成";
  if (value === "ready_for_review") return "待审核";
  if (value === "rejected") return "已拒绝";
  if (value === "superseded") return "已失效";
  if (value === "pending_review") return "等待审核";
  if (value === "not_applied") return "未应用";
  if (value === "applied") return "已应用";
  return value;
}

function formatStamp(value: string | null): string {
  if (!value) return "未记录";
  return value.slice(0, 16).replace("T", " ");
}

function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}
