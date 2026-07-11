"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { apiFetch } from "@/lib/api";

type CreatedResult = { label: string; routes: Record<string, string> };

export default function ManualKnowledgePage() {
  const [kind, setKind] = useState<"entity" | "event">("entity");
  const [name, setName] = useState("");
  const [subtype, setSubtype] = useState("");
  const [description, setDescription] = useState("");
  const [eventTime, setEventTime] = useState("");
  const [noteId, setNoteId] = useState("");
  const [assetId, setAssetId] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<CreatedResult | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setCreated(null);
    const evidence = noteId.trim()
      ? { note_id: noteId.trim(), excerpt: excerpt.trim() || null }
      : assetId.trim()
        ? { raw_asset_id: assetId.trim(), excerpt: excerpt.trim() || null }
        : null;
    try {
      if (kind === "entity") {
        const result = await apiFetch<{ entity: { display_name: string }; routes: Record<string, string> }>("/entities", {
          method: "POST",
          body: JSON.stringify({
            canonical_name: name,
            display_name: name,
            entity_type: subtype || "person",
            description: description || null,
            evidence,
          }),
        });
        setCreated({ label: result.entity.display_name, routes: result.routes });
      } else {
        const result = await apiFetch<{ event: { title: string }; routes: Record<string, string> }>("/events", {
          method: "POST",
          body: JSON.stringify({
            title: name,
            event_type: subtype || null,
            summary: description || null,
            description: description || null,
            start_time: eventTime ? new Date(eventTime).toISOString() : null,
            timeline_sort_time: eventTime ? new Date(eventTime).toISOString() : null,
            time_precision: eventTime ? "exact" : "unknown",
            evidence,
          }),
        });
        setCreated({ label: result.event.title, routes: result.routes });
      }
      setName("");
      setDescription("");
      setEventTime("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "手工知识创建失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthGate>
      <main className="space-y-5">
        <section className="workbench-header">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="workbench-title">手工知识创建</h1>
              <p className="workbench-lede">无需再次运行抽取，直接补充缺失人物或事件，并可绑定现有笔记、原始素材作为证据。</p>
            </div>
            <Link href="/graph" className="tool-action bg-aqua">从图谱创建并连接</Link>
          </div>
        </section>

        <form onSubmit={handleSubmit} className="border-4 border-ink bg-bone p-5 shadow-brutal">
          <div className="flex flex-wrap gap-2">
            {(["entity", "event"] as const).map((value) => (
              <button key={value} type="button" onClick={() => setKind(value)} className={`tool-action ${kind === value ? "bg-neon" : "bg-canvas"}`}>
                {value === "entity" ? "创建人物 / 实体" : "创建事件"}
              </button>
            ))}
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <Field label={kind === "entity" ? "规范名称" : "事件标题"}>
              <input required value={name} onChange={(event) => setName(event.target.value)} className="brutal-input" placeholder={kind === "entity" ? "例如：张三" : "例如：项目复盘会"} />
            </Field>
            <Field label={kind === "entity" ? "实体类型" : "事件类型"}>
              <input value={subtype} onChange={(event) => setSubtype(event.target.value)} className="brutal-input" placeholder={kind === "entity" ? "person" : "meeting"} />
            </Field>
            {kind === "event" ? (
              <Field label="发生时间">
                <input type="datetime-local" value={eventTime} onChange={(event) => setEventTime(event.target.value)} className="brutal-input" />
              </Field>
            ) : null}
            <Field label="说明" wide>
              <textarea value={description} onChange={(event) => setDescription(event.target.value)} className="brutal-input min-h-28" placeholder="记录为什么需要手工补充，以及已知事实。" />
            </Field>
          </div>

          <div className="mt-5 border-2 border-ink bg-canvas p-4">
            <p className="font-black">可选证据来源</p>
            <p className="mt-1 text-sm font-bold text-muted">填写笔记 ID 或原始素材 ID，二者只选一个；系统只建立证据引用，不修改来源内容。</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <input value={noteId} onChange={(event) => { setNoteId(event.target.value); if (event.target.value) setAssetId(""); }} className="brutal-input" placeholder="笔记 ID" />
              <input value={assetId} onChange={(event) => { setAssetId(event.target.value); if (event.target.value) setNoteId(""); }} className="brutal-input" placeholder="原始素材 ID" />
              <textarea value={excerpt} onChange={(event) => setExcerpt(event.target.value)} className="brutal-input min-h-20 md:col-span-2" placeholder="证据摘录或定位说明" />
            </div>
          </div>

          {error ? <p className="mt-4 border-2 border-ink bg-ember p-3 font-bold text-red-950">{error}</p> : null}
          {created ? (
            <div className="mt-4 border-2 border-ink bg-aqua p-4 font-bold">
              已创建：{created.label}
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(created.routes).map(([label, href]) => <Link key={label} href={href} className="tool-action bg-canvas">{routeLabel(label)}</Link>)}
              </div>
            </div>
          ) : null}
          <button disabled={busy} className="brutal-action brutal-action-primary mt-5 disabled:opacity-50">{busy ? "创建中…" : "创建并写入审计"}</button>
        </form>
      </main>
    </AuthGate>
  );
}

function Field({ label, wide = false, children }: { label: string; wide?: boolean; children: ReactNode }) {
  return <label className={`block ${wide ? "md:col-span-2" : ""}`}><span className="mb-2 block text-sm font-black">{label}</span>{children}</label>;
}

function routeLabel(value: string) {
  return ({ detail: "查看详情", curation: "继续校对", graph: "图谱定位", timeline: "打开时间线" } as Record<string, string>)[value] ?? value;
}
