"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type EventItem = {
  id: string;
  title: string;
  summary: string | null;
  description: string | null;
  time_text: string | null;
  location_text: string | null;
  confidence_score: number | null;
};

export default function EventsPage() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<{ items: EventItem[] }>("/events")
      .then((data) => {
        setEvents(data.items);
        setError("");
      })
      .catch((err) => {
        setEvents([]);
        setError(err instanceof Error ? err.message : "事件列表加载失败");
      });
  }, []);

  return (
    <AuthGate>
      <main className="space-y-5">
        <section className="border-4 border-ink bg-bone p-5 shadow-brutal md:p-6">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-4xl">
              <div className="flex flex-wrap items-center gap-3">
                <p className="page-kicker">Event Dossier</p>
                <span className="border-2 border-ink bg-gold px-3 py-1 text-xs font-black uppercase tracking-[0.14em]">
                  {events.length} events
                </span>
              </div>
              <h1 className="mt-3 font-display text-[clamp(3.2rem,7vw,6.6rem)] leading-[0.86]">
                事件清单
              </h1>
              <p className="mt-4 max-w-2xl text-base font-black leading-relaxed text-ink/65">
                按时间追踪人物与事件的交叉点。先扫事件，再进入详情追关系。
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link href="/inbox" className="brutal-action brutal-action-primary">
                导入新卷宗
              </Link>
              <Link href="/timeline" className="brutal-action brutal-action-secondary">
                打开图谱
              </Link>
            </div>
          </div>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <section className="space-y-4">
          {events.map((event) => (
            <Link key={event.id} href={`/events/${event.id}`} className="block">
              <article className="group grid border-4 border-ink bg-bone shadow-brutal transition-transform hover:-translate-y-1 md:grid-cols-[13rem_1fr]">
                <div className="flex border-b-4 border-ink bg-gold p-5 md:border-b-0 md:border-r-4 md:p-6">
                  <div className="flex min-h-24 w-full flex-col justify-between gap-5">
                    <p className="text-xs font-black uppercase tracking-[0.16em]">Time Anchor</p>
                    <p className="text-2xl font-black leading-tight">
                      {event.time_text ?? "待校准时间"}
                    </p>
                  </div>
                </div>

                <div className="grid gap-4 p-5 md:grid-cols-[1fr_auto] md:p-6">
                  <div className="min-w-0">
                    <p className="text-[clamp(1.8rem,3vw,3.2rem)] font-black leading-[0.98] transition-transform group-hover:translate-x-1">
                      {event.title}
                    </p>
                    <p className="mt-3 line-clamp-2 max-w-4xl text-base font-black leading-relaxed text-ink/60">
                      {event.summary ?? event.description ?? "暂无摘要，进入详情页查看更多事件信息。"}
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {event.location_text ? (
                        <span className="brutal-chip">{event.location_text}</span>
                      ) : (
                        <span className="brutal-chip">地点待补</span>
                      )}
                      <span className="brutal-chip">事件节点</span>
                    </div>
                  </div>

                  <div className="flex items-start justify-start md:justify-end">
                    {event.confidence_score ? (
                      <span className="border-4 border-ink bg-canvas px-4 py-2 text-lg font-black shadow-brutal">
                        {Math.round(event.confidence_score * 100)}%
                      </span>
                    ) : (
                      <span className="border-4 border-ink bg-canvas px-4 py-2 text-lg font-black shadow-brutal">
                        待审
                      </span>
                    )}
                  </div>
                </div>
              </article>
            </Link>
          ))}

          {events.length === 0 && !error ? (
            <div className="empty-state">
              当前没有事件节点。导入一条卷宗后，系统会把可追踪事件放到这里。
            </div>
          ) : null}
        </section>
      </main>
    </AuthGate>
  );
}
