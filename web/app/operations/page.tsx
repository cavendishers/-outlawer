"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type ListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

type JobItem = {
  id: string;
  job_type: string;
  status: string;
  target_type: string;
  target_id: string;
  error_message: string | null;
  retry_count: number;
  created_at: string | null;
  finished_at: string | null;
};

type JobDetail = JobItem & {
  result_json?: Record<string, unknown>;
  payload_json?: Record<string, unknown>;
};

type AssetItem = {
  id: string;
  asset_type: string;
  title: string;
  status: string;
  mime_type: string | null;
  file_size: number | null;
  raw_url: string | null;
  created_at: string | null;
};

type AssetDerivative = {
  id: string;
  derivative_type: string;
  version: string;
  content_preview: string;
  meta_json: Record<string, unknown>;
  created_at: string | null;
};

type AssetNoteRef = {
  id: string;
  title: string;
  status: string;
  created_at: string | null;
  processed_at: string | null;
};

type AssetDetail = AssetItem & {
  original_text: string | null;
  checksum: string | null;
  object_key: string | null;
  derivatives: AssetDerivative[];
  notes: AssetNoteRef[];
};

type NoteItem = {
  id: string;
  title: string;
  status: string;
  asset_id: string | null;
  processed_at: string | null;
  created_at: string | null;
};

type ExtractionRunSummary = {
  title: string | null;
  entity_count: number;
  event_count: number;
  relation_count: number;
  timeline_count: number;
  similarity_hint_count: number;
};

type ExtractionRunItem = {
  id: string;
  status: string;
  extractor_name: string;
  extractor_version: string;
  is_applied: boolean;
  created_at: string | null;
  summary: ExtractionRunSummary;
};

type StatusCount = {
  status: string;
  count: number;
};

type OperationsActionItem = {
  id: string;
  target_type: string;
  target_id: string;
  action_type: string;
  status_before: string | null;
  status_after: string | null;
  created_at: string | null;
  href: string;
  href_label: string;
  summary: string;
};

type OperationsOverview = {
  jobs: {
    total: number;
    pending: number;
    running: number;
    failed: number;
    completed: number;
    by_status: StatusCount[];
    recent_failed_jobs: JobItem[];
  };
  assets: {
    total: number;
    uploaded: number;
    by_type: StatusCount[];
  };
  review: {
    pending_total: number;
    pending_entities: number;
    pending_events: number;
    recent_candidates: Array<{
      id: string;
      object_type: string;
      status: string;
      score: number;
      source_label: string | null;
      candidate_label: string | null;
      href: string;
    }>;
  };
  extraction: {
    ready_for_review: number;
    processing_notes: number;
    recent_reviewable_runs: Array<{
      run_id: string;
      note_id: string;
      note_title: string;
      status: string;
      extractor_name: string;
      extractor_version: string;
      created_at: string | null;
      href: string;
    }>;
  };
  activity: {
    recent_actions: OperationsActionItem[];
  };
  graph_quality: {
    viewpoint_count: number;
    low_confidence_relation_count: number;
    orphan_entity_count: number;
    orphan_event_count: number;
    recent_graph_actions: OperationsActionItem[];
  };
};

export default function OperationsPage() {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [overview, setOverview] = useState<OperationsOverview | null>(null);
  const [jobTotal, setJobTotal] = useState(0);
  const [assetTotal, setAssetTotal] = useState(0);
  const [noteTotal, setNoteTotal] = useState(0);
  const [selectedJob, setSelectedJob] = useState<JobDetail | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<AssetDetail | null>(null);
  const [selectedNoteId, setSelectedNoteId] = useState("");
  const [runs, setRuns] = useState<ExtractionRunItem[]>([]);
  const [retryingJobId, setRetryingJobId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadOverview();
  }, []);

  async function loadOverview() {
    setLoading(true);
    try {
      const [jobData, assetData, noteData, operationsData] = await Promise.all([
        apiFetch<ListResponse<JobItem>>("/jobs?page_size=16"),
        apiFetch<ListResponse<AssetItem>>("/assets?page_size=12"),
        apiFetch<ListResponse<NoteItem>>("/notes?page_size=12"),
        apiFetch<OperationsOverview>("/operations/overview"),
      ]);
      setJobs(jobData.items);
      setAssets(assetData.items);
      setNotes(noteData.items);
      setOverview(operationsData);
      setJobTotal(jobData.total);
      setAssetTotal(assetData.total);
      setNoteTotal(noteData.total);
      setError("");
      if (jobData.items[0]) {
        await loadJob(jobData.items[0].id);
      }
      if (assetData.items[0]) {
        await loadAsset(assetData.items[0].id);
      }
      if (noteData.items[0]) {
        await loadRuns(noteData.items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "运维数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadJob(jobId: string) {
    const data = await apiFetch<JobDetail>(`/jobs/${jobId}`);
    setSelectedJob(data);
  }

  async function loadAsset(assetId: string) {
    const data = await apiFetch<AssetDetail>(`/assets/${assetId}`);
    setSelectedAsset(data);
  }

  async function loadRuns(noteId: string) {
    setSelectedNoteId(noteId);
    const data = await apiFetch<ListResponse<ExtractionRunItem>>(`/notes/${noteId}/extraction-runs?page_size=10`);
    setRuns(data.items);
  }

  async function retryJob(jobId: string) {
    setRetryingJobId(jobId);
    try {
      await apiFetch<{ job_id: string; status: string }>(`/jobs/${jobId}/retry`, { method: "POST" });
      await loadOverview();
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务重试失败");
    } finally {
      setRetryingJobId("");
    }
  }

  const failedJobs = overview?.jobs.failed ?? jobs.filter((job) => job.status === "failed").length;
  const activeJobs = overview ? overview.jobs.pending + overview.jobs.running : jobs.filter((job) => job.status === "pending" || job.status === "running").length;
  const pendingRuns = overview?.extraction.ready_for_review ?? runs.filter((run) => run.status === "ready_for_review").length;
  const selectedNote = notes.find((note) => note.id === selectedNoteId);

  return (
    <AuthGate>
      <main className="space-y-4">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <h1 className="workbench-title">运维后台</h1>
              <p className="workbench-lede">
                集中检查异步任务、失败重试、原始资产、派生内容和抽取运行，快速定位处理链路里的断点。
              </p>
            </div>
            <div className="flex flex-wrap justify-start gap-2 md:justify-end">
              <span className={`workbench-stamp ${failedJobs ? "bg-ember" : "bg-mint"}`}>失败任务 {failedJobs}</span>
              <span className="workbench-stamp bg-gold">活跃任务 {activeJobs}</span>
              <span className="workbench-stamp bg-aqua">待审抽取 {pendingRuns}</span>
              <span className="workbench-stamp bg-canvas">知识卷宗 {noteTotal}</span>
              <button type="button" className="tool-action bg-canvas" onClick={loadOverview}>
                刷新
              </button>
              <Link href="/review" className="tool-action bg-canvas">
                审核队列
              </Link>
            </div>
          </div>
        </section>

        {error ? (
          <Panel className="p-4" tone="danger">
            <p className="text-base font-black">{error}</p>
          </Panel>
        ) : null}

        <section className="grid gap-3 md:grid-cols-4">
          <MetricCard label="任务总数" value={overview?.jobs.total ?? jobTotal} description={`活跃 ${activeJobs} / 失败 ${failedJobs}`} tone="info" />
          <MetricCard label="原始资产" value={overview?.assets.total ?? assetTotal} description="文本、图片、音频、视频原始输入" tone="default" />
          <MetricCard label="知识卷宗" value={noteTotal} description="已经创建或等待处理的卷宗" tone="story" />
          <MetricCard label="待审草稿" value={pendingRuns} description="全局待审抽取草稿" tone={pendingRuns ? "time" : "success"} />
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel className="p-5" tone="time">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="section-kicker">图谱质量</p>
              <Link href="/graph" className="tool-action bg-canvas">
                打开图谱工作台
              </Link>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <BacklogSignalCard
                label="保存视角"
                value={overview?.graph_quality.viewpoint_count ?? 0}
                description="可复用的图谱治理入口"
                tone="info"
              />
              <BacklogSignalCard
                label="低置信关系"
                value={overview?.graph_quality.low_confidence_relation_count ?? 0}
                description="优先人工确认的关系边"
                tone={overview?.graph_quality.low_confidence_relation_count ? "time" : "success"}
              />
              <BacklogSignalCard
                label="孤立人物"
                value={overview?.graph_quality.orphan_entity_count ?? 0}
                description="未连接事件或关系的人物"
                tone={overview?.graph_quality.orphan_entity_count ? "signal" : "success"}
              />
              <BacklogSignalCard
                label="孤立事件"
                value={overview?.graph_quality.orphan_event_count ?? 0}
                description="未连接参与者或关系的事件"
                tone={overview?.graph_quality.orphan_event_count ? "signal" : "success"}
              />
            </div>
          </Panel>

          <Panel className="p-5" tone="paper">
            <p className="section-kicker">图谱治理操作</p>
            <div className="mt-5 space-y-3">
              {overview?.graph_quality.recent_graph_actions.length ? (
                overview.graph_quality.recent_graph_actions.map((item) => (
                  <Link key={item.id} href={item.href} className="surface-inset block border-4 border-ink p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs font-black uppercase tracking-[0.14em]">
                        {item.target_type} / {item.action_type}
                      </p>
                      <p className="text-xs font-black uppercase tracking-[0.12em]">{formatStamp(item.created_at)}</p>
                    </div>
                    <p className="mt-3 text-sm font-bold leading-relaxed">{item.summary}</p>
                    <span className="brutal-chip mt-4 inline-flex">{item.href_label}</span>
                  </Link>
                ))
              ) : (
                <EmptyState text="当前还没有图谱治理操作。" />
              )}
            </div>
          </Panel>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <Panel className="p-5" tone="danger">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="section-kicker">积压雷达</p>
              <Link href="/review" className="tool-action bg-canvas">
                打开审核队列
              </Link>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <BacklogSignalCard
                label="失败任务"
                value={failedJobs}
                description="优先检查失败 job 和错误信息"
                tone={failedJobs ? "danger" : "success"}
              />
              <BacklogSignalCard
                label="待审抽取"
                value={overview?.extraction.ready_for_review ?? 0}
                description="需要人工审批后才能成为新投影"
                tone={overview?.extraction.ready_for_review ? "time" : "success"}
              />
              <BacklogSignalCard
                label="待合并候选"
                value={overview?.review.pending_total ?? 0}
                description={`人物 ${overview?.review.pending_entities ?? 0} / 事件 ${overview?.review.pending_events ?? 0}`}
                tone={overview?.review.pending_total ? "signal" : "success"}
              />
              <BacklogSignalCard
                label="处理中卷宗"
                value={overview?.extraction.processing_notes ?? 0}
                description="仍在等待异步解析完成"
                tone={overview?.extraction.processing_notes ? "info" : "success"}
              />
            </div>
            <div className="mt-5 space-y-3">
              {overview?.extraction.recent_reviewable_runs.length ? (
                overview.extraction.recent_reviewable_runs.map((run) => (
                  <Link key={run.run_id} href={run.href} className="surface-inset block border-4 border-ink p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs font-black uppercase tracking-[0.14em]">
                        {run.extractor_name} / {run.extractor_version}
                      </p>
                      <StatusPill status={run.status} />
                    </div>
                    <p className="mt-3 text-lg font-black">{run.note_title}</p>
                    <p className="mt-2 text-sm font-bold">{formatStamp(run.created_at)}</p>
                  </Link>
                ))
              ) : (
                <EmptyState text="当前没有待审抽取草稿。" />
              )}
            </div>
          </Panel>

          <Panel className="p-5" tone="paper">
            <p className="section-kicker">最近操作动作</p>
            <div className="mt-5 space-y-3">
              {overview?.activity.recent_actions.length ? (
                overview.activity.recent_actions.map((item) => (
                  <div key={item.id} className="surface-inset border-4 border-ink p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs font-black uppercase tracking-[0.14em]">
                        {item.target_type} / {item.action_type}
                      </p>
                      <p className="text-xs font-black uppercase tracking-[0.12em]">{formatStamp(item.created_at)}</p>
                    </div>
                    <p className="mt-3 text-sm font-bold leading-relaxed">{item.summary}</p>
                    <Link href={item.href} className="brutal-action brutal-action-secondary mt-4 text-sm">
                      {item.href_label}
                    </Link>
                  </div>
                ))
              ) : (
                <EmptyState text="当前还没有可追踪的审核或校对动作。" />
              )}
            </div>
          </Panel>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <Panel className="p-5" tone="signal">
            <p className="section-kicker">待合并候选</p>
            <div className="mt-5 space-y-3">
              {overview?.review.recent_candidates.length ? (
                overview.review.recent_candidates.map((candidate) => (
                  <Link key={candidate.id} href={candidate.href} className="surface-inset block border-4 border-ink p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs font-black uppercase tracking-[0.14em]">
                        {candidate.object_type} / {candidate.status}
                      </p>
                      <span className="brutal-chip">相似度 {candidate.score.toFixed(2)}</span>
                    </div>
                    <p className="mt-3 text-base font-black">
                      {candidate.source_label ?? "未知源对象"} ↔ {candidate.candidate_label ?? "未知候选对象"}
                    </p>
                  </Link>
                ))
              ) : (
                <EmptyState text="当前没有待处理的合并候选。" />
              )}
            </div>
          </Panel>

          <Panel className="p-5" tone="default">
            <p className="section-kicker">资产类型分布</p>
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {(overview?.assets.by_type ?? []).map((item) => (
                <div key={item.status} className="surface-inset border-4 border-ink p-4">
                  <p className="text-xs font-black uppercase tracking-[0.14em]">{item.status}</p>
                  <p className="mt-3 text-3xl font-black">{item.count}</p>
                </div>
              ))}
              {!overview?.assets.by_type.length ? <EmptyState text="当前还没有资产类型分布数据。" /> : null}
            </div>
          </Panel>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <Panel className="p-5" tone="info">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="section-kicker">任务队列</p>
              <span className="brutal-chip">{loading ? "加载中" : `显示 ${jobs.length}`}</span>
            </div>
            <div className="mt-5 space-y-3">
              {jobs.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => loadJob(job.id)}
                  className={`block w-full border-4 border-ink p-4 text-left shadow-brutal transition-transform hover:-translate-y-1 ${
                    selectedJob?.id === job.id ? "bg-neon" : "bg-white/80"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs font-black uppercase tracking-[0.14em]">{job.job_type}</p>
                    <StatusPill status={job.status} />
                  </div>
                  <p className="mt-3 break-all text-sm font-bold">{job.target_type}: {job.target_id}</p>
                  <p className="mt-2 text-xs font-black uppercase tracking-[0.12em]">
                    重试 {job.retry_count} / {formatStamp(job.created_at)}
                  </p>
                  {job.error_message ? (
                    <p className="mt-2 max-h-12 overflow-hidden text-sm font-bold text-red-950">{job.error_message}</p>
                  ) : null}
                </button>
              ))}
              {!jobs.length ? <EmptyState text="当前没有任务记录。" /> : null}
            </div>
          </Panel>

          <Panel className="p-5" tone={selectedJob?.status === "failed" ? "danger" : "default"}>
            <p className="section-kicker">任务详情</p>
            {selectedJob ? (
              <div className="mt-5 space-y-4">
                <div className="surface-inset border-4 border-ink p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="break-all text-xl font-black">{selectedJob.id}</p>
                    <StatusPill status={selectedJob.status} />
                  </div>
                  <p className="mt-3 text-sm font-bold leading-relaxed">
                    {selectedJob.job_type} / {selectedJob.target_type} / {formatStamp(selectedJob.created_at)}
                  </p>
                  {selectedJob.error_message ? (
                    <p className="mt-3 border-4 border-ink bg-[var(--surface-danger-soft)] p-3 text-sm font-bold">
                      {selectedJob.error_message}
                    </p>
                  ) : null}
                  {selectedJob.status === "failed" ? (
                    <button
                      type="button"
                      disabled={retryingJobId === selectedJob.id}
                      onClick={() => retryJob(selectedJob.id)}
                      className="brutal-action brutal-action-primary mt-4"
                    >
                      {retryingJobId === selectedJob.id ? "重试中..." : "重试任务"}
                    </button>
                  ) : null}
                </div>
                <JsonBlock title="请求负载" value={selectedJob.payload_json} />
                <JsonBlock title="执行结果" value={selectedJob.result_json} />
              </div>
            ) : (
              <EmptyState text="从左侧选择一个任务查看详情。" />
            )}
          </Panel>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <Panel className="p-5" tone="default">
            <p className="section-kicker">原始资产</p>
            <div className="mt-5 space-y-3">
              {assets.map((asset) => (
                <button
                  key={asset.id}
                  type="button"
                  onClick={() => loadAsset(asset.id)}
                  className={`block w-full border-4 border-ink p-4 text-left shadow-brutal transition-transform hover:-translate-y-1 ${
                    selectedAsset?.id === asset.id ? "bg-gold" : "bg-white/80"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs font-black uppercase tracking-[0.14em]">{asset.asset_type}</p>
                    <StatusPill status={asset.status} />
                  </div>
                  <p className="mt-3 text-lg font-black">{asset.title}</p>
                  <p className="mt-2 text-xs font-black uppercase tracking-[0.12em]">
                    {asset.mime_type ?? "text"} / {formatBytes(asset.file_size)} / {formatStamp(asset.created_at)}
                  </p>
                </button>
              ))}
              {!assets.length ? <EmptyState text="当前没有原始资产。" /> : null}
            </div>
          </Panel>

          <Panel className="p-5" tone="paper">
            <p className="section-kicker">资产派生检查</p>
            {selectedAsset ? (
              <div className="mt-5 space-y-4">
                <div className="surface-inset border-4 border-ink p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xl font-black">{selectedAsset.title}</p>
                    {selectedAsset.raw_url ? (
                      <a href={selectedAsset.raw_url} className="brutal-action text-sm" target="_blank" rel="noreferrer">
                        原始文件
                      </a>
                    ) : null}
                  </div>
                  <p className="mt-3 break-all text-sm font-bold">
                    {selectedAsset.asset_type} / {selectedAsset.mime_type ?? "text"} / {selectedAsset.object_key ?? "内联文本"}
                  </p>
                  {selectedAsset.original_text ? (
                    <p className="mt-3 border-4 border-ink bg-white p-3 text-sm font-bold leading-relaxed">
                      {selectedAsset.original_text.slice(0, 240)}
                    </p>
                  ) : null}
                </div>
                {selectedAsset.notes.length ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {selectedAsset.notes.map((note) => (
                      <Link key={note.id} href={`/notes/${note.id}`} className="surface-inset block border-4 border-ink p-3">
                        <p className="text-xs font-black uppercase tracking-[0.14em]">{note.status}</p>
                        <p className="mt-2 text-base font-black">{note.title}</p>
                      </Link>
                    ))}
                  </div>
                ) : null}
                <div className="space-y-3">
                  {selectedAsset.derivatives.map((derivative) => (
                    <div key={derivative.id} className="surface-inset border-4 border-ink p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-sm font-black uppercase tracking-[0.14em]">{derivative.derivative_type}</p>
                        <span className="brutal-chip">{derivative.version}</span>
                      </div>
                      <p className="mt-3 whitespace-pre-wrap text-sm font-bold leading-relaxed">{derivative.content_preview}</p>
                      <JsonBlock title="元数据" value={derivative.meta_json} compact />
                    </div>
                  ))}
                  {!selectedAsset.derivatives.length ? <EmptyState text="这个资产还没有派生内容。" /> : null}
                </div>
              </div>
            ) : (
              <EmptyState text="从左侧选择一个资产查看文字识别、转写、语义提示或规范化文本。" />
            )}
          </Panel>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <Panel className="p-5" tone="story">
            <p className="section-kicker">抽取运行入口</p>
            <div className="mt-5 space-y-3">
              {notes.map((note) => (
                <button
                  key={note.id}
                  type="button"
                  onClick={() => loadRuns(note.id)}
                  className={`block w-full border-4 border-ink p-4 text-left shadow-brutal transition-transform hover:-translate-y-1 ${
                    selectedNoteId === note.id ? "bg-aqua" : "bg-white/80"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs font-black uppercase tracking-[0.14em]">{note.status}</p>
                    <p className="text-xs font-black uppercase tracking-[0.14em]">{formatStamp(note.processed_at)}</p>
                  </div>
                  <p className="mt-3 text-lg font-black">{note.title}</p>
                </button>
              ))}
              {!notes.length ? <EmptyState text="当前没有可检查的卷宗。" /> : null}
            </div>
          </Panel>

          <Panel className="p-5" tone="info">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="section-kicker">抽取运行记录</p>
              {selectedNote ? <Link href={`/notes/${selectedNote.id}`} className="tool-action bg-canvas">打开卷宗</Link> : null}
            </div>
            {selectedNote ? <p className="mt-3 text-2xl font-black">{selectedNote.title}</p> : null}
            <div className="mt-5 space-y-3">
              {runs.map((run) => (
                <div key={run.id} className="surface-inset border-4 border-ink p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs font-black uppercase tracking-[0.14em]">
                      {run.extractor_name} / {run.extractor_version}
                    </p>
                    <StatusPill status={run.is_applied ? "applied" : run.status} />
                  </div>
                  <p className="mt-3 text-lg font-black">{run.summary.title || "未命名抽取运行"}</p>
                  <p className="mt-2 text-sm font-bold leading-relaxed">
                    人物 {run.summary.entity_count} / 事件 {run.summary.event_count} / 关系 {run.summary.relation_count}
                  </p>
                  <p className="mt-2 text-xs font-black uppercase tracking-[0.12em]">{formatStamp(run.created_at)}</p>
                </div>
              ))}
              {!runs.length ? <EmptyState text="这个卷宗还没有抽取运行记录。" /> : null}
            </div>
          </Panel>
        </section>
      </main>
    </AuthGate>
  );
}

function MetricCard({
  label,
  value,
  description,
  tone,
}: {
  label: string;
  value: number;
  description: string;
  tone: "default" | "info" | "story" | "signal" | "time" | "success" | "danger" | "paper";
}) {
  return (
    <Panel className="p-4" tone={tone} intensity="quiet">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-black tracking-[0.12em]">{label}</p>
        <p className="text-2xl font-black leading-none">{value}</p>
      </div>
      <p className="mt-3 text-sm font-bold leading-relaxed text-ink/65">{description}</p>
    </Panel>
  );
}

function BacklogSignalCard({
  label,
  value,
  description,
  tone,
}: {
  label: string;
  value: number;
  description: string;
  tone: "default" | "info" | "story" | "signal" | "time" | "success" | "danger" | "paper";
}) {
  return (
    <Panel className="p-4" tone={tone} intensity="quiet">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-black tracking-[0.12em]">{label}</p>
        <p className="text-2xl font-black leading-none">{value}</p>
      </div>
      <p className="mt-3 text-sm font-bold leading-relaxed text-ink/65">{description}</p>
    </Panel>
  );
}

function StatusPill({ status }: { status: string }) {
  const tone =
    status === "failed" || status === "rejected"
      ? "bg-[var(--surface-danger-soft)]"
      : status === "completed" || status === "ready" || status === "applied"
        ? "bg-[var(--surface-success-soft)]"
        : status === "pending" || status === "running" || status === "ready_for_review"
          ? "bg-[var(--surface-time-soft)]"
          : "bg-white";
  return (
    <span className={`border-2 border-ink px-2 py-1 text-xs font-black uppercase tracking-[0.12em] ${tone}`}>
      {status}
    </span>
  );
}

function JsonBlock({ title, value, compact = false }: { title: string; value: unknown; compact?: boolean }) {
  return (
    <div className={compact ? "mt-3" : ""}>
      <p className="text-xs font-black uppercase tracking-[0.14em]">{title}</p>
      <pre className="mt-2 max-h-72 overflow-auto border-4 border-ink bg-white p-3 text-xs font-bold leading-relaxed">
        {JSON.stringify(value ?? {}, null, 2)}
      </pre>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="surface-inset border-4 border-dashed border-ink p-4 text-base font-bold">
      {text}
    </div>
  );
}

function formatStamp(value: string | null): string {
  if (!value) return "未记录";
  return value.slice(0, 16).replace("T", " ");
}

function formatBytes(value: number | null): string {
  if (!value) return "0 B";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}
