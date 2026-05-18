"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

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
  primary_time: string | null;
};

type StoryView = {
  id: string;
  title: string;
  content: string;
  style_type: string;
};

export default function NoteStoryPage() {
  const params = useParams<{ id: string }>();
  const [note, setNote] = useState<NoteDetail | null>(null);
  const [story, setStory] = useState<StoryView | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!params?.id) return;
    Promise.all([
      apiFetch<NoteDetail>(`/notes/${params.id}`),
      apiFetch<StoryView>(`/views/story/note/${params.id}`),
    ])
      .then(([noteData, storyData]) => {
        setNote(noteData);
        setStory(storyData);
        setError("");
      })
      .catch((err) => {
        setNote(null);
        setStory(null);
        setError(err instanceof Error ? err.message : "中二风卷宗加载失败");
      });
  }, [params]);

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-4xl">
              <div className="flex flex-wrap gap-2">
                <span className="workbench-stamp bg-peach">风格化阅读</span>
                <span className="workbench-stamp bg-gold">{note?.primary_time?.slice(0, 10) ?? "待校时"}</span>
                <span className="workbench-stamp bg-canvas">{note?.category ?? "未分类"}</span>
              </div>
              <h1 className="workbench-title mt-3">{story?.title ?? note?.title ?? "风格化卷宗载入中"}</h1>
              <p className="workbench-lede max-w-4xl">
                {note?.summary ?? "系统正在把结构化知识翻译成更戏剧化的展示文本。"}
              </p>
            </div>
            {note?.id ? (
              <Link href={`/notes/${note.id}`} className="tool-action bg-canvas">
                返回标准视图
              </Link>
            ) : null}
          </div>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <Panel className="p-6 md:p-8" tone="story" intensity="quiet">
          <p className="section-kicker">风格化叙事</p>
          <div className="mt-5 space-y-4">
            {(story?.content ?? "暂无风格化内容。")
              .split(/\n+/)
              .filter(Boolean)
              .map((paragraph, index) => (
                <p key={`${index}-${paragraph.slice(0, 12)}`} className="whitespace-pre-wrap text-lg font-semibold leading-9 text-muted">
                  {paragraph}
                </p>
              ))}
          </div>
        </Panel>

        <details className="border-4 border-ink bg-bone p-5 shadow-brutalSoft">
          <summary className="cursor-pointer text-sm font-black tracking-[0.12em]">
            展开标准摘要与原始文本
          </summary>
          <div className="mt-5 grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
            <Panel className="p-5" tone="info" intensity="quiet">
              <p className="section-kicker">标准摘要</p>
              <p className="body-copy mt-4">{note?.summary ?? "暂无摘要"}</p>
            </Panel>
            <Panel className="p-5" tone="quiet" intensity="quiet">
              <p className="section-kicker">原始文本摘录</p>
              <p className="body-copy mt-4 whitespace-pre-wrap">
                {note?.canonical_text ?? "暂无标准文本。"}
              </p>
            </Panel>
          </div>
        </details>
      </main>
    </AuthGate>
  );
}
