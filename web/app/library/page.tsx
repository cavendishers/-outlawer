"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
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
      <main className="space-y-6">
        <Panel className="p-6 md:p-8" tone="quiet">
          <p className="page-kicker">Archive Library</p>
          <h1 className="page-title mt-3">档案库</h1>
          <p className="page-lede">
            原始记录和 AI 派生结果在这里汇总。每条档案都可以进入中二风故事视图，也能继续追溯结构化分析。
          </p>
        </Panel>
        <div className="grid gap-4 md:grid-cols-2">
          {notes.map((note) => (
            <Link key={note.id} href={`/story/note/${note.id}`}>
              <article className="dossier-card">
                <div className="dossier-card-content">
                <div className="flex items-center justify-between gap-3">
                  <p className="meta-copy">{note.status}</p>
                  {note.primary_time ? (
                    <p className="meta-copy">
                      {note.primary_time.slice(0, 10)}
                    </p>
                  ) : null}
                </div>
                <p className="single-line-clamp mt-3 text-2xl font-black">{note.title}</p>
                <p className="body-copy mt-3">{note.summary ?? "等待摘要..."}</p>
                </div>
              </article>
            </Link>
          ))}
        </div>
      </main>
    </AuthGate>
  );
}
