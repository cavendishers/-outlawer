"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";

type CollectionOption = { id: string; title: string; collection_type: string; item_count: number };

export function AddToCollectionControl({
  itemType,
  itemId,
  label,
  className = "",
}: {
  itemType: "note" | "raw_asset" | "entity" | "event" | "graph_viewpoint";
  itemId: string;
  label: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [collections, setCollections] = useState<CollectionOption[]>([]);
  const [collectionId, setCollectionId] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function toggle() {
    const nextOpen = !open;
    setOpen(nextOpen);
    setMessage("");
    setError("");
    if (!nextOpen || collections.length) return;
    try {
      const data = await apiFetch<{ items: CollectionOption[] }>("/collections?page_size=100");
      setCollections(data.items);
      setCollectionId(data.items[0]?.id ?? "");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "专题列表加载失败");
    }
  }

  async function add() {
    if (!collectionId) return;
    setBusy(true);
    setError("");
    try {
      await apiFetch(`/collections/${collectionId}/items`, {
        method: "POST",
        body: JSON.stringify({ item_type: itemType, item_id: itemId, curator_note: `从“${label}”快捷加入` }),
      });
      setMessage("已加入专题。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加入专题失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`relative ${className}`}>
      <button type="button" onClick={toggle} className="tool-action bg-gold">加入专题</button>
      {open ? (
        <div className="absolute right-0 z-30 mt-2 w-72 border-4 border-ink bg-paper p-3 text-left shadow-brutal">
          <p className="text-sm font-black">将“{label}”加入</p>
          {collections.length ? (
            <div className="mt-3 space-y-2">
              <select value={collectionId} onChange={(event) => setCollectionId(event.target.value)} className="brutal-input w-full">
                {collections.map((item) => <option key={item.id} value={item.id}>{item.title} · {item.item_count} 项</option>)}
              </select>
              <button type="button" onClick={add} disabled={busy || !collectionId} className="brutal-action brutal-action-primary w-full disabled:opacity-50">{busy ? "加入中…" : "确认加入"}</button>
            </div>
          ) : <p className="mt-3 text-sm font-bold text-muted">暂无专题，请先到“专题 / 案件”创建。</p>}
          {message ? <p className="mt-2 border-2 border-ink bg-aqua p-2 text-sm font-bold">{message}</p> : null}
          {error ? <p className="mt-2 border-2 border-ink bg-ember p-2 text-sm font-bold text-red-950">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
