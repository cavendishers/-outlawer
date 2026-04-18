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
        <Panel className="p-6 md:p-8" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.2em]">Story View</p>
          <h1 className="mt-3 font-display text-[clamp(2.4rem,5vw,4.8rem)] leading-[0.9]">
            {story?.title ?? note?.title ?? "风格化卷宗载入中"}
          </h1>
          <p className="mt-4 max-w-4xl text-lg font-bold leading-relaxed">
            {note?.summary ?? "系统正在把结构化知识翻译成更戏剧化的展示文本。"}
          </p>
        </Panel>

        <section className="grid gap-4 lg:grid-cols-3">
          <Panel className="p-5" tone="info">
            <p className="text-xs font-black uppercase tracking-[0.16em]">原始卷宗</p>
            {note?.id ? (
              <Link
                href={`/notes/${note.id}`}
                className="brutal-action brutal-action-secondary mt-4 text-lg"
              >
                返回标准视图
              </Link>
            ) : (
              <p className="mt-4 text-base font-bold">标准视图载入中。</p>
            )}
          </Panel>

          <Panel className="p-5" tone="time">
            <p className="text-xs font-black uppercase tracking-[0.16em]">时间锚点</p>
            <p className="mt-3 text-2xl font-black">{note?.primary_time?.slice(0, 10) ?? "待校准"}</p>
          </Panel>

          <Panel className="p-5" tone="default">
            <p className="text-xs font-black uppercase tracking-[0.16em]">卷宗分类</p>
            <p className="mt-3 text-2xl font-black">{note?.category ?? "未分类"}</p>
          </Panel>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <Panel className="p-6 md:p-8" tone="story">
          <p className="text-sm font-black uppercase tracking-[0.16em]">风格化叙事</p>
          <div className="mt-5 space-y-4">
            {(story?.content ?? "暂无风格化内容。")
              .split(/\n+/)
              .filter(Boolean)
              .map((paragraph, index) => (
                <p key={`${index}-${paragraph.slice(0, 12)}`} className="whitespace-pre-wrap text-lg font-semibold leading-9">
                  {paragraph}
                </p>
              ))}
          </div>
        </Panel>

        <Panel className="p-6" tone="info">
          <p className="text-sm font-black uppercase tracking-[0.16em]">标准摘要</p>
          <p className="mt-4 text-base font-semibold leading-relaxed">{note?.summary ?? "暂无摘要"}</p>
        </Panel>

        <Panel className="p-6" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.16em]">原始文本摘录</p>
          <p className="mt-4 whitespace-pre-wrap text-base font-semibold leading-relaxed">
            {note?.canonical_text ?? "暂无标准文本。"}
          </p>
        </Panel>
      </main>
    </AuthGate>
  );
}
