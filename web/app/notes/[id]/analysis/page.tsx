"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type NoteDetail = {
  id: string;
  title: string;
  summary: string | null;
  canonical_text: string | null;
  category: string | null;
  status: string;
  asset_id: string | null;
  active_projection_id: string | null;
  primary_time: string | null;
  processed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type WorkflowStep = {
  step_key: string;
  title: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  model_name: string | null;
  provider_name: string | null;
  summary: string;
  evidence: string[];
  output_refs: string[];
};

type WorkflowRun = {
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
  raw_result_json: Record<string, unknown>;
  normalized_result_json: Record<string, unknown>;
};

type WorkflowDiffCollection = {
  changed: boolean;
  added: Array<Record<string, unknown>>;
  removed: Array<Record<string, unknown>>;
  changed_items: Array<{
    key: string;
    base: Record<string, unknown>;
    candidate: Record<string, unknown>;
  }>;
  unchanged_count: number;
  base_count: number;
  candidate_count: number;
};

type WorkflowDiffSection = {
  changed: boolean;
  fields: Array<{
    field: string;
    base: unknown;
    candidate: unknown;
    changed: boolean;
  }>;
};

type WorkflowDiff = {
  changed: boolean;
  summary: WorkflowDiffSection;
  entities: WorkflowDiffCollection;
  events: WorkflowDiffCollection;
  relations: WorkflowDiffCollection;
  similarity_hints: WorkflowDiffCollection;
  style_payload: WorkflowDiffSection;
};

type WorkflowData = {
  note: NoteDetail;
  asset: {
    id: string;
    asset_type: string;
    title: string;
    status: string;
    mime_type: string | null;
    file_size: number | null;
    original_text_preview: string | null;
    created_at: string | null;
  } | null;
  active_run_id: string | null;
  latest_run_id: string | null;
  active_projection_id: string | null;
  stats: {
    job_count: number;
    derivative_count: number;
    run_count: number;
    projection_count: number;
    replay_action_count: number;
    evidence_count: number;
  };
  steps: WorkflowStep[];
  jobs: Array<{
    id: string;
    job_type: string;
    status: string;
    payload_json: Record<string, unknown>;
    result_json: Record<string, unknown>;
    error_message: string | null;
    retry_count: number;
    created_at: string | null;
    finished_at: string | null;
  }>;
  derivatives: Array<{
    id: string;
    derivative_type: string;
    version: string;
    content_preview: string;
    meta_json: Record<string, unknown>;
    created_at: string | null;
    updated_at: string | null;
  }>;
  runs: WorkflowRun[];
  projections: Array<{
    id: string;
    extraction_run_id: string;
    source_asset_id: string | null;
    previous_projection_id: string | null;
    action_type: string;
    summary_json: Record<string, unknown>;
    created_at: string | null;
    updated_at: string | null;
  }>;
  evidence_groups: Array<{
    target_type: string;
    target_id: string;
    target_label: string;
    target_subtitle: string;
    detail_href: string | null;
    curation_href: string | null;
    graph_href: string | null;
    field_names: string[];
    evidence_count: number;
    average_confidence: number | null;
    samples: Array<{
      id: string;
      target_type: string;
      target_id: string;
      field_name: string | null;
      evidence_text: string;
      evidence_offset_start: number | null;
      evidence_offset_end: number | null;
      extractor_name: string;
      extractor_version: string;
      confidence_score: number | null;
      context_before: string;
      context_after: string;
      created_at: string | null;
    }>;
  }>;
  raw_normalized_diff: WorkflowDiff;
  replay_actions: Array<{
    id: string;
    action_type: string;
    created_at: string | null;
    status_before: string | null;
    status_after: string | null;
    run_id: string;
    previous_run_id: string | null;
    projection_version_id: string | null;
    previous_projection_version_id: string | null;
    provider_name: string | null;
    model_name: string | null;
    note: string | null;
  }>;
};

export default function NoteAnalysisPage() {
  const params = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<WorkflowData | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyAction, setBusyAction] = useState("");

  useEffect(() => {
    if (!params?.id) return;
    void loadWorkflow(params.id);
  }, [params]);

  async function loadWorkflow(noteId: string) {
    return apiFetch<WorkflowData>(`/notes/${noteId}/analysis-workflow`)
      .then((data) => {
        setWorkflow(data);
        setError("");
      })
      .catch((err) => {
        setWorkflow(null);
        setError(err instanceof Error ? err.message : "分析工作流加载失败");
      });
  }

  async function runWorkflowAction(action: "rerun_extraction" | "apply_projection" | "regenerate_story", runId?: string) {
    if (!params?.id) return;
    setBusyAction(`${action}-${runId ?? "note"}`);
    try {
      if (action === "rerun_extraction") {
        const result = await apiFetch<{ note_id: string; job_id: string }>(`/notes/${params.id}/reprocess`, {
          method: "POST",
        });
        setNotice(`已创建重跑抽取任务：${result.job_id}`);
      } else if (action === "apply_projection" && runId) {
        await apiFetch(`/notes/${params.id}/extraction-runs/${runId}/apply`, {
          method: "POST",
          body: JSON.stringify({ note: "从分析工作流重新应用投影。" }),
        });
        setNotice("已重新应用投影，当前工作流已刷新。");
      } else if (action === "regenerate_story") {
        await apiFetch(`/notes/${params.id}/story/regenerate`, { method: "POST" });
        setNotice("已根据当前抽取运行重生成故事视图。");
      }
      await loadWorkflow(params.id);
      setError("");
    } catch (err) {
      setNotice("");
      setError(err instanceof Error ? err.message : "工作流操作失败");
    } finally {
      setBusyAction("");
    }
  }

  const activeRun = useMemo(
    () => workflow?.runs.find((run) => run.id === workflow.active_run_id) ?? workflow?.runs.at(-1) ?? null,
    [workflow]
  );

  return (
    <AuthGate>
      <main className="space-y-4">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-4xl">
              <div className="flex flex-wrap gap-2">
                <span className="workbench-stamp bg-canvas">{formatStatus(workflow?.note.status ?? "loading")}</span>
                <span className="workbench-stamp bg-aqua">运行 {workflow?.stats.run_count ?? 0}</span>
                <span className="workbench-stamp bg-gold">投影 {workflow?.stats.projection_count ?? 0}</span>
                <span className="workbench-stamp bg-mint">审计 {workflow?.stats.replay_action_count ?? 0}</span>
              </div>
              <h1 className="workbench-title mt-3">分析工作流</h1>
              <p className="workbench-lede">{workflow?.note.title ?? "卷宗分析过程载入中"}</p>
            </div>
            {params?.id ? (
              <div className="flex flex-wrap gap-2">
                <Link href={`/notes/${params.id}`} className="tool-action bg-canvas">
                  返回卷宗
                </Link>
                <Link href="/operations" className="tool-action bg-neon">
                  运维台
                </Link>
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
          <Panel className="p-5 text-base font-black" tone="success">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p>{notice}</p>
              <button type="button" onClick={() => setNotice("")} className="brutal-action text-xs">
                关闭
              </button>
            </div>
          </Panel>
        ) : null}

        {workflow ? (
          <>
            <Panel className="p-5" tone="info" intensity="quiet">
              <div className="grid gap-3 md:grid-cols-4">
                <Metric label="当前模型" value={activeRun?.model_name ?? "未知"} detail={activeRun?.provider_name ?? "无运行"} />
                <Metric label="应用版本" value={workflow.active_run_id ? shortId(workflow.active_run_id) : "未应用"} detail={workflow.active_projection_id ? shortId(workflow.active_projection_id) : "无投影"} />
                <Metric label="结构结果" value={activeRun ? `${activeRun.summary.entity_count}/${activeRun.summary.event_count}/${activeRun.summary.relation_count}` : "0/0/0"} detail="实体 / 事件 / 关系" />
                <Metric label="证据记录" value={String(workflow.stats.evidence_count)} detail={`衍生物 ${workflow.stats.derivative_count}`} />
              </div>
            </Panel>

            <Panel className="p-5" tone="quiet" intensity="quiet">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="section-kicker">流水线</p>
                  <h2 className="mt-2 text-2xl font-black">从原始材料到知识图谱</h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void runWorkflowAction("rerun_extraction")}
                    disabled={Boolean(busyAction)}
                    className="brutal-action brutal-action-primary text-xs disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {busyAction === "rerun_extraction-note" ? "创建中..." : "重跑抽取"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void runWorkflowAction("regenerate_story")}
                    disabled={Boolean(busyAction) || !activeRun}
                    className="brutal-action brutal-action-info text-xs disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {busyAction === "regenerate_story-note" ? "生成中..." : "重生成故事"}
                  </button>
                  <span className="brutal-chip">步骤 {workflow.steps.length}</span>
                </div>
              </div>
              <div className="mt-5 space-y-3">
                {workflow.steps.map((step, index) => (
                  <article key={step.step_key} className="dense-record md:grid-cols-[8rem_1fr]">
                    <div className={`dense-record-side ${toneForStatus(step.status)}`}>
                      <p className="text-xs font-black tracking-[0.12em]">步骤 {index + 1}</p>
                      <p className="mt-3 text-lg font-black leading-tight">{formatStatus(step.status)}</p>
                    </div>
                    <div className="dense-record-body">
                      <div className="min-w-0">
                        <p className="dense-record-title">{step.title}</p>
                        <p className="dense-record-summary">{step.summary}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {step.provider_name ? <span className="brutal-chip">{step.provider_name}</span> : null}
                          {step.model_name ? <span className="brutal-chip">{step.model_name}</span> : null}
                          {step.duration_ms !== null ? <span className="brutal-chip">{step.duration_ms}ms</span> : null}
                          {step.started_at ? <span className="brutal-chip">开始 {formatStamp(step.started_at)}</span> : null}
                          {step.finished_at ? <span className="brutal-chip">完成 {formatStamp(step.finished_at)}</span> : null}
                          {step.output_refs.length ? <span className="brutal-chip">输出 {step.output_refs.length}</span> : null}
                        </div>
                        <StepActions
                          stepKey={step.step_key}
                          activeRun={activeRun}
                          busyAction={busyAction}
                          onRunAction={runWorkflowAction}
                        />
                        {step.evidence.length ? (
                          <div className="mt-3 space-y-2">
                            {step.evidence.map((item) => (
                              <p key={`${step.step_key}-${item}`} className="border-2 border-ink bg-white px-3 py-2 text-sm font-bold leading-relaxed">
                                {item}
                              </p>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </Panel>

            <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
              <Panel className="p-5" tone="quiet" intensity="quiet">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="section-kicker">抽取运行</p>
                    <h2 className="mt-2 text-2xl font-black">AI 输出与规范化结果</h2>
                  </div>
                  <span className="brutal-chip">{workflow.runs.length} 次</span>
                </div>
                <div className="mt-5 space-y-4">
                  {workflow.runs.map((run) => (
                    <details key={run.id} className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft" open={run.id === workflow.active_run_id}>
                      <summary className="cursor-pointer list-none">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-black tracking-[0.14em]">
                              {run.is_applied ? "当前应用" : formatStatus(run.status)}
                            </p>
                            <p className="mt-2 text-xl font-black">{run.summary.title || run.id}</p>
                            <p className="mt-2 text-sm font-bold text-muted">
                              {run.provider_name} / {run.model_name} / {run.prompt_version}
                            </p>
                          </div>
                          <span className="brutal-chip">{formatStamp(run.created_at)}</span>
                        </div>
                      </summary>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => void runWorkflowAction("apply_projection", run.id)}
                          disabled={Boolean(busyAction) || run.is_applied || run.status === "ready_for_review" || run.status === "rejected"}
                          className="brutal-action brutal-action-primary text-xs disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {busyAction === `apply_projection-${run.id}` ? "应用中..." : run.is_applied ? "当前已应用" : "重新应用投影"}
                        </button>
                        <button
                          type="button"
                          onClick={() => void runWorkflowAction("regenerate_story")}
                          disabled={Boolean(busyAction) || !run.is_applied}
                          className="brutal-action brutal-action-info text-xs disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {busyAction === "regenerate_story-note" ? "生成中..." : "用当前版本重生成故事"}
                        </button>
                      </div>
                      <div className="mt-4 grid gap-4 lg:grid-cols-2">
                        <JsonBlock title="模型原始输出" value={run.raw_result_json} />
                        <JsonBlock title="系统规范化结果" value={run.normalized_result_json} />
                      </div>
                    </details>
                  ))}
                  {workflow.runs.length === 0 ? <p className="empty-state">还没有抽取运行。</p> : null}
                </div>
              </Panel>

              <Panel className="p-5" tone="story" intensity="quiet">
                <p className="section-kicker">来源与审计</p>
                <h2 className="mt-2 text-2xl font-black">材料、任务、投影</h2>
                <div className="mt-5 space-y-4">
                  <InfoCard title="原始材料" rows={[
                    ["标题", workflow.asset?.title ?? "无"],
                    ["类型", workflow.asset?.asset_type ?? "无"],
                    ["状态", formatStatus(workflow.asset?.status ?? "unknown")],
                    ["预览", workflow.asset?.original_text_preview ?? "无原文预览"],
                  ]} />
                  <InfoCard title="衍生内容" rows={workflow.derivatives.map((item) => [item.derivative_type, item.content_preview || item.version])} />
                  <InfoCard title="任务记录" rows={workflow.jobs.map((job) => [job.job_type, `${formatStatus(job.status)} / ${formatStamp(job.finished_at)}`])} />
                  <InfoCard title="投影版本" rows={workflow.projections.map((projection) => [shortId(projection.id), projection.action_type])} />
                  <AuditTrail actions={workflow.replay_actions} />
                </div>
              </Panel>
            </section>

            <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
              <DiffSummaryPanel diff={workflow.raw_normalized_diff} />
              <EvidenceGroupsPanel groups={workflow.evidence_groups} />
            </section>
          </>
        ) : !error ? (
          <Panel className="p-6" tone="quiet">
            <p className="text-lg font-black">分析工作流载入中</p>
          </Panel>
        ) : null}
      </main>
    </AuthGate>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
      <p className="text-xs font-black tracking-[0.14em]">{label}</p>
      <p className="mt-3 break-words text-xl font-black leading-tight">{value}</p>
      <p className="mt-2 text-xs font-bold text-muted">{detail}</p>
    </div>
  );
}

function DiffSummaryPanel({ diff }: { diff: WorkflowDiff }) {
  const collectionRows = [
    ["人物", diff.entities],
    ["事件", diff.events],
    ["关系", diff.relations],
    ["相似线索", diff.similarity_hints],
  ] as const;
  const changedSummaryFields = diff.summary.fields.filter((item) => item.changed);
  const changedStyleFields = diff.style_payload.fields.filter((item) => item.changed);

  return (
    <Panel className="p-5" tone="quiet" intensity="quiet">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="section-kicker">规范化差异</p>
          <h2 className="mt-2 text-2xl font-black">原始输出 vs 系统规范化</h2>
          <p className="mt-2 text-sm font-bold text-muted">
            {diff.changed ? "系统在入库前对模型输出做过结构调整。" : "当前应用运行的原始输出与规范化结果一致。"}
          </p>
        </div>
        <span className={`workbench-stamp ${diff.changed ? "bg-gold" : "bg-mint"}`}>
          {diff.changed ? "有差异" : "无差异"}
        </span>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {collectionRows.map(([label, section]) => (
          <div key={label} className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
            <p className="text-sm font-black">{label}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="brutal-chip">新增 {section.added.length}</span>
              <span className="brutal-chip">移除 {section.removed.length}</span>
              <span className="brutal-chip">变更 {section.changed_items.length}</span>
              <span className="brutal-chip">保留 {section.unchanged_count}</span>
            </div>
            <p className="mt-3 text-xs font-bold text-muted">
              原始 {section.base_count} / 规范化 {section.candidate_count}
            </p>
          </div>
        ))}
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <DiffFieldCard title="摘要字段变化" fields={changedSummaryFields} />
        <DiffFieldCard title="故事视图字段变化" fields={changedStyleFields} />
      </div>
      <div className="mt-4 space-y-3">
        <ObjectDiffGroup title="人物对象变化" section={diff.entities} />
        <ObjectDiffGroup title="事件对象变化" section={diff.events} />
        <ObjectDiffGroup title="关系对象变化" section={diff.relations} />
      </div>
    </Panel>
  );
}

function DiffFieldCard({ title, fields }: { title: string; fields: WorkflowDiffSection["fields"] }) {
  return (
    <div className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-black">{title}</p>
        <span className="brutal-chip">{fields.length} 项</span>
      </div>
      <div className="mt-3 space-y-2">
        {fields.length ? fields.slice(0, 4).map((field) => (
          <div key={field.field} className="border-2 border-ink bg-white px-3 py-2">
            <p className="text-xs font-black text-muted">{field.field}</p>
            <p className="mt-1 break-words text-sm font-bold leading-relaxed">
              {stringifyShort(field.base)} {"->"} {stringifyShort(field.candidate)}
            </p>
          </div>
        )) : <p className="text-sm font-bold text-muted">无字段变化</p>}
      </div>
    </div>
  );
}

function ObjectDiffGroup({ title, section }: { title: string; section: WorkflowDiffCollection }) {
  const hasChanges = section.added.length || section.removed.length || section.changed_items.length;
  return (
    <details className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
      <summary className="cursor-pointer list-none">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm font-black">{title}</p>
          <span className="brutal-chip">
            +{section.added.length} / -{section.removed.length} / 改 {section.changed_items.length}
          </span>
        </div>
      </summary>
      <div className="mt-3 space-y-3">
        {hasChanges ? (
          <>
            <DiffObjectList label="新增" items={section.added} tone="bg-mint" />
            <DiffObjectList label="移除" items={section.removed} tone="bg-ember" />
            {section.changed_items.slice(0, 6).map((item) => (
              <div key={item.key} className="border-2 border-ink bg-white p-3">
                <p className="text-xs font-black text-muted">变更 / {item.key}</p>
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  <pre className="max-h-56 overflow-auto border-2 border-ink bg-canvas p-2 text-xs font-bold leading-relaxed">
                    {JSON.stringify(item.base, null, 2)}
                  </pre>
                  <pre className="max-h-56 overflow-auto border-2 border-ink bg-mint/40 p-2 text-xs font-bold leading-relaxed">
                    {JSON.stringify(item.candidate, null, 2)}
                  </pre>
                </div>
              </div>
            ))}
          </>
        ) : <p className="text-sm font-bold text-muted">这个对象集合没有变化。</p>}
      </div>
    </details>
  );
}

function DiffObjectList({ label, items, tone }: { label: string; items: Array<Record<string, unknown>>; tone: string }) {
  if (!items.length) return null;
  return (
    <div className="border-2 border-ink bg-white p-3">
      <p className={`inline-block border-2 border-ink px-2 py-1 text-xs font-black ${tone}`}>{label}</p>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        {items.slice(0, 6).map((item, index) => (
          <pre key={`${label}-${index}`} className="max-h-52 overflow-auto border-2 border-ink bg-canvas p-2 text-xs font-bold leading-relaxed">
            {JSON.stringify(item, null, 2)}
          </pre>
        ))}
      </div>
    </div>
  );
}

function EvidenceGroupsPanel({ groups }: { groups: WorkflowData["evidence_groups"] }) {
  return (
    <Panel className="p-5" tone="info" intensity="quiet">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="section-kicker">证据链</p>
          <h2 className="mt-2 text-2xl font-black">实体、事件、关系的来源片段</h2>
          <p className="mt-2 text-sm font-bold text-muted">优先展示证据最多的对象，帮助判断 AI 为什么这样抽取。</p>
        </div>
        <span className="workbench-stamp bg-aqua">{groups.length} 组</span>
      </div>
      <div className="mt-5 space-y-3">
        {groups.length ? groups.slice(0, 8).map((group) => (
          <article key={`${group.target_type}-${group.target_id}`} className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-black tracking-[0.14em]">{formatTargetType(group.target_type)}</p>
                <p className="mt-2 break-words text-lg font-black">{group.target_label}</p>
                <p className="mt-1 break-words text-xs font-bold text-muted">{group.target_subtitle}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="brutal-chip">证据 {group.evidence_count}</span>
                <span className="brutal-chip">置信 {formatConfidence(group.average_confidence)}</span>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {group.field_names.map((field) => <span key={field} className="brutal-chip">{field}</span>)}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {group.detail_href ? <Link href={group.detail_href} className="brutal-action text-xs">打开详情</Link> : null}
              {group.curation_href ? <Link href={group.curation_href} className="brutal-action brutal-action-primary text-xs">进入校正</Link> : null}
              {group.graph_href ? <Link href={group.graph_href} className="brutal-action brutal-action-info text-xs">图谱定位</Link> : null}
            </div>
            <div className="mt-3 space-y-2">
              {group.samples.map((sample) => (
                <div key={sample.id} className="border-2 border-ink bg-white px-3 py-2">
                  <p className="text-sm font-bold leading-relaxed">
                    {sample.context_before ? <span className="text-muted">{sample.context_before}</span> : null}
                    <mark className="border-2 border-ink bg-gold px-1 font-black">{sample.evidence_text}</mark>
                    {sample.context_after ? <span className="text-muted">{sample.context_after}</span> : null}
                  </p>
                  <p className="mt-2 text-xs font-black text-muted">
                    {sample.extractor_name} / {sample.extractor_version} / {sample.field_name ?? "unknown"} / {formatConfidence(sample.confidence_score)}
                  </p>
                  {sample.evidence_offset_start !== null ? (
                    <p className="mt-1 text-xs font-bold text-muted">
                      位置 {sample.evidence_offset_start} - {sample.evidence_offset_end ?? sample.evidence_offset_start}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          </article>
        )) : <p className="empty-state">暂无抽取证据。后续投影或重新抽取后会在这里显示来源片段。</p>}
      </div>
    </Panel>
  );
}

function StepActions({
  stepKey,
  activeRun,
  busyAction,
  onRunAction,
}: {
  stepKey: string;
  activeRun: WorkflowRun | null;
  busyAction: string;
  onRunAction: (action: "rerun_extraction" | "apply_projection" | "regenerate_story", runId?: string) => Promise<void>;
}) {
  if (stepKey === "knowledge_extraction") {
    return (
      <button
        type="button"
        onClick={() => void onRunAction("rerun_extraction")}
        disabled={Boolean(busyAction)}
        className="brutal-action brutal-action-primary mt-3 text-xs disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busyAction === "rerun_extraction-note" ? "创建重跑任务中..." : "重跑抽取"}
      </button>
    );
  }
  if (stepKey === "projection" && activeRun) {
    const cannotApply = ["ready_for_review", "rejected"].includes(activeRun.status);
    return (
      <button
        type="button"
        onClick={() => void onRunAction("apply_projection", activeRun.id)}
        disabled={Boolean(busyAction) || cannotApply}
        className="brutal-action brutal-action-primary mt-3 text-xs disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busyAction === `apply_projection-${activeRun.id}` ? "重新应用中..." : "重新应用当前投影"}
      </button>
    );
  }
  if (stepKey === "story_rendering") {
    return (
      <button
        type="button"
        onClick={() => void onRunAction("regenerate_story")}
        disabled={Boolean(busyAction) || !activeRun}
        className="brutal-action brutal-action-info mt-3 text-xs disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busyAction === "regenerate_story-note" ? "重生成中..." : "重生成故事视图"}
      </button>
    );
  }
  return null;
}

function InfoCard({ title, rows }: { title: string; rows: Array<[string, string]> }) {
  return (
    <div className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
      <p className="text-sm font-black">{title}</p>
      <div className="mt-3 space-y-2">
        {rows.length ? rows.map(([label, value]) => (
          <div key={`${title}-${label}-${value}`} className="border-2 border-ink bg-white px-3 py-2">
            <p className="text-xs font-black text-muted">{label}</p>
            <p className="mt-1 break-words text-sm font-bold leading-relaxed">{value}</p>
          </div>
        )) : <p className="text-sm font-bold text-muted">暂无记录</p>}
      </div>
    </div>
  );
}

function AuditTrail({ actions }: { actions: WorkflowData["replay_actions"] }) {
  return (
    <div className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-black">操作历史</p>
        <span className="brutal-chip">{actions.length} 条</span>
      </div>
      <div className="mt-3 space-y-3">
        {actions.length ? actions.map((action) => (
          <article key={action.id} className="border-2 border-ink bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-black">{formatReplayAction(action.action_type)}</p>
                <p className="mt-1 text-xs font-bold text-muted">
                  {formatStatus(action.status_before ?? "none")} {"->"} {formatStatus(action.status_after ?? "none")}
                </p>
              </div>
              <span className="brutal-chip">{formatStamp(action.created_at)}</span>
            </div>
            {action.note ? <p className="mt-3 text-sm font-bold leading-relaxed">{action.note}</p> : null}
            <div className="mt-3 flex flex-wrap gap-2">
              {action.run_id ? <span className="brutal-chip">运行 {shortId(action.run_id)}</span> : null}
              {action.projection_version_id ? <span className="brutal-chip">投影 {shortId(action.projection_version_id)}</span> : null}
              {action.model_name ? <span className="brutal-chip">{action.model_name}</span> : null}
            </div>
          </article>
        )) : <p className="text-sm font-bold text-muted">暂无操作历史</p>}
      </div>
    </div>
  );
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <div>
      <p className="text-xs font-black tracking-[0.14em]">{title}</p>
      <pre className="mt-2 max-h-96 overflow-auto border-4 border-ink bg-white p-3 text-xs font-bold leading-relaxed">
        {JSON.stringify(value ?? {}, null, 2)}
      </pre>
    </div>
  );
}

function toneForStatus(status: string): string {
  if (["completed", "applied", "ready", "reviewed", "uploaded"].includes(status)) return "bg-mint";
  if (["running", "processing", "pending"].includes(status)) return "bg-gold";
  if (["failed", "missing", "rejected"].includes(status)) return "bg-ember";
  return "bg-canvas";
}

function formatStatus(value: string): string {
  const map: Record<string, string> = {
    loading: "加载中",
    unknown: "未知",
    none: "无",
    ready: "已就绪",
    uploaded: "已上传",
    processing: "处理中",
    pending: "等待中",
    running: "运行中",
    completed: "已完成",
    applied: "已应用",
    superseded: "已失效",
    ready_for_review: "待审核",
    pending_review: "等待审核",
    not_applied: "未应用",
    not_reviewed: "未审核",
    reviewed: "已审核",
    rejected: "已拒绝",
    failed: "失败",
    missing: "缺失",
  };
  return map[value] ?? value;
}

function formatReplayAction(value: string): string {
  if (value === "auto_apply_extraction_run") return "自动应用";
  if (value === "apply_extraction_run") return "手动重放";
  if (value === "approve_extraction_run") return "审批通过";
  if (value === "reject_extraction_run") return "审批拒绝";
  if (value === "regenerate_story_view") return "重生成故事视图";
  return value;
}

function formatTargetType(value: string): string {
  if (value === "entity") return "人物/实体";
  if (value === "event") return "事件";
  if (value === "relation") return "关系";
  return value;
}

function formatConfidence(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "未知";
  return `${Math.round(value * 100)}%`;
}

function stringifyShort(value: unknown): string {
  if (value === null || value === undefined || value === "") return "空";
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > 120 ? `${text.slice(0, 120)}...` : text;
}

function formatStamp(value: string | null): string {
  return value ? value.slice(0, 16).replace("T", " ") : "未记录";
}

function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}
