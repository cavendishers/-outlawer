"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AuthGate } from "@/components/auth-gate";
import { apiFetch } from "@/lib/api";

type NoteItem = {
  id: string;
  title: string;
  summary: string | null;
  status: string;
  primary_time: string | null;
};

export default function LibraryPage() {
  const [notes, setNotes] = useState<NoteItem[]>([]);

  useEffect(() => {
    apiFetch<{ items: NoteItem[] }>("/notes").then((data) => setNotes(data.items)).catch(() => setNotes([]));
  }, []);

  return (
    <AuthGate>
      <main className="space-y-4">
        <section className="workbench-header">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="workbench-title">档案库</h1>
                <span className="workbench-stamp bg-canvas">{notes.length} 条</span>
              </div>
              <p className="workbench-lede">
                扫标题、时间和状态，进入档案查看原文、故事视图和结构化分析。
              </p>
            </div>
            <Link href="/inbox" className="tool-action bg-neon">
              导入
            </Link>
          </div>
        </section>

        <section className="space-y-3">
          {notes.map((note) => (
            <Link key={note.id} href={`/story/note/${note.id}`} className="block">
              <article className="group dense-record md:grid-cols-[12rem_1fr]">
                <div className="dense-record-side bg-canvas">
                  <p className="text-xs font-black tracking-[0.12em]">时间</p>
                  <p className="mt-3 text-lg font-black leading-tight">
                    {note.primary_time ? note.primary_time.slice(0, 10) : "待校准"}
                  </p>
                </div>
                <div className="dense-record-body">
                  <div className="min-w-0">
                    <p className="dense-record-title">{note.title}</p>
                    <p className="dense-record-summary">{note.summary ?? "等待摘要..."}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="brutal-chip">{note.status}</span>
                      {note.primary_time ? <span className="brutal-chip">{note.primary_time.slice(0, 10)}</span> : null}
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

          {notes.length === 0 ? (
            <div className="empty-state">
              当前没有档案。导入一条卷宗后，原始文本和 AI 派生内容会出现在这里。
            </div>
          ) : null}
        </section>
      </main>
    </AuthGate>
  );
}
