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
        <Panel className="p-6" tone="default">
          <h1 className="text-4xl font-black">档案库</h1>
        </Panel>
        <div className="grid gap-4 md:grid-cols-2">
          {notes.map((note) => (
            <Link key={note.id} href={`/story/note/${note.id}`}>
              <Panel className="p-5 transition-transform hover:-translate-y-1" tone="default">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-black uppercase tracking-[0.16em]">{note.status}</p>
                  {note.primary_time ? (
                    <p className="text-xs font-black uppercase tracking-[0.16em]">
                      {note.primary_time.slice(0, 10)}
                    </p>
                  ) : null}
                </div>
                <p className="single-line-clamp mt-3 text-2xl font-black">{note.title}</p>
                <p className="mt-3 text-base font-semibold">{note.summary ?? "等待摘要..."}</p>
              </Panel>
            </Link>
          ))}
        </div>
      </main>
    </AuthGate>
  );
}
