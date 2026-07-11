"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { apiFetch } from "@/lib/api";

type CollectionItem = { id: string; item_type: string; item_id: string; label: string; subtitle: string | null; href: string; sort_order: number; curator_note: string | null };
type Story = { title: string | null; summary: string | null; body: string | null; style: string };
type CollectionDetail = { id: string; title: string; description: string | null; collection_type: string; status: string; item_count: number; story: Story; items: CollectionItem[] };
type TimelineItem = { event_id: string; title: string; summary: string | null; display_time: string | null; sort_time: string | null; location_text: string | null; curator_note: string | null; href: string };

export default function CollectionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [collectionId, setCollectionId] = useState("");
  const [collection, setCollection] = useState<CollectionDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [itemType, setItemType] = useState("note");
  const [itemId, setItemId] = useState("");
  const [curatorNote, setCuratorNote] = useState("");
  const [story, setStory] = useState<Story>({ title: "", summary: "", body: "", style: "documentary" });
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => { params.then((value) => setCollectionId(value.id)); }, [params]);

  const load = useCallback(async () => {
    if (!collectionId) return;
    try {
      const [detail, timelineData] = await Promise.all([
        apiFetch<CollectionDetail>(`/collections/${collectionId}`),
        apiFetch<{ items: TimelineItem[] }>(`/collections/${collectionId}/timeline`),
      ]);
      setCollection(detail);
      setTimeline(timelineData.items);
      setStory(detail.story);
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "专题加载失败");
    }
  }, [collectionId]);

  useEffect(() => { void load(); }, [load]);

  async function addItem(event: FormEvent) {
    event.preventDefault();
    setBusy("item");
    try {
      await apiFetch(`/collections/${collectionId}/items`, { method: "POST", body: JSON.stringify({ item_type: itemType, item_id: itemId, curator_note: curatorNote || null }) });
      setItemId("");
      setCuratorNote("");
      setMessage("材料已加入专题。");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "材料加入失败");
    } finally { setBusy(""); }
  }

  async function removeItem(id: string) {
    setBusy(id);
    try {
      await apiFetch(`/collections/${collectionId}/items/${id}`, { method: "DELETE" });
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "材料移除失败");
    } finally { setBusy(""); }
  }

  async function saveStory(event: FormEvent) {
    event.preventDefault();
    setBusy("story");
    try {
      const result = await apiFetch<Story>(`/collections/${collectionId}/story`, { method: "PUT", body: JSON.stringify(story) });
      setStory(result);
      setMessage("故事编排已保存。");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "故事保存失败");
    } finally { setBusy(""); }
  }

  async function compileStory() {
    setBusy("compile");
    try {
      const result = await apiFetch<Story>(`/collections/${collectionId}/story/compile`, { method: "POST" });
      setStory(result);
      setMessage("已按专题材料重新编排故事草稿。");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "故事编排失败");
    } finally { setBusy(""); }
  }

  async function exportCollection(format: "markdown" | "json") {
    setBusy(`export-${format}`);
    try {
      const result = await apiFetch<{ filename: string; mime_type: string; content: string }>(`/collections/${collectionId}/export?format=${format}`);
      const url = URL.createObjectURL(new Blob([result.content], { type: result.mime_type }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = result.filename;
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage(`已生成 ${result.filename}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "导出失败");
    } finally { setBusy(""); }
  }

  return (
    <AuthGate>
      <main className="space-y-5">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div><div className="flex flex-wrap items-center gap-3"><h1 className="workbench-title">{collection?.title || "专题载入中"}</h1>{collection ? <span className="workbench-stamp bg-gold">{collection.item_count} 项</span> : null}</div><p className="workbench-lede">{collection?.description || "组织材料、人物、事件与图谱视角，形成可交付叙事。"}</p></div>
            <Link href="/collections" className="tool-action bg-canvas">返回专题列表</Link>
          </div>
        </section>
        {error ? <div className="border-4 border-ink bg-ember p-4 font-bold text-red-950">{error}</div> : null}
        {message ? <button type="button" onClick={() => setMessage("")} className="w-full border-4 border-ink bg-aqua p-3 text-left font-bold shadow-brutal">{message}</button> : null}

        <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <form onSubmit={addItem} className="border-4 border-ink bg-bone p-4 shadow-brutal">
              <h2 className="text-xl font-black">收录知识对象</h2>
              <p className="mt-1 text-sm font-bold text-muted">对象仍保留在各自真源表中，专题只保存引用、顺序与策展备注。</p>
              <div className="mt-4 grid gap-3">
                <select value={itemType} onChange={(event) => setItemType(event.target.value)} className="brutal-input">
                  <option value="note">笔记</option><option value="raw_asset">原始素材</option><option value="entity">人物 / 实体</option><option value="event">事件</option><option value="graph_viewpoint">保存视角</option>
                </select>
                <input required value={itemId} onChange={(event) => setItemId(event.target.value)} className="brutal-input" placeholder="对象 ID" />
                <textarea value={curatorNote} onChange={(event) => setCuratorNote(event.target.value)} className="brutal-input min-h-20" placeholder="为什么收录、在叙事中承担什么作用" />
                <button disabled={busy === "item"} className="brutal-action brutal-action-primary disabled:opacity-50">加入专题</button>
              </div>
            </form>
            <div className="space-y-3">
              {(collection?.items ?? []).map((item) => (
                <article key={item.id} className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft">
                  <div className="flex items-start justify-between gap-3"><div><span className="brutal-chip">{item.item_type}</span><Link href={item.href} className="mt-3 block text-lg font-black underline decoration-2">{item.label}</Link><p className="mt-2 text-sm font-bold text-muted">{item.curator_note || item.subtitle || "暂无策展备注"}</p></div><button type="button" disabled={busy === item.id} onClick={() => removeItem(item.id)} className="tool-action bg-ember">移除</button></div>
                </article>
              ))}
              {collection && !collection.items.length ? <div className="empty-state">专题尚未收录材料。</div> : null}
            </div>
          </div>

          <div className="space-y-5">
            <section className="border-4 border-ink bg-white p-5 shadow-brutal">
              <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="section-kicker">策展时间线</p><h2 className="mt-2 text-2xl font-black">按 canonical 事件时间排序</h2></div><span className="workbench-stamp bg-peach">{timeline.length} 个节点</span></div>
              <div className="mt-5 space-y-3">
                {timeline.map((item, index) => <Link key={item.event_id} href={item.href} className="block border-l-4 border-ink bg-bone p-4"><p className="text-xs font-black">{String(index + 1).padStart(2, "0")} · {item.display_time || "时间待考"}</p><p className="mt-1 text-lg font-black">{item.title}</p><p className="mt-1 text-sm font-bold text-muted">{item.curator_note || item.summary || item.location_text || "暂无摘要"}</p></Link>)}
                {!timeline.length ? <p className="text-sm font-bold text-muted">加入事件后，这里会形成专题时间线。</p> : null}
              </div>
            </section>

            <form onSubmit={saveStory} className="border-4 border-ink bg-gold p-5 shadow-brutal">
              <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="section-kicker">故事编排</p><h2 className="mt-2 text-2xl font-black">专题叙事稿</h2></div><button type="button" onClick={compileStory} disabled={busy === "compile"} className="tool-action bg-neon">按材料生成草稿</button></div>
              <div className="mt-4 grid gap-3">
                <input value={story.title ?? ""} onChange={(event) => setStory((current) => ({ ...current, title: event.target.value }))} className="brutal-input" placeholder="故事标题" />
                <textarea value={story.summary ?? ""} onChange={(event) => setStory((current) => ({ ...current, summary: event.target.value }))} className="brutal-input min-h-20" placeholder="导语" />
                <textarea value={story.body ?? ""} onChange={(event) => setStory((current) => ({ ...current, body: event.target.value }))} className="brutal-input min-h-72 font-mono text-sm" placeholder="支持 Markdown 的故事正文" />
                <select value={story.style} onChange={(event) => setStory((current) => ({ ...current, style: event.target.value }))} className="brutal-input"><option value="documentary">纪实</option><option value="briefing">简报</option><option value="chunibyo">风格化故事</option></select>
                <div className="flex flex-wrap gap-2"><button disabled={busy === "story"} className="brutal-action brutal-action-primary">保存编排</button><button type="button" onClick={() => exportCollection("markdown")} className="tool-action bg-canvas">导出 Markdown</button><button type="button" onClick={() => exportCollection("json")} className="tool-action bg-canvas">导出 JSON</button></div>
              </div>
            </form>
          </div>
        </section>
      </main>
    </AuthGate>
  );
}
