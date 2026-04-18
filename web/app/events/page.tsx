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
      <main className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <Panel className="p-6 md:p-8" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.2em]">Event Dossier</p>
            <h1 className="mt-3 font-display text-[clamp(2.4rem,5.5vw,4.8rem)] leading-[0.9]">事件清单</h1>
            <p className="mt-4 max-w-3xl text-lg font-bold leading-relaxed">
              这里展示从原始文本中沉淀出来的事件节点，按时间排序，并保留进入事件详情页继续追踪人物与来源卷宗的入口。
            </p>
          </Panel>

          <Panel className="p-5" tone="info">
            <p className="text-xs font-black uppercase tracking-[0.16em]">事件总数</p>
            <p className="mt-3 text-5xl font-black">{events.length}</p>
            <p className="mt-4 text-sm font-bold leading-relaxed">
              每条事件都可以继续向下钻取到参与人物、来源笔记和时间定位。
            </p>
          </Panel>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <div className="space-y-4">
          {events.map((event) => (
            <Link key={event.id} href={`/events/${event.id}`}>
              <Panel className="p-5 transition-transform hover:-translate-y-1" tone="default">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="border-2 border-ink bg-gold px-2 py-1 text-xs font-black uppercase tracking-[0.12em]">
                    {event.time_text ?? "待校准时间"}
                  </p>
                  <div className="flex flex-wrap gap-2 text-xs font-black uppercase tracking-[0.12em]">
                    {event.location_text ? (
                      <span className="brutal-chip">{event.location_text}</span>
                    ) : null}
                    {event.confidence_score ? (
                      <span className="brutal-chip">
                        {Math.round(event.confidence_score * 100)}%
                      </span>
                    ) : null}
                  </div>
                </div>
                <p className="mt-3 text-3xl font-black">{event.title}</p>
                <p className="mt-3 text-base font-semibold">
                  {event.summary ?? event.description ?? "暂无摘要，进入详情页查看更多事件信息。"}
                </p>
              </Panel>
            </Link>
          ))}
        </div>
      </main>
    </AuthGate>
  );
}
