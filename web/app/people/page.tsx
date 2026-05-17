"use client";

import { useDeferredValue, useEffect, useState } from "react";
import Link from "next/link";

import { AuthGate } from "@/components/auth-gate";
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
      <main className="space-y-4">
        <section className="workbench-header">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="workbench-title">人物索引</h1>
                <span className="workbench-stamp bg-aqua">{peopleEntities.length} 人</span>
                {normalizedQuery ? (
                  <span className="workbench-stamp bg-canvas">{filteredEntities.length} 命中</span>
                ) : null}
              </div>
              <p className="workbench-lede">
                扫名字、别名和角色注释，进入人物档案查看时间线与相关事件。
              </p>
            </div>
            <Link href="/inbox" className="tool-action bg-neon">
              导入
            </Link>
          </div>
        </section>

        <section className="border-4 border-ink bg-bone px-4 py-3 shadow-brutal">
          <label className="sr-only" htmlFor="people-query">快速检索</label>
          <input
            id="people-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="w-full border-2 border-ink bg-canvas px-3 py-2 text-base font-bold outline-none focus:border-4"
            placeholder="按名字、别名、类型搜索人物"
          />
        </section>

        {error ? (
          <div className="border-4 border-ink bg-ember p-5 text-lg font-bold text-red-950 shadow-brutal">
            {error}
          </div>
        ) : null}

        {filteredEntities.length ? (
          <section className="space-y-3">
            {filteredEntities.map((entity) => (
              <Link key={entity.id} href={`/story/entity/${entity.id}`} className="block">
                <article className="group dense-record md:grid-cols-[12rem_1fr]">
                  <div className="dense-record-side bg-aqua">
                    <p className="text-xs font-black tracking-[0.12em]">人物</p>
                    <p className="mt-3 text-lg font-black leading-tight">{entity.display_name}</p>
                  </div>
                  <div className="dense-record-body">
                    <div className="min-w-0">
                      <p className="dense-record-title">{entity.canonical_name || entity.display_name}</p>
                      <p className="dense-record-summary">
                        {entity.description || "暂无角色注释，等待后续卷宗补足设定。"}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className="brutal-chip">{entity.entity_type}</span>
                        {(entity.aliases ?? []).slice(0, 2).map((alias) => (
                          <span key={alias} className="brutal-chip">
                            {alias}
                          </span>
                        ))}
                        {entity.confidence_score ? (
                          <span className="brutal-chip">置信度 {Math.round(entity.confidence_score * 100)}%</span>
                        ) : null}
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
          </section>
        ) : (
          <div className="empty-state">
            当前没有可展示的人物索引。先去导入一条文本卷宗，或者换一个检索词试试。
          </div>
        )}
      </main>
    </AuthGate>
  );
}
