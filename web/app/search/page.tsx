"use client";

import Link from "next/link";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type SearchHit = {
  id: string;
  label: string;
  summary: string | null;
  href: string;
  result_type: string;
  meta: Array<string | null>;
};

type SearchNote = {
  id: string;
  title: string;
  summary: string | null;
  status: string;
  primary_time: string | null;
  href: string;
  search_type: string;
};

type SearchEntity = {
  id: string;
  display_name: string;
  canonical_name: string;
  entity_type: string;
  description: string | null;
  aliases: string[];
  confidence_score: number | null;
  href: string;
  search_type: string;
};

type SearchEvent = {
  id: string;
  title: string;
  summary: string | null;
  event_type: string | null;
  time_text: string | null;
  location_text: string | null;
  confidence_score: number | null;
  href: string;
  search_type: string;
};

type SimilarNote = {
  id: string;
  note_id: string;
  title: string;
  summary: string | null;
  primary_time: string | null;
  href: string;
  search_type: string;
  score: number;
};

type UnifiedSearchResponse = {
  query: string;
  seed_note_id: string | null;
  seed_note_title: string | null;
  top_hits: SearchHit[];
  notes: SearchNote[];
  entities: SearchEntity[];
  events: SearchEvent[];
  similar_notes: SimilarNote[];
  stats: {
    top_hit_count: number;
    note_count: number;
    entity_count: number;
    event_count: number;
    similar_count: number;
  };
};

type NoteOption = {
  id: string;
  title: string;
  primary_time: string | null;
};

const queryPresets = ["启动会", "张三", "图谱", "导入流程", "会议室A"];

function formatDateLabel(value: string | null): string {
  if (!value) return "未标定";
  return value.slice(0, 10);
}

function toneForHit(resultType: string): "default" | "info" | "story" | "time" {
  if (resultType === "entity") return "info";
  if (resultType === "event") return "time";
  if (resultType === "similar_note") return "story";
  return "default";
}

function labelForResultType(resultType: string): string {
  if (resultType === "entity") return "人物";
  if (resultType === "event") return "事件";
  if (resultType === "similar_note") return "相似卷宗";
  return "卷宗";
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [seedNoteId, setSeedNoteId] = useState("");
  const [noteOptions, setNoteOptions] = useState<NoteOption[]>([]);
  const [results, setResults] = useState<UnifiedSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    apiFetch<{ items: NoteOption[] }>("/notes")
      .then((data) => {
        startTransition(() => {
          setNoteOptions(data.items);
        });
      })
      .catch(() => {
        startTransition(() => {
          setNoteOptions([]);
        });
      });
  }, []);

  useEffect(() => {
    const normalizedQuery = deferredQuery.trim();
    if (!normalizedQuery && !seedNoteId) {
      startTransition(() => {
        setResults(null);
        setError("");
        setLoading(false);
      });
      return;
    }

    const params = new URLSearchParams();
    if (normalizedQuery) params.set("q", normalizedQuery);
    if (seedNoteId) params.set("seed_note_id", seedNoteId);
    params.set("limit", "8");

    setLoading(true);
    apiFetch<UnifiedSearchResponse>(`/search/unified?${params.toString()}`)
      .then((data) => {
        startTransition(() => {
          setResults(data);
          setError("");
          setLoading(false);
        });
      })
      .catch((err) => {
        startTransition(() => {
          setResults(null);
          setError(err instanceof Error ? err.message : "统一搜索加载失败");
          setLoading(false);
        });
      });
  }, [deferredQuery, seedNoteId]);

  const selectedNote = useMemo(
    () => noteOptions.find((item) => item.id === seedNoteId) ?? null,
    [noteOptions, seedNoteId],
  );

  return (
    <AuthGate>
      <main className="space-y-4">
        <section className="workbench-header">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="workbench-title">统一搜索</h1>
                <span className={`workbench-stamp ${loading || results ? "bg-neon" : "bg-aqua"}`}>
                  {loading ? "检索中" : results ? "已聚合" : "待命中"}
                </span>
              </div>
              <p className="workbench-lede">
                聚合关键词、相似卷宗、人物和事件结果。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="brutal-chip">关键词</span>
              <span className="brutal-chip">相似</span>
              <span className="brutal-chip">人物</span>
              <span className="brutal-chip">事件</span>
            </div>
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <Panel className="p-4" tone="quiet" intensity="quiet">
            <label className="section-kicker" htmlFor="global-search-query">
              关键词检索
            </label>
            <input
              id="global-search-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="brutal-input mt-3 w-full text-lg font-semibold"
              placeholder="搜索笔记标题、人物名称、事件摘要、地点、时间"
            />
            <div className="mt-4 flex flex-wrap gap-2">
              {queryPresets.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="brutal-chip"
                  onClick={() => setQuery(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </Panel>

          <Panel className="p-4" tone="info" intensity="quiet">
            <label className="section-kicker" htmlFor="seed-note-select">
              相似检索种子
            </label>
            <select
              id="seed-note-select"
              value={seedNoteId}
              onChange={(event) => setSeedNoteId(event.target.value)}
              className="brutal-input mt-3 w-full text-lg font-semibold"
            >
              <option value="">不启用相似检索</option>
              {noteOptions.map((note) => (
                <option key={note.id} value={note.id}>
                  {formatDateLabel(note.primary_time)} · {note.title}
                </option>
              ))}
            </select>
            <p className="mt-3 line-clamp-1 text-sm font-semibold leading-relaxed">
              {selectedNote ? `种子：${selectedNote.title}` : "选择卷宗后启用相似检索。"}
            </p>
            <div className="mt-5">
              <button
                type="button"
                className="brutal-action brutal-action-secondary"
                onClick={() => {
                  setQuery("");
                  setSeedNoteId("");
                }}
              >
                重置检索
              </button>
            </div>
          </Panel>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        {loading ? (
          <Panel className="p-6 text-lg font-bold" tone="default">
            正在聚合笔记、人物、事件和相似内容，请稍候……
          </Panel>
        ) : null}

        {results ? (
          <>
            <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <Panel className="metric-card" tone="signal" intensity="quiet">
                <p className="section-kicker">总命中</p>
                <p className="mt-3 text-4xl font-black">{results.stats.top_hit_count}</p>
              </Panel>
              <Panel className="metric-card" tone="quiet" intensity="quiet">
                <p className="section-kicker">笔记</p>
                <p className="mt-3 text-4xl font-black">{results.stats.note_count}</p>
              </Panel>
              <Panel className="metric-card" tone="info" intensity="quiet">
                <p className="section-kicker">人物</p>
                <p className="mt-3 text-4xl font-black">{results.stats.entity_count}</p>
              </Panel>
              <Panel className="metric-card" tone="time" intensity="quiet">
                <p className="section-kicker">事件</p>
                <p className="mt-3 text-4xl font-black">{results.stats.event_count}</p>
              </Panel>
              <Panel className="metric-card" tone="story" intensity="quiet">
                <p className="section-kicker">相似卷宗</p>
                <p className="mt-3 text-4xl font-black">{results.stats.similar_count}</p>
              </Panel>
            </section>

            <section className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="section-kicker">优先命中</p>
                <span className="brutal-chip">{results.top_hits.length} 条</span>
              </div>
              {results.top_hits.length ? (
                <div className="space-y-3">
                  {results.top_hits.map((hit) => (
                    <Link key={`${hit.result_type}-${hit.id}`} href={hit.href} className="block">
                      <article className="group dense-record md:grid-cols-[10rem_1fr]">
                        <div className={`dense-record-side ${toneForHit(hit.result_type) === "info" ? "bg-aqua" : toneForHit(hit.result_type) === "time" ? "bg-gold" : toneForHit(hit.result_type) === "story" ? "bg-peach" : "bg-canvas"}`}>
                          <p className="text-xs font-black tracking-[0.12em]">类型</p>
                          <p className="mt-3 text-lg font-black leading-tight">{labelForResultType(hit.result_type)}</p>
                        </div>
                        <div className="dense-record-body">
                          <div className="min-w-0">
                            <p className="dense-record-title">{hit.label}</p>
                            <p className="dense-record-summary">
                              {hit.summary || "该条命中暂无额外摘要，进入详情页查看完整信息。"}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-2">
                              {hit.meta.filter(Boolean).slice(0, 3).map((item) => (
                                <span key={item} className="brutal-chip">
                                  {item}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="flex items-start justify-start md:justify-end">
                            <span className="border-2 border-ink bg-canvas px-3 py-2 text-sm font-black shadow-brutalTiny">
                              查看
                            </span>
                          </div>
                        </div>
                      </article>
                    </Link>
                  ))}
                </div>
              ) : (
                <Panel className="p-5" tone="default">
                  当前没有形成明显的优先命中，继续换关键词或指定一条相似检索种子。
                </Panel>
              )}
            </section>

            <section className="grid gap-6 xl:grid-cols-2">
              <div className="space-y-4">
                <Panel className="p-5" tone="quiet" intensity="quiet">
                  <p className="section-kicker">笔记命中</p>
                </Panel>
                {results.notes.length ? (
                  results.notes.map((note) => (
                    <Link key={note.id} href={note.href} className="block">
                      <Panel className="p-5 transition-transform hover:-translate-y-1" tone="quiet" intensity="quiet">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="meta-copy">{note.status}</p>
                          <p className="meta-copy">{formatDateLabel(note.primary_time)}</p>
                        </div>
                        <p className="card-title mt-3">{note.title}</p>
                        <p className="body-copy mt-3">
                          {note.summary || "暂无摘要，进入卷宗详情查看标准视图与中二风版本。"}
                        </p>
                      </Panel>
                    </Link>
                  ))
                ) : (
                  <Panel className="p-5" tone="default">
                    当前关键词还没有命中卷宗标题或正文。
                  </Panel>
                )}

                <Panel className="p-5" tone="story" intensity="quiet">
                  <p className="section-kicker">相似卷宗</p>
                </Panel>
                {results.similar_notes.length ? (
                  results.similar_notes.map((note) => (
                    <Link key={note.id} href={note.href} className="block">
                      <Panel className="p-5 transition-transform hover:-translate-y-1" tone="story" intensity="quiet">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="section-kicker">相似卷宗</p>
                          <p className="section-kicker">
                            {Math.round(note.score * 100)}%
                          </p>
                        </div>
                        <p className="card-title mt-3">{note.title}</p>
                        <p className="mt-3 text-sm font-semibold leading-relaxed">
                          {note.summary || "暂无摘要，进入卷宗详情查看相邻主题。"}
                        </p>
                      </Panel>
                    </Link>
                  ))
                ) : (
                  <Panel className="p-5" tone="story">
                    {seedNoteId ? "当前种子还没有找到更接近的卷宗。" : "选择一条卷宗后，这里会展示 embedding 相似结果。"}
                  </Panel>
                )}
              </div>

              <div className="space-y-4">
                <Panel className="p-5" tone="info" intensity="quiet">
                  <p className="section-kicker">人物命中</p>
                </Panel>
                {results.entities.length ? (
                  results.entities.map((entity) => (
                    <Link key={entity.id} href={entity.href} className="block">
                      <Panel className="p-5 transition-transform hover:-translate-y-1" tone="info" intensity="quiet">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="section-kicker">{entity.entity_type}</p>
                          {entity.confidence_score ? (
                            <p className="section-kicker">
                              {Math.round(entity.confidence_score * 100)}%
                            </p>
                          ) : null}
                        </div>
                        <p className="card-title mt-3">{entity.display_name}</p>
                        <p className="mt-2 text-sm font-semibold text-muted">{entity.canonical_name}</p>
                        <p className="mt-3 text-sm font-semibold leading-relaxed">
                          {entity.description || "暂无人物注释，进入档案页查看更多上下文。"}
                        </p>
                        <div className="mt-4 flex flex-wrap gap-2">
                          {entity.aliases.slice(0, 3).map((alias) => (
                            <span key={alias} className="brutal-chip">
                              {alias}
                            </span>
                          ))}
                        </div>
                      </Panel>
                    </Link>
                  ))
                ) : (
                  <Panel className="p-5" tone="info">
                    当前关键词没有命中人物或别名。
                  </Panel>
                )}

                <Panel className="p-5" tone="time" intensity="quiet">
                  <p className="section-kicker">事件命中</p>
                </Panel>
                {results.events.length ? (
                  results.events.map((event) => (
                    <Link key={event.id} href={event.href} className="block">
                      <Panel className="p-5 transition-transform hover:-translate-y-1" tone="time" intensity="quiet">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="section-kicker">
                            {event.event_type || "event"}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {event.time_text ? <span className="brutal-chip">{event.time_text}</span> : null}
                            {event.location_text ? <span className="brutal-chip">{event.location_text}</span> : null}
                          </div>
                        </div>
                        <p className="card-title mt-3">{event.title}</p>
                        <p className="mt-3 text-sm font-semibold leading-relaxed">
                          {event.summary || "暂无事件摘要，进入事件页查看参与人物和关联事件。"}
                        </p>
                      </Panel>
                    </Link>
                  ))
                ) : (
                  <Panel className="p-5" tone="time">
                    当前关键词没有命中事件标题、地点或摘要。
                  </Panel>
                )}
              </div>
            </section>
          </>
        ) : !loading ? (
          <Panel className="p-6 text-lg font-bold" tone="default">
            先输入一个关键词，或者指定一条卷宗作为相似检索种子，统一搜索才会开始工作。
          </Panel>
        ) : null}
      </main>
    </AuthGate>
  );
}
