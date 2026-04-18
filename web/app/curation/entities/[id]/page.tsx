"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, startTransition, useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type EntityCurationContext = {
  entity: {
    id: string;
    entity_type: string;
    canonical_name: string;
    display_name: string;
    description: string | null;
    aliases: string[];
    confidence_score: number | null;
    status: string;
    first_seen_at: string | null;
    last_seen_at: string | null;
  };
  aliases: Array<{
    id: string;
    alias: string;
    normalized_alias: string;
    alias_type: string;
    created_at: string | null;
  }>;
  related_events: Array<{
    id: string;
    title: string;
    summary: string | null;
    time_text: string | null;
    event_type: string | null;
    location_text: string | null;
    role: string | null;
    relation_type: string | null;
  }>;
  timeline_fragments: Array<{
    event_id: string;
    title: string;
    summary: string | null;
    time_text: string | null;
    event_type: string | null;
    location_text: string | null;
    role: string | null;
    relation_type: string | null;
    chapter_label: string;
    source_note_title: string | null;
    position: number;
    total: number;
  }>;
  stats: {
    alias_count: number;
    related_event_count: number;
    related_note_count: number;
  };
};

function toInputDateTime(value: string | null): string {
  if (!value) return "";
  return value.slice(0, 16);
}

export default function EntityCurationPage() {
  const params = useParams<{ id: string }>();
  const entityId = params?.id;
  const [context, setContext] = useState<EntityCurationContext | null>(null);
  const [entityForm, setEntityForm] = useState({
    entity_type: "person",
    canonical_name: "",
    display_name: "",
    description: "",
    status: "active",
    first_seen_at: "",
    last_seen_at: "",
  });
  const [aliasInput, setAliasInput] = useState("");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!entityId) return;
    apiFetch<EntityCurationContext>(`/curation/entities/${entityId}`)
      .then((data) => {
        startTransition(() => {
          setContext(data);
          setEntityForm({
            entity_type: data.entity.entity_type,
            canonical_name: data.entity.canonical_name,
            display_name: data.entity.display_name,
            description: data.entity.description ?? "",
            status: data.entity.status,
            first_seen_at: toInputDateTime(data.entity.first_seen_at),
            last_seen_at: toInputDateTime(data.entity.last_seen_at),
          });
          setError("");
        });
      })
      .catch((err) => {
        startTransition(() => {
          setContext(null);
          setError(err instanceof Error ? err.message : "实体校对上下文加载失败");
        });
      });
  }, [entityId]);

  async function refreshContext() {
    if (!entityId) return;
    const data = await apiFetch<EntityCurationContext>(`/curation/entities/${entityId}`);
    startTransition(() => {
      setContext(data);
      setEntityForm({
        entity_type: data.entity.entity_type,
        canonical_name: data.entity.canonical_name,
        display_name: data.entity.display_name,
        description: data.entity.description ?? "",
        status: data.entity.status,
        first_seen_at: toInputDateTime(data.entity.first_seen_at),
        last_seen_at: toInputDateTime(data.entity.last_seen_at),
      });
    });
  }

  async function handleEntitySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!entityId) return;
    setBusy("entity");
    try {
      await apiFetch(`/curation/entities/${entityId}`, {
        method: "PATCH",
        body: JSON.stringify(entityForm),
      });
      await refreshContext();
      startTransition(() => {
        setMessage("人物档案字段已保存。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "实体字段保存失败");
      });
    } finally {
      setBusy("");
    }
  }

  async function handleAliasSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!entityId || !aliasInput.trim()) return;
    setBusy("alias");
    try {
      await apiFetch(`/curation/entities/${entityId}/aliases`, {
        method: "POST",
        body: JSON.stringify({ alias: aliasInput.trim(), alias_type: "manual" }),
      });
      setAliasInput("");
      await refreshContext();
      startTransition(() => {
        setMessage("别名已登记到人物档案。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "别名保存失败");
      });
    } finally {
      setBusy("");
    }
  }

  async function removeAlias(aliasId: string) {
    if (!entityId || !window.confirm("确认删除这个别名吗？")) return;
    setBusy(`alias-${aliasId}`);
    try {
      await apiFetch(`/curation/entities/${entityId}/aliases/${aliasId}`, {
        method: "DELETE",
      });
      await refreshContext();
      startTransition(() => {
        setMessage("别名已移除。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "删除别名失败");
      });
    } finally {
      setBusy("");
    }
  }

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <Panel className="p-6 md:p-8" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.2em]">Entity Curation</p>
            <h1 className="mt-3 font-display text-[clamp(2.4rem,5vw,4.8rem)] leading-[0.9]">
              {context?.entity.display_name ?? "人物校对台"}
            </h1>
            <p className="mt-4 text-lg font-bold leading-relaxed">
              在这里手动修正人物节点的命名、身份、说明和别名，让后续时间线、故事页和事件图谱都引用同一份可信档案。
            </p>
          </Panel>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <Panel className="p-5" tone="info">
              <p className="text-xs font-black uppercase tracking-[0.16em]">关联事件</p>
              <p className="mt-3 text-5xl font-black">{context?.stats.related_event_count ?? 0}</p>
            </Panel>
            <Panel className="p-5" tone="signal">
              <p className="text-xs font-black uppercase tracking-[0.16em]">可信别名</p>
              <p className="mt-3 text-5xl font-black">{context?.stats.alias_count ?? 0}</p>
              <p className="mt-3 text-sm font-bold leading-relaxed">
                同步影响人物页、搜索与后续审核判断。
              </p>
            </Panel>
          </div>
        </section>

        {message ? (
          <Panel className="p-5 text-lg font-bold" tone="success">
            {message}
          </Panel>
        ) : null}

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <Panel className="p-6" tone="default">
            <div className="flex flex-wrap gap-3">
              {context ? (
                <>
                  <Link href={`/story/entity/${context.entity.id}`} className="brutal-action brutal-action-secondary">
                    查看人物故事页
                  </Link>
                  <Link href={`/review/entities/${context.entity.id}`} className="brutal-action brutal-action-info">
                    返回审核页
                  </Link>
                </>
              ) : null}
            </div>

            <form className="mt-6 grid gap-4 md:grid-cols-2" onSubmit={handleEntitySubmit}>
              <div className="md:col-span-2">
                <label htmlFor="display_name" className="text-xs font-black uppercase tracking-[0.16em]">
                  显示名
                </label>
                <input
                  id="display_name"
                  value={entityForm.display_name}
                  onChange={(event) => setEntityForm((current) => ({ ...current, display_name: event.target.value }))}
                  className="brutal-input mt-2 w-full text-lg font-semibold"
                />
              </div>

              <div>
                <label htmlFor="canonical_name" className="text-xs font-black uppercase tracking-[0.16em]">
                  规范名
                </label>
                <input
                  id="canonical_name"
                  value={entityForm.canonical_name}
                  onChange={(event) => setEntityForm((current) => ({ ...current, canonical_name: event.target.value }))}
                  className="brutal-input mt-2 w-full text-lg font-semibold"
                />
              </div>

              <div>
                <label htmlFor="entity_type" className="text-xs font-black uppercase tracking-[0.16em]">
                  类型
                </label>
                <input
                  id="entity_type"
                  value={entityForm.entity_type}
                  onChange={(event) => setEntityForm((current) => ({ ...current, entity_type: event.target.value }))}
                  className="brutal-input mt-2 w-full text-lg font-semibold"
                  placeholder="person / organization / place"
                />
              </div>

              <div>
                <label htmlFor="status" className="text-xs font-black uppercase tracking-[0.16em]">
                  状态
                </label>
                <input
                  id="status"
                  value={entityForm.status}
                  onChange={(event) => setEntityForm((current) => ({ ...current, status: event.target.value }))}
                  className="brutal-input mt-2 w-full text-lg font-semibold"
                />
              </div>

              <div>
                <label htmlFor="first_seen_at" className="text-xs font-black uppercase tracking-[0.16em]">
                  初次出现
                </label>
                <input
                  id="first_seen_at"
                  type="datetime-local"
                  value={entityForm.first_seen_at}
                  onChange={(event) => setEntityForm((current) => ({ ...current, first_seen_at: event.target.value }))}
                  className="brutal-input mt-2 w-full text-lg font-semibold"
                />
              </div>

              <div>
                <label htmlFor="last_seen_at" className="text-xs font-black uppercase tracking-[0.16em]">
                  最近出现
                </label>
                <input
                  id="last_seen_at"
                  type="datetime-local"
                  value={entityForm.last_seen_at}
                  onChange={(event) => setEntityForm((current) => ({ ...current, last_seen_at: event.target.value }))}
                  className="brutal-input mt-2 w-full text-lg font-semibold"
                />
              </div>

              <div className="md:col-span-2">
                <label htmlFor="description" className="text-xs font-black uppercase tracking-[0.16em]">
                  说明
                </label>
                <textarea
                  id="description"
                  value={entityForm.description}
                  onChange={(event) => setEntityForm((current) => ({ ...current, description: event.target.value }))}
                  className="brutal-input mt-2 min-h-32 w-full text-base font-semibold"
                  placeholder="补充更可信的人物设定、身份说明或上下文。"
                />
              </div>

              <div className="md:col-span-2 flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={busy === "entity"}
                  className="brutal-action brutal-action-primary disabled:cursor-not-allowed disabled:opacity-60"
                >
                  保存人物档案
                </button>
              </div>
            </form>
          </Panel>

          <Panel className="p-6" tone="info">
            <p className="text-sm font-black uppercase tracking-[0.16em]">别名治理</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {(context?.aliases ?? []).map((alias) => (
                <button
                  key={alias.id}
                  type="button"
                  onClick={() => removeAlias(alias.id)}
                  disabled={busy === `alias-${alias.id}`}
                  className="brutal-chip disabled:cursor-not-allowed disabled:opacity-60"
                  title="点击移除这个别名"
                >
                  {alias.alias}
                </button>
              ))}
              {context && context.aliases.length === 0 ? (
                <p className="text-base font-bold">当前没有已确认别名。</p>
              ) : null}
            </div>

            <form className="mt-6 space-y-3" onSubmit={handleAliasSubmit}>
              <label htmlFor="alias" className="text-xs font-black uppercase tracking-[0.16em]">
                新增可信别名
              </label>
              <input
                id="alias"
                value={aliasInput}
                onChange={(event) => setAliasInput(event.target.value)}
                className="brutal-input w-full text-lg font-semibold"
                placeholder="输入角色别名、简称或译名"
              />
              <button
                type="submit"
                disabled={busy === "alias"}
                className="brutal-action brutal-action-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                写入别名
              </button>
            </form>

            <div className="mt-6 text-sm font-bold leading-relaxed">
              别名只会更新实体档案与检索线索，不会覆盖原始卷宗。人物故事页仍然使用独立的衍生视图。
            </div>
          </Panel>
        </section>

        <Panel className="p-6" tone="story">
          <p className="text-sm font-black uppercase tracking-[0.16em]">人物时间线片段</p>
          <div className="mt-5 space-y-4">
            {(context?.timeline_fragments ?? []).map((fragment) => (
              <Link key={fragment.event_id} href={`/events/${fragment.event_id}`} className="block transition-transform hover:-translate-y-1">
                <div className="grid gap-4 lg:grid-cols-[180px_1fr]">
                  <div className="border-4 border-ink bg-gold p-4">
                    <p className="text-xs font-black uppercase tracking-[0.16em]">{fragment.chapter_label}</p>
                    <p className="mt-4 text-2xl font-black">{fragment.time_text ?? "待校时"}</p>
                  </div>
                  <Panel className="p-5" tone="default">
                    <div className="flex flex-wrap gap-2">
                      {fragment.role ? <span className="brutal-chip">{fragment.role}</span> : null}
                      {fragment.event_type ? <span className="brutal-chip">{fragment.event_type}</span> : null}
                      {fragment.location_text ? <span className="brutal-chip">{fragment.location_text}</span> : null}
                    </div>
                    <p className="mt-4 text-2xl font-black">{fragment.title}</p>
                    <p className="mt-3 text-sm font-bold leading-relaxed">{fragment.summary ?? "暂无摘要。"}</p>
                  </Panel>
                </div>
              </Link>
            ))}
            {context && context.timeline_fragments.length === 0 ? (
              <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
                当前人物还没有时间线片段，后续事件挂接后会在这里长出连续轨迹。
              </div>
            ) : null}
          </div>
        </Panel>

        <Panel className="p-6" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.16em]">关联事件速览</p>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {(context?.related_events ?? []).map((item) => (
              <Link key={item.id} href={`/events/${item.id}`}>
                <Panel className="h-full p-5 transition-transform hover:-translate-y-1" tone="default">
                  <div className="flex flex-wrap gap-2">
                    {item.time_text ? <span className="brutal-chip">{item.time_text}</span> : null}
                    {item.role ? <span className="brutal-chip">{item.role}</span> : null}
                    {item.location_text ? <span className="brutal-chip">{item.location_text}</span> : null}
                  </div>
                  <p className="mt-4 text-2xl font-black">{item.title}</p>
                  <p className="mt-3 text-sm font-bold leading-relaxed">{item.summary ?? "暂无摘要。"}</p>
                </Panel>
              </Link>
            ))}
            {context && context.related_events.length === 0 ? (
              <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
                当前人物还没有关联事件可供校验。
              </div>
            ) : null}
          </div>
        </Panel>
      </main>
    </AuthGate>
  );
}
