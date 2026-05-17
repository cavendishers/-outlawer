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
        <section className="workbench-header">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="workbench-title">
                  事件清单
                </h1>
                <span className="workbench-stamp bg-gold">
                  {events.length} 条
                </span>
              </div>
              <p className="workbench-lede">
                扫时间、标题、地点，进入详情再看人物和关系。
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Link href="/inbox" className="tool-action bg-neon">
                导入
              </Link>
              <Link href="/timeline" className="tool-action bg-canvas">
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
              <article className="group dense-record md:grid-cols-[12rem_1fr]">
                <div className="dense-record-side bg-gold">
                  <p className="text-xs font-black tracking-[0.12em]">时间</p>
                  <p className="mt-3 text-lg font-black leading-tight">
                    {event.time_text ?? "待校准"}
                  </p>
                </div>

                <div className="dense-record-body">
                  <div className="min-w-0">
                    <p className="dense-record-title">
                      {event.title}
                    </p>
                    <p className="dense-record-summary">
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
