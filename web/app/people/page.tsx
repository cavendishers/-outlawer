"use client";

import { useDeferredValue, useEffect, useState } from "react";
import Link from "next/link";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type EntityItem = {
  id: string;
  display_name: string;
  canonical_name: string;
  entity_type: string;
  description?: string | null;
  aliases?: string[];
  confidence_score?: number | null;
};

export default function PeoplePage() {
  const [entities, setEntities] = useState<EntityItem[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    apiFetch<{ items: EntityItem[] }>("/entities")
      .then((data) => {
        setEntities(data.items);
        setError("");
      })
      .catch((err) => {
        setEntities([]);
        setError(err instanceof Error ? err.message : "人物索引加载失败");
      });
  }, []);

  const peopleEntities = entities.filter((entity) => entity.entity_type === "person");
  const normalizedQuery = deferredQuery.trim().toLowerCase();
  const filteredEntities = peopleEntities.filter((entity) => {
    if (!normalizedQuery) return true;
    return [
      entity.display_name,
      entity.canonical_name,
      entity.entity_type,
      ...(entity.aliases ?? []),
    ]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(normalizedQuery));
  });

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <Panel className="p-6 md:p-8" tone="quiet">
            <p className="page-kicker">People Index</p>
            <h1 className="page-title mt-3">人物索引</h1>
            <p className="page-lede">
              把输入文本中的人物、组织与关键称号汇成名册。这里优先展示可追踪、可跳转、可继续编排的角色节点。
            </p>
          </Panel>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <Panel className="metric-card" tone="info" intensity="quiet">
              <p className="section-kicker">已识别角色</p>
              <p className="mt-3 text-5xl font-black">{peopleEntities.length}</p>
            </Panel>
            <Panel className="metric-card" tone="quiet" intensity="quiet">
              <p className="section-kicker">当前筛选结果</p>
              <p className="mt-3 text-5xl font-black">{filteredEntities.length}</p>
            </Panel>
          </div>
        </section>

        <Panel className="p-5" tone="quiet" intensity="quiet">
          <label className="section-kicker" htmlFor="people-query">
            快速检索
          </label>
          <input
            id="people-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="brutal-input mt-3 w-full text-lg font-semibold"
            placeholder="按名字、别名、类型搜索人物"
          />
        </Panel>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        {filteredEntities.length ? (
          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
            {filteredEntities.map((entity) => (
              <Link key={entity.id} href={`/story/entity/${entity.id}`}>
                <article className="dossier-card">
                  <div className="dossier-card-content flex h-full flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between gap-4">
                      <p className="meta-copy">{entity.entity_type}</p>
                      {entity.confidence_score ? (
                        <p className="meta-copy">
                          {Math.round(entity.confidence_score * 100)}%
                        </p>
                      ) : null}
                    </div>
                    <p className="mt-4 text-3xl font-black leading-tight">{entity.display_name}</p>
                    <p className="mt-2 text-base font-semibold text-muted">{entity.canonical_name}</p>
                    <p className="body-copy mt-4 min-h-12">
                      {entity.description || "暂无角色注释，等待后续卷宗补足设定。"}
                    </p>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    {(entity.aliases ?? []).slice(0, 3).map((alias) => (
                      <span key={alias} className="brutal-chip">
                        {alias}
                      </span>
                    ))}
                    <span className="brutal-chip">
                      查看档案
                    </span>
                  </div>
                  </div>
                </article>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            当前没有可展示的人物索引。先去导入一条文本卷宗，或者换一个检索词试试。
          </div>
        )}
      </main>
    </AuthGate>
  );
}
