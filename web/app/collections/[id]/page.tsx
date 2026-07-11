"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { apiFetch } from "@/lib/api";

type CollectionItem = {
  id: string;
  item_type: string;
  item_id: string;
  label: string;
  subtitle: string | null;
  href: string;
  sort_order: number;
  curator_note: string | null;
  has_evidence: boolean;
};
type CollectionCandidate = { item_type: string; item_id: string; label: string; subtitle: string | null; meta: string | null; href: string };
type Story = { title: string | null; summary: string | null; body: string | null; style: string };
type CollectionStats = { total: number; by_type: Record<string, number>; evidence_eligible_count: number; evidence_linked_count: number; evidence_coverage: number };
type CollectionDetail = { id: string; title: string; description: string | null; collection_type: string; status: string; item_count: number; story: Story; stats: CollectionStats; items: CollectionItem[] };
type TimelineItem = { event_id: string; title: string; summary: string | null; display_time: string | null; sort_time: string | null; location_text: string | null; curator_note: string | null; href: string };

const ITEM_TYPE_LABELS: Record<string, string> = { note: "笔记", raw_asset: "原始素材", entity: "人物 / 实体", event: "事件", graph_viewpoint: "保存视角" };

export default function CollectionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [collectionId, setCollectionId] = useState("");
  const [collection, setCollection] = useState<CollectionDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [candidateType, setCandidateType] = useState("note");
  const [candidateQuery, setCandidateQuery] = useState("");
  const [candidates, setCandidates] = useState<CollectionCandidate[]>([]);
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<string[]>([]);
  const [curatorNote, setCuratorNote] = useState("");
  const [selectedItemIds, setSelectedItemIds] = useState<string[]>([]);
  const [itemFilter, setItemFilter] = useState("all");
  const [evidenceOnly, setEvidenceOnly] = useState(false);
  const [bulkConfirm, setBulkConfirm] = useState(false);
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
      setSelectedItemIds((current) => current.filter((id) => detail.items.some((item) => item.id === id)));
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "专题加载失败");
    }
  }, [collectionId]);

  const searchCandidates = useCallback(async () => {
    if (!collectionId) return;
    setBusy("candidates");
    try {
      const query = new URLSearchParams({ item_type: candidateType, page_size: "30" });
      if (candidateQuery.trim()) query.set("q", candidateQuery.trim());
      const data = await apiFetch<{ items: CollectionCandidate[] }>(`/collections/${collectionId}/candidates?${query.toString()}`);
      setCandidates(data.items);
      setSelectedCandidateIds([]);
      setError("");
    } catch (caught) {
      setCandidates([]);
      setError(caught instanceof Error ? caught.message : "可选知识对象加载失败");
    } finally {
      setBusy("");
    }
  }, [candidateQuery, candidateType, collectionId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void searchCandidates(); }, [collectionId, candidateType]);

  const visibleItems = useMemo(
    () => (collection?.items ?? []).filter((item) => (itemFilter === "all" || item.item_type === itemFilter) && (!evidenceOnly || item.has_evidence)),
    [collection?.items, evidenceOnly, itemFilter],
  );

  async function addSelected(event: FormEvent) {
    event.preventDefault();
    const selected = candidates.filter((item) => selectedCandidateIds.includes(item.item_id));
    if (!selected.length) { setError("请先选择至少一个知识对象。"); return; }
    setBusy("item");
    try {
      for (const item of selected) {
        await apiFetch(`/collections/${collectionId}/items`, { method: "POST", body: JSON.stringify({ item_type: item.item_type, item_id: item.item_id, curator_note: curatorNote || null }) });
      }
      setCuratorNote("");
      setSelectedCandidateIds([]);
      setMessage(`已加入 ${selected.length} 项材料。`);
      await Promise.all([load(), searchCandidates()]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "材料加入失败");
    } finally { setBusy(""); }
  }

  async function moveItem(itemId: string, direction: -1 | 1) {
    if (!collection) return;
    const ids = collection.items.map((item) => item.id);
    const index = ids.indexOf(itemId);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    setBusy(`order-${itemId}`);
    try {
      await apiFetch(`/collections/${collectionId}/items/order`, { method: "PUT", body: JSON.stringify({ item_ids: ids }) });
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "成员顺序更新失败");
    } finally { setBusy(""); }
  }

  async function bulkRemove() {
    if (!selectedItemIds.length) return;
    setBusy("bulk-remove");
    try {
      await apiFetch(`/collections/${collectionId}/items/bulk-remove`, { method: "POST", body: JSON.stringify({ item_ids: selectedItemIds }) });
      setMessage(`已移除 ${selectedItemIds.length} 项材料。`);
      setSelectedItemIds([]);
      setBulkConfirm(false);
      await Promise.all([load(), searchCandidates()]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "批量移除失败");
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
    } catch (caught) { setError(caught instanceof Error ? caught.message : "故事保存失败"); }
    finally { setBusy(""); }
  }

  async function compileStory() {
    setBusy("compile");
    try {
      const result = await apiFetch<Story>(`/collections/${collectionId}/story/compile`, { method: "POST" });
      setStory(result);
      setMessage("已按专题材料重新编排故事草稿。");
      await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "故事编排失败"); }
    finally { setBusy(""); }
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
    } catch (caught) { setError(caught instanceof Error ? caught.message : "导出失败"); }
    finally { setBusy(""); }
  }

  return (
    <AuthGate>
      <main className="space-y-5">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div><div className="flex flex-wrap items-center gap-3"><h1 className="workbench-title">{collection?.title || "专题载入中"}</h1>{collection ? <span className="workbench-stamp bg-gold">{collection.item_count} 项</span> : null}</div><p className="workbench-lede">{collection?.description || "组织材料、人物、事件与图谱视角，形成可交付叙事。"}</p></div>
            <div className="flex flex-wrap gap-2"><Link href={`/graph?collection_id=${collectionId}`} className="tool-action bg-aqua">专题图谱</Link><Link href="/collections" className="tool-action bg-canvas">返回专题列表</Link></div>
          </div>
        </section>
        {collection ? <CollectionStatsStrip stats={collection.stats} /> : null}
        {error ? <button type="button" onClick={() => setError("")} className="w-full border-4 border-ink bg-ember p-4 text-left font-bold text-red-950">{error}</button> : null}
        {message ? <button type="button" onClick={() => setMessage("")} className="w-full border-4 border-ink bg-aqua p-3 text-left font-bold shadow-brutal">{message}</button> : null}

        <section className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-4">
            <form onSubmit={addSelected} className="border-4 border-ink bg-bone p-4 shadow-brutal">
              <h2 className="text-xl font-black">搜索并收录知识对象</h2>
              <p className="mt-1 text-sm font-bold text-muted">按名称和摘要选择材料，不再需要复制 UUID；对象仍保留在各自真源表中。</p>
              <div className="mt-4 grid gap-3 md:grid-cols-[10rem_1fr_auto]">
                <select value={candidateType} onChange={(event) => setCandidateType(event.target.value)} className="brutal-input">{Object.entries(ITEM_TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
                <input value={candidateQuery} onChange={(event) => setCandidateQuery(event.target.value)} className="brutal-input" placeholder="搜索名称、标题或摘要" />
                <button type="button" onClick={() => void searchCandidates()} className="tool-action bg-aqua">{busy === "candidates" ? "搜索中…" : "搜索"}</button>
              </div>
              <div className="mt-3 max-h-72 space-y-2 overflow-y-auto">
                {candidates.map((item) => {
                  const selected = selectedCandidateIds.includes(item.item_id);
                  return <button key={`${item.item_type}-${item.item_id}`} type="button" onClick={() => setSelectedCandidateIds((current) => selected ? current.filter((id) => id !== item.item_id) : [...current, item.item_id])} className={`w-full border-2 border-ink p-3 text-left ${selected ? "bg-neon" : "bg-canvas"}`}><div className="flex items-start justify-between gap-3"><div><p className="font-black">{item.label}</p><p className="mt-1 text-xs font-bold text-muted">{item.subtitle || "暂无摘要"}</p></div><span className="brutal-chip">{item.meta || ITEM_TYPE_LABELS[item.item_type]}</span></div></button>;
                })}
                {!candidates.length && busy !== "candidates" ? <p className="border-2 border-dashed border-ink p-3 text-sm font-bold text-muted">没有更多可加入的对象。</p> : null}
              </div>
              <textarea value={curatorNote} onChange={(event) => setCuratorNote(event.target.value)} className="brutal-input mt-3 min-h-20 w-full" placeholder="为什么收录、在叙事中承担什么作用" />
              <button disabled={busy === "item" || !selectedCandidateIds.length} className="brutal-action brutal-action-primary mt-3 w-full disabled:opacity-50">加入已选 {selectedCandidateIds.length || ""} 项</button>
            </form>

            <section className="border-4 border-ink bg-white p-4 shadow-brutal">
              <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="section-kicker">专题成员</p><h2 className="mt-1 text-xl font-black">筛选、排序与批量管理</h2></div><span className="brutal-chip">已选 {selectedItemIds.length}</span></div>
              <div className="mt-3 flex flex-wrap gap-2"><select value={itemFilter} onChange={(event) => setItemFilter(event.target.value)} className="brutal-input"><option value="all">全部类型</option>{Object.entries(ITEM_TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><label className="flex items-center gap-2 border-2 border-ink bg-canvas px-3 py-2 text-sm font-black"><input type="checkbox" checked={evidenceOnly} onChange={(event) => setEvidenceOnly(event.target.checked)} />仅看有证据</label>{selectedItemIds.length ? bulkConfirm ? <><button type="button" onClick={bulkRemove} className="tool-action bg-ember">确认移除 {selectedItemIds.length} 项</button><button type="button" onClick={() => setBulkConfirm(false)} className="tool-action bg-canvas">取消</button></> : <button type="button" onClick={() => setBulkConfirm(true)} className="tool-action bg-ember">批量移除</button> : null}</div>
            </section>

            <div className="space-y-3">
              {visibleItems.map((item) => {
                const index = collection?.items.findIndex((row) => row.id === item.id) ?? -1;
                return <article key={item.id} className="border-4 border-ink bg-canvas p-4 shadow-brutalSoft"><div className="flex items-start gap-3"><input type="checkbox" checked={selectedItemIds.includes(item.id)} onChange={(event) => setSelectedItemIds((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} aria-label={`选择 ${item.label}`} className="mt-1 size-5" /><div className="min-w-0 flex-1"><div className="flex flex-wrap gap-2"><span className="brutal-chip">{ITEM_TYPE_LABELS[item.item_type] ?? item.item_type}</span>{item.has_evidence ? <span className="brutal-chip bg-aqua">有证据</span> : null}</div><Link href={item.href} className="mt-3 block text-lg font-black underline decoration-2">{item.label}</Link><p className="mt-2 text-sm font-bold text-muted">{item.curator_note || item.subtitle || "暂无策展备注"}</p></div><div className="flex flex-col gap-2"><button type="button" disabled={index <= 0 || Boolean(busy)} onClick={() => moveItem(item.id, -1)} className="tool-action bg-canvas disabled:opacity-40">上移</button><button type="button" disabled={!collection || index >= collection.items.length - 1 || Boolean(busy)} onClick={() => moveItem(item.id, 1)} className="tool-action bg-canvas disabled:opacity-40">下移</button></div></div></article>;
              })}
              {collection && !visibleItems.length ? <div className="empty-state">当前筛选条件下没有专题成员。</div> : null}
            </div>
          </div>

          <div className="space-y-5">
            <section className="border-4 border-ink bg-white p-5 shadow-brutal">
              <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="section-kicker">策展时间线</p><h2 className="mt-2 text-2xl font-black">按 canonical 事件时间排序</h2></div><span className="workbench-stamp bg-peach">{timeline.length} 个节点</span></div>
              <div className="mt-5 space-y-3">{timeline.map((item, index) => <Link key={item.event_id} href={item.href} className="block border-l-4 border-ink bg-bone p-4"><p className="text-xs font-black">{String(index + 1).padStart(2, "0")} · {item.display_time || "时间待考"}</p><p className="mt-1 text-lg font-black">{item.title}</p><p className="mt-1 text-sm font-bold text-muted">{item.curator_note || item.summary || item.location_text || "暂无摘要"}</p></Link>)}{!timeline.length ? <p className="text-sm font-bold text-muted">加入事件后，这里会形成专题时间线。</p> : null}</div>
            </section>

            <form onSubmit={saveStory} className="border-4 border-ink bg-gold p-5 shadow-brutal">
              <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="section-kicker">故事编排</p><h2 className="mt-2 text-2xl font-black">专题叙事稿</h2></div><button type="button" onClick={compileStory} disabled={busy === "compile"} className="tool-action bg-neon">按材料生成草稿</button></div>
              {collection && (timeline.length === 0 || collection.stats.evidence_coverage < 1) ? <div className="mt-4 border-2 border-ink bg-canvas p-3 text-sm font-bold">导出检查：{timeline.length === 0 ? "尚无事件时间线；" : ""}{collection.stats.evidence_eligible_count && collection.stats.evidence_coverage < 1 ? `仍有 ${collection.stats.evidence_eligible_count - collection.stats.evidence_linked_count} 个知识对象缺少手工证据。` : ""}</div> : null}
              <div className="mt-4 grid gap-3"><input value={story.title ?? ""} onChange={(event) => setStory((current) => ({ ...current, title: event.target.value }))} className="brutal-input" placeholder="故事标题" /><textarea value={story.summary ?? ""} onChange={(event) => setStory((current) => ({ ...current, summary: event.target.value }))} className="brutal-input min-h-20" placeholder="导语" /><textarea value={story.body ?? ""} onChange={(event) => setStory((current) => ({ ...current, body: event.target.value }))} className="brutal-input min-h-72 font-mono text-sm" placeholder="支持 Markdown 的故事正文" /><select value={story.style} onChange={(event) => setStory((current) => ({ ...current, style: event.target.value }))} className="brutal-input"><option value="documentary">纪实</option><option value="briefing">简报</option><option value="chunibyo">风格化故事</option></select><div className="flex flex-wrap gap-2"><button disabled={busy === "story"} className="brutal-action brutal-action-primary">保存编排</button><button type="button" onClick={() => exportCollection("markdown")} className="tool-action bg-canvas">导出 Markdown</button><button type="button" onClick={() => exportCollection("json")} className="tool-action bg-canvas">导出 JSON</button></div></div>
            </form>
          </div>
        </section>
      </main>
    </AuthGate>
  );
}

function CollectionStatsStrip({ stats }: { stats: CollectionStats }) {
  const labels = Object.entries(stats.by_type).map(([type, count]) => `${ITEM_TYPE_LABELS[type] ?? type} ${count}`).join(" · ") || "尚无材料";
  return <section className="grid gap-3 md:grid-cols-3"><div className="metric-card bg-canvas"><p className="section-kicker">成员构成</p><p className="mt-3 text-sm font-black">{labels}</p></div><div className="metric-card bg-aqua"><p className="section-kicker">证据覆盖</p><p className="mt-3 text-3xl font-black">{Math.round(stats.evidence_coverage * 100)}%</p></div><div className="metric-card bg-gold"><p className="section-kicker">已绑定证据</p><p className="mt-3 text-3xl font-black">{stats.evidence_linked_count}/{stats.evidence_eligible_count}</p></div></section>;
}
