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
        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <Panel className="p-6 md:p-8" tone="quiet">
            <p className="page-kicker">Timeline Projection</p>
            <h1 className="page-title mt-3">时间线 / 图谱视野</h1>
            <p className="page-lede">
              把零散记录压成一条可阅读的时间轨。每个时间点都能继续跳向事件详情，追溯上下文与参与者。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/graph" className="brutal-action brutal-action-primary text-lg">
                进入图谱工作台
              </Link>
            </div>
          </Panel>

          <Panel className="metric-card" tone="info" intensity="quiet">
            <p className="section-kicker">图谱节点</p>
            <p className="mt-3 text-5xl font-black">{overview?.nodes.length ?? items.length}</p>
            <p className="body-copy mt-4">
              当前总览把近期事件和高频人物压进同一张网里，便于先看结构，再回到具体卷宗。
            </p>
          </Panel>
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

        <div className="space-y-4">
          {items.map((item) => {
            const card = (
              <div className="grid gap-4 md:grid-cols-[160px_1fr]">
                <Panel className="flex items-center justify-center p-4 text-center text-lg font-black" tone="time" intensity="quiet">
                  {item.display_time ?? "未校时"}
                </Panel>
                <Panel className="relative overflow-hidden p-5" tone="quiet" intensity="quiet">
                  <div className="absolute inset-y-0 left-0 w-3 bg-ink" />
                  <div className="pl-4">
                    <p className="meta-copy">
                      {item.event_id ? "事件节点" : "笔记节点"}
                    </p>
                    <p className="mt-3 text-3xl font-black">{item.title}</p>
                    <p className="body-copy mt-3">{item.summary ?? "暂无补充摘要。"}</p>
                  </div>
                </Panel>
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
