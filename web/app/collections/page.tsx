"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { apiFetch } from "@/lib/api";

type Collection = { id: string; title: string; description: string | null; collection_type: string; status: string; item_count: number; updated_at: string | null };

export default function CollectionsPage() {
  const [items, setItems] = useState<Collection[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [collectionType, setCollectionType] = useState("topic");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const data = await apiFetch<{ items: Collection[] }>("/collections");
      setItems(data.items);
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "专题列表加载失败");
    }
  }

  useEffect(() => { void load(); }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await apiFetch("/collections", { method: "POST", body: JSON.stringify({ title, description: description || null, collection_type: collectionType }) });
      setTitle("");
      setDescription("");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "专题创建失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthGate>
      <main className="space-y-5">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div><h1 className="workbench-title">专题 / 案件集合</h1><p className="workbench-lede">把笔记、素材、人物、事件和图谱视角放进同一工作集，再编排时间线与故事输出。</p></div>
            <span className="workbench-stamp bg-gold">{items.length} 个集合</span>
          </div>
        </section>
        <form onSubmit={create} className="grid gap-3 border-4 border-ink bg-bone p-4 shadow-brutal md:grid-cols-[1fr_10rem_auto]">
          <input required value={title} onChange={(event) => setTitle(event.target.value)} className="brutal-input" placeholder="专题或案件名称" />
          <select value={collectionType} onChange={(event) => setCollectionType(event.target.value)} className="brutal-input"><option value="topic">专题</option><option value="case">案件</option></select>
          <button disabled={busy} className="brutal-action brutal-action-primary disabled:opacity-50">{busy ? "创建中…" : "创建集合"}</button>
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} className="brutal-input min-h-20 md:col-span-3" placeholder="范围、问题意识或编排说明" />
        </form>
        {error ? <div className="border-4 border-ink bg-ember p-4 font-bold text-red-950">{error}</div> : null}
        <section className="grid gap-4 lg:grid-cols-2">
          {items.map((item) => (
            <Link key={item.id} href={`/collections/${item.id}`} className="border-4 border-ink bg-canvas p-5 shadow-brutal transition-transform hover:-translate-y-1">
              <div className="flex flex-wrap items-center justify-between gap-2"><span className="workbench-stamp bg-aqua">{item.collection_type === "case" ? "案件" : "专题"}</span><span className="brutal-chip">{item.item_count} 项材料</span></div>
              <h2 className="mt-4 text-2xl font-black">{item.title}</h2>
              <p className="mt-2 font-bold leading-relaxed text-muted">{item.description || "尚未填写专题说明。"}</p>
            </Link>
          ))}
        </section>
        {!items.length && !error ? <div className="empty-state">尚无专题集合。先创建一个工作集，再收录知识对象。</div> : null}
      </main>
    </AuthGate>
  );
}
