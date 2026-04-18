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

export default function NotePage() {
  const params = useParams<{ id: string }>();
  const [note, setNote] = useState<NoteDetail | null>(null);
  const [noteId, setNoteId] = useState("");
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
  }, [params]);

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
