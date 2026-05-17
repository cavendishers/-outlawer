"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AuthGate } from "@/components/auth-gate";
import { GraphOverviewCanvas } from "@/components/graph-overview-canvas";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type TimelineItem = {
  id: string;
  event_id: string | null;
  note_id: string | null;
  title: string;
  summary: string | null;
  display_time: string | null;
};

type GraphOverview = {
  stats: {
    event_count: number;
    entity_count: number;
    timeline_count: number;
    edge_count: number;
  };
  nodes: Array<{
    id: string;
    node_type: string;
    label: string;
    subtitle: string;
    href: string;
    importance: number;
    meta: string[];
  }>;
  edges: Array<{
    source_id: string;
    target_id: string;
    edge_type: string;
    label: string;
    weight: number;
  }>;
  timeline_focus: TimelineItem[];
};

export default function TimelinePage() {
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [overview, setOverview] = useState<GraphOverview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch<{ items: TimelineItem[] }>("/timeline"),
      apiFetch<GraphOverview>("/timeline/overview"),
    ])
      .then(([timelineData, overviewData]) => {
        setItems(timelineData.items);
        setOverview(overviewData);
        setError("");
      })
      .catch((err) => {
        setItems([]);
        setOverview(null);
        setError(err instanceof Error ? err.message : "时间线加载失败");
      });
  }, []);

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="workbench-header">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="workbench-title">时间线 / 图谱</h1>
                <span className="workbench-stamp bg-gold">{items.length} 段</span>
                <span className="workbench-stamp bg-aqua">{overview?.nodes.length ?? 0} 节点</span>
              </div>
              <p className="workbench-lede">
                先看时间骨架，再进入图谱工作台追人物和事件关系。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/graph" className="tool-action bg-neon">
                工作台
              </Link>
            </div>
          </div>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        {overview ? (
          <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
            <Panel className="p-6 md:p-8" tone="quiet" intensity="quiet">
              <p className="section-kicker">全局图谱画布</p>
              <div className="mt-5">
                <GraphOverviewCanvas
                  title="近期事件网络"
                  nodes={overview.nodes}
                  edges={overview.edges}
                />
              </div>
            </Panel>

            <div className="space-y-4">
              <Panel className="metric-card" tone="time" intensity="quiet">
                <p className="section-kicker">事件节点</p>
                <p className="mt-3 text-5xl font-black">{overview.stats.event_count}</p>
              </Panel>
              <Panel className="metric-card" tone="info" intensity="quiet">
                <p className="section-kicker">人物节点</p>
                <p className="mt-3 text-5xl font-black">{overview.stats.entity_count}</p>
              </Panel>
              <Panel className="metric-card" tone="quiet" intensity="quiet">
                <p className="section-kicker">关系连线</p>
                <p className="mt-3 text-5xl font-black">{overview.stats.edge_count}</p>
                <p className="body-copy mt-4">
                  实线表示人物参与事件，虚线表示事件与事件之间的关联。
                </p>
              </Panel>
            </div>
          </section>
        ) : null}

        <div className="space-y-3">
          {items.map((item) => {
            const card = (
              <div className="group dense-record md:grid-cols-[12rem_1fr]">
                <div className="dense-record-side bg-gold">
                  <p className="text-xs font-black tracking-[0.12em]">时间</p>
                  <p className="mt-3 text-lg font-black leading-tight">
                  {item.display_time ?? "未校时"}
                  </p>
                </div>
                <div className="dense-record-body">
                  <div className="min-w-0">
                    <p className="dense-record-title">{item.title}</p>
                    <p className="dense-record-summary">{item.summary ?? "暂无补充摘要。"}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="brutal-chip">{item.event_id ? "事件节点" : "笔记节点"}</span>
                    </div>
                  </div>
                  <div className="flex items-start justify-start md:justify-end">
                    <span className="border-2 border-ink bg-canvas px-3 py-2 text-sm font-black shadow-brutalTiny">
                      查看
                    </span>
                  </div>
                </div>
              </div>
            );

            return item.event_id ? (
              <Link key={item.id} href={`/events/${item.event_id}`} className="block transition-transform hover:-translate-y-1">
                {card}
              </Link>
            ) : (
              <div key={item.id}>{card}</div>
            );
          })}
        </div>
      </main>
    </AuthGate>
  );
}
