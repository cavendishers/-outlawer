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
      <main className="space-y-4">
        <section className="border-4 border-ink bg-bone px-4 py-4 shadow-brutal md:px-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-[clamp(2rem,4vw,3.2rem)] font-black leading-none tracking-[-0.06em]">
                  事件清单
                </h1>
                <span className="border-2 border-ink bg-gold px-3 py-1 text-xs font-black tracking-[0.12em]">
                  {events.length} 条
                </span>
              </div>
              <p className="mt-2 text-sm font-bold leading-relaxed text-ink/60">
                扫时间、标题、地点，进入详情再看人物和关系。
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Link href="/inbox" className="border-2 border-ink bg-neon px-3 py-2 text-sm font-black shadow-brutalTiny transition-transform hover:-translate-y-0.5">
                导入
              </Link>
              <Link href="/timeline" className="border-2 border-ink bg-canvas px-3 py-2 text-sm font-black shadow-brutalTiny transition-transform hover:-translate-y-0.5">
                图谱
              </Link>
            </div>
          </div>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <section className="space-y-3">
          {events.map((event) => (
            <Link key={event.id} href={`/events/${event.id}`} className="block">
              <article className="group grid border-4 border-ink bg-bone shadow-brutal transition-transform hover:-translate-y-1 md:grid-cols-[12rem_1fr]">
                <div className="border-b-4 border-ink bg-gold px-4 py-3 md:border-b-0 md:border-r-4">
                  <p className="text-xs font-black tracking-[0.12em]">时间</p>
                  <p className="mt-3 text-lg font-black leading-tight">
                    {event.time_text ?? "待校准"}
                  </p>
                </div>

                <div className="grid gap-3 px-4 py-3 md:grid-cols-[1fr_auto]">
                  <div className="min-w-0">
                    <p className="text-[clamp(1.35rem,2vw,1.8rem)] font-black leading-tight tracking-[-0.04em] transition-transform group-hover:translate-x-1">
                      {event.title}
                    </p>
                    <p className="mt-2 line-clamp-1 max-w-4xl text-sm font-bold leading-relaxed text-ink/60">
                      {event.summary ?? event.description ?? "暂无摘要，进入详情页查看更多事件信息。"}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {event.location_text ? (
                        <span className="brutal-chip">{event.location_text}</span>
                      ) : (
                        <span className="brutal-chip">地点待补</span>
                      )}
                      {event.confidence_score ? (
                        <span className="brutal-chip">
                          置信度 {Math.round(event.confidence_score * 100)}%
                        </span>
                      ) : (
                        <span className="brutal-chip">待复核</span>
                      )}
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
