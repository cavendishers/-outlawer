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
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-3">
                <p className="page-kicker">事件索引</p>
                <span className="border-2 border-ink bg-gold px-3 py-1 text-xs font-black uppercase tracking-[0.14em]">
                  {events.length} 条事件
                </span>
              </div>
              <h1 className="mt-3 text-[clamp(2.6rem,5vw,4.6rem)] font-black leading-[0.92] tracking-[-0.08em]">
                事件清单
              </h1>
              <p className="mt-3 max-w-2xl text-base font-bold leading-relaxed text-ink/65">
                先扫时间、标题和参与线索，再进入详情追关系。
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
                <div className="flex border-b-4 border-ink bg-gold p-4 md:border-b-0 md:border-r-4 md:p-5">
                  <div className="flex min-h-20 w-full flex-col justify-between gap-4">
                    <p className="text-xs font-black tracking-[0.12em]">时间</p>
                    <p className="text-xl font-black leading-tight">
                      {event.time_text ?? "待校准时间"}
                    </p>
                  </div>
                </div>

                <div className="grid gap-4 p-5 md:grid-cols-[1fr_auto]">
                  <div className="min-w-0">
                    <p className="text-[clamp(1.45rem,2.2vw,2.1rem)] font-black leading-tight tracking-[-0.04em] transition-transform group-hover:translate-x-1">
                      {event.title}
                    </p>
                    <p className="mt-3 line-clamp-2 max-w-4xl text-sm font-bold leading-relaxed text-ink/60 md:text-base">
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
                      <span className="border-4 border-ink bg-canvas px-3 py-2 text-base font-black shadow-brutal">
                        {Math.round(event.confidence_score * 100)}%
                      </span>
                    ) : (
                      <span className="border-4 border-ink bg-canvas px-3 py-2 text-base font-black shadow-brutal">
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
