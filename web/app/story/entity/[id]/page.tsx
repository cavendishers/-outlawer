"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { EntityTimelineWorkspace } from "@/components/entity-timeline-workspace";
import { EntityJourneyMap } from "@/components/entity-journey-map";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type EntityDetail = {
  id: string;
  entity_type: string;
  canonical_name: string;
  display_name: string;
  description: string | null;
  aliases: string[];
  confidence_score: number | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
  related_events: Array<{
    id: string;
    title: string;
    summary: string | null;
    time_text: string | null;
    event_type: string | null;
    location_text?: string | null;
    role?: string | null;
    relation_type?: string | null;
    start_time?: string | null;
  }>;
  timeline_fragments: Array<{
    event_id: string;
    title: string;
    summary: string | null;
    time_text: string | null;
    event_type: string | null;
    location_text: string | null;
    role: string | null;
    relation_type: string | null;
    chapter_label: string;
    source_note_title: string | null;
    position: number;
    total: number;
  }>;
};

type StoryView = {
  id: string;
  title: string;
  content: string;
  style_type: string;
};

export default function EntityStoryPage() {
  const params = useParams<{ id: string }>();
  const [entity, setEntity] = useState<EntityDetail | null>(null);
  const [story, setStory] = useState<StoryView | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!params?.id) return;
    Promise.all([
      apiFetch<EntityDetail>(`/entities/${params.id}`),
      apiFetch<StoryView>(`/views/story/entity/${params.id}`),
    ])
      .then(([entityData, storyData]) => {
        setEntity(entityData);
        setStory(storyData);
        setError("");
      })
      .catch((err) => {
        setEntity(null);
        setStory(null);
        setError(err instanceof Error ? err.message : "人物故事页加载失败");
      });
  }, [params]);

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Panel className="p-6 md:p-8" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.2em]">Entity Story</p>
            <h1 className="mt-3 font-display text-[clamp(2.4rem,5vw,4.8rem)] leading-[0.9]">
              {story?.title ?? entity?.display_name ?? "人物档案载入中"}
            </h1>
            <p className="mt-4 text-lg font-bold leading-relaxed">
              {entity?.description ?? "该角色的设定注释尚未补齐，先从故事视图读取它的气场。"}
            </p>
            {entity ? (
              <div className="mt-6 flex flex-wrap gap-3">
                <Link href={`/curation/entities/${entity.id}`} className="brutal-action brutal-action-primary text-lg">
                  进入校对台
                </Link>
                <Link href={`/review/entities/${entity.id}`} className="brutal-action brutal-action-info text-lg">
                  查看审核页
                </Link>
              </div>
            ) : null}
          </Panel>

          <Panel className="p-6" tone="info">
            <p className="text-xs font-black uppercase tracking-[0.16em]">身份卡</p>
            <p className="mt-3 text-4xl font-black">{entity?.display_name ?? "..."}</p>
            <p className="mt-2 text-base font-semibold opacity-80">{entity?.canonical_name}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {entity?.entity_type ? (
                <span className="brutal-chip">
                  {entity.entity_type}
                </span>
              ) : null}
              {entity?.confidence_score ? (
                <span className="brutal-chip">
                  {Math.round(entity.confidence_score * 100)}%
                </span>
              ) : null}
            </div>
          </Panel>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Panel className="p-6" tone="story">
            <p className="text-sm font-black uppercase tracking-[0.16em]">中二风档案</p>
            <p className="mt-4 whitespace-pre-wrap text-base font-semibold leading-relaxed">
              {story?.content ?? "风格化卷轴尚未生成。"}
            </p>
          </Panel>

          <Panel className="p-6" tone="info">
            <p className="text-sm font-black uppercase tracking-[0.16em]">别名与出场时间</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {(entity?.aliases ?? []).length ? (
                entity?.aliases.map((alias) => (
                  <span key={alias} className="brutal-chip">
                    {alias}
                  </span>
                ))
              ) : (
                <p className="text-base font-bold">暂无别名。</p>
              )}
            </div>
            {entity?.first_seen_at ? (
              <p className="mt-5 text-sm font-black uppercase tracking-[0.16em]">
                first seen {entity.first_seen_at}
              </p>
            ) : null}
            {entity?.last_seen_at ? (
              <p className="mt-2 text-sm font-black uppercase tracking-[0.16em]">
                last seen {entity.last_seen_at}
              </p>
            ) : null}
            <p className="mt-5 text-4xl font-black">{entity?.timeline_fragments.length ?? 0}</p>
            <p className="mt-2 text-sm font-bold leading-relaxed">
              当前角色已经被挂接到 {entity?.timeline_fragments.length ?? 0} 个事件节点，可沿时间轴继续回溯。
            </p>
          </Panel>
        </section>

        <Panel className="p-6 md:p-8" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.16em]">人物时间线片段</p>
          {entity ? (
            <div className="mt-5">
              <EntityJourneyMap
                displayName={entity.display_name}
                entityType={entity.entity_type}
                fragments={entity.timeline_fragments}
              />
            </div>
          ) : null}
          <div className="mt-6 space-y-4">
            {(entity?.timeline_fragments ?? []).map((fragment) => (
              <Link key={fragment.event_id} href={`/events/${fragment.event_id}`} className="block transition-transform hover:-translate-y-1">
                <div className="grid gap-4 lg:grid-cols-[180px_1fr]">
                  <div className="flex min-h-32 flex-col justify-between border-4 border-ink bg-gold p-4">
                    <p className="text-xs font-black uppercase tracking-[0.16em]">{fragment.chapter_label}</p>
                    <p className="text-2xl font-black">{fragment.time_text ?? "待校时"}</p>
                    <p className="text-xs font-black uppercase tracking-[0.16em]">
                      {fragment.position}/{fragment.total}
                    </p>
                  </div>
                  <Panel className="relative overflow-hidden p-5" tone="default">
                    <div className="absolute inset-y-0 left-0 w-3 bg-ink" />
                    <div className="pl-4">
                      <div className="flex flex-wrap gap-2">
                        {fragment.role ? (
                          <span className="brutal-chip">
                            {fragment.role}
                          </span>
                        ) : null}
                        {fragment.event_type ? (
                          <span className="brutal-chip">
                            {fragment.event_type}
                          </span>
                        ) : null}
                        {fragment.location_text ? (
                          <span className="brutal-chip">
                            {fragment.location_text}
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-4 text-3xl font-black">{fragment.title}</p>
                      <p className="mt-3 text-base font-semibold leading-relaxed">
                        {fragment.summary ?? "暂无事件摘要。"}
                      </p>
                      {fragment.source_note_title ? (
                        <p className="mt-4 text-sm font-black uppercase tracking-[0.16em]">
                          来源卷宗 {fragment.source_note_title}
                        </p>
                      ) : null}
                    </div>
                  </Panel>
                </div>
              </Link>
            ))}
            {entity && entity.timeline_fragments.length === 0 ? (
              <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
                当前人物还没有可展开的时间线片段。等更多事件进入图谱后，这里会逐步长出完整轨迹。
              </div>
            ) : null}
          </div>
        </Panel>

        {entity ? (
          <EntityTimelineWorkspace
            entityId={entity.id}
            displayName={entity.display_name}
            entityType={entity.entity_type}
            aliases={entity.aliases}
            fragments={entity.timeline_fragments}
            relatedEvents={entity.related_events}
          />
        ) : null}

        <Panel className="p-6" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.16em]">关联事件速览</p>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {(entity?.related_events ?? []).map((item) => (
              <Link key={item.id} href={`/events/${item.id}`}>
                <Panel className="h-full p-5 transition-transform hover:-translate-y-1" tone="default">
                  <p className="text-xs font-black uppercase tracking-[0.16em]">
                    {item.time_text ?? item.event_type ?? "事件"}
                  </p>
                  <p className="mt-3 text-2xl font-black">{item.title}</p>
                  <p className="mt-3 text-sm font-bold leading-relaxed">{item.summary ?? "暂无摘要"}</p>
                </Panel>
              </Link>
            ))}
          </div>
        </Panel>
      </main>
    </AuthGate>
  );
}
