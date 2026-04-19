"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, startTransition, useEffect, useMemo, useState } from "react";

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
  relations: Array<{
    id: string;
    direction: string;
    relation_type: string;
    peer: {
      id: string;
      object_type: string;
      label: string;
      subtitle: string | null;
      href: string;
    };
    source_type: string;
    source_id: string;
    target_type: string;
    target_id: string;
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
    relation_count: number;
  };
};

type EntityOption = {
  id: string;
  display_name: string;
  entity_type: string;
};

type EventOption = {
  id: string;
  title: string;
  time_text: string | null;
  event_type: string | null;
};

type NoteOption = {
  id: string;
  title: string;
  primary_time: string | null;
  status: string;
};

const relationTypeOptions = [
  "related_to",
  "supports",
  "blocks",
  "source_of",
  "located_in",
  "member_of",
  "mentions",
];

function toInputDateTime(value: string | null): string {
  if (!value) return "";
  return value.slice(0, 16);
}

export default function EntityCurationPage() {
  const params = useParams<{ id: string }>();
  const entityId = params?.id;
  const [context, setContext] = useState<EntityCurationContext | null>(null);
  const [entities, setEntities] = useState<EntityOption[]>([]);
  const [events, setEvents] = useState<EventOption[]>([]);
  const [notes, setNotes] = useState<NoteOption[]>([]);
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
  const [relationForm, setRelationForm] = useState({
    direction: "outgoing",
    related_type: "entity",
    related_id: "",
    relation_type: "related_to",
  });
  const [editingRelationId, setEditingRelationId] = useState("");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!entityId) return;
    Promise.all([
      apiFetch<EntityCurationContext>(`/curation/entities/${entityId}`),
      apiFetch<{ items: EntityOption[] }>("/entities?page_size=100"),
      apiFetch<{ items: EventOption[] }>("/events?page_size=100"),
      apiFetch<{ items: NoteOption[] }>("/notes?page_size=100"),
    ])
      .then(([data, entityData, eventData, noteData]) => {
        startTransition(() => {
          setContext(data);
          setEntities(entityData.items);
          setEvents(eventData.items);
          setNotes(noteData.items);
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

  const relatedOptions = useMemo(() => {
    if (relationForm.related_type === "event") {
      return events.map((event) => ({
        id: event.id,
        label: [event.time_text, event.event_type, event.title].filter(Boolean).join(" / "),
      }));
    }
    if (relationForm.related_type === "note") {
      return notes.map((note) => ({
        id: note.id,
        label: [note.primary_time?.slice(0, 10), note.title].filter(Boolean).join(" / "),
      }));
    }
    return entities
      .filter((entity) => entity.id !== entityId)
      .map((entity) => ({
        id: entity.id,
        label: `${entity.display_name} / ${entity.entity_type}`,
      }));
  }, [entities, entityId, events, notes, relationForm.related_type]);

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

  async function handleRelationSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!entityId || !relationForm.related_id) return;
    setBusy("relation");
    try {
      await apiFetch(
        editingRelationId ? `/curation/entities/${entityId}/relations/${editingRelationId}` : `/curation/entities/${entityId}/relations`,
        {
          method: editingRelationId ? "PATCH" : "POST",
          body: JSON.stringify(relationForm),
        }
      );
      await refreshContext();
      startTransition(() => {
        setEditingRelationId("");
        setRelationForm({
          direction: "outgoing",
          related_type: "entity",
          related_id: "",
          relation_type: "related_to",
        });
        setMessage(editingRelationId ? "人物关系已更新。" : "人物关系已写入。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : editingRelationId ? "人物关系更新失败" : "人物关系保存失败");
      });
    } finally {
      setBusy("");
    }
  }

  function beginRelationEdit(relation: EntityCurationContext["relations"][number]) {
    startTransition(() => {
      setEditingRelationId(relation.id);
      setRelationForm({
        direction: relation.direction,
        related_type: relation.peer.object_type,
        related_id: relation.peer.id,
        relation_type: relation.relation_type,
      });
      setMessage("");
      setError("");
    });
  }

  function cancelRelationEdit() {
    startTransition(() => {
      setEditingRelationId("");
      setRelationForm({
        direction: "outgoing",
        related_type: "entity",
        related_id: "",
        relation_type: "related_to",
      });
    });
  }

  async function removeRelation(relationId: string) {
    if (!entityId || !window.confirm("确认删除这条人物关系吗？")) return;
    setBusy(`relation-${relationId}`);
    try {
      await apiFetch(`/curation/entities/${entityId}/relations/${relationId}`, { method: "DELETE" });
      await refreshContext();
      startTransition(() => {
        if (editingRelationId === relationId) {
          setEditingRelationId("");
          setRelationForm({
            direction: "outgoing",
            related_type: "entity",
            related_id: "",
            relation_type: "related_to",
          });
        }
        setMessage("人物关系已删除。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "删除人物关系失败");
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

          <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
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
            <Panel className="p-5" tone="story">
              <p className="text-xs font-black uppercase tracking-[0.16em]">图谱关系</p>
              <p className="mt-3 text-5xl font-black">{context?.stats.relation_count ?? 0}</p>
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

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel className="p-6" tone="story">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-black uppercase tracking-[0.16em]">
                {editingRelationId ? "编辑人物关系" : "新增人物关系"}
              </p>
              {editingRelationId ? (
                <button type="button" onClick={cancelRelationEdit} className="brutal-action brutal-action-secondary text-sm">
                  取消编辑
                </button>
              ) : null}
            </div>
            <form className="mt-5 space-y-4" onSubmit={handleRelationSubmit}>
              <div className="grid gap-4 md:grid-cols-2">
                <select
                  value={relationForm.direction}
                  onChange={(event) => setRelationForm((current) => ({ ...current, direction: event.target.value }))}
                  className="brutal-input w-full text-base"
                >
                  <option value="outgoing">当前人物指向对象</option>
                  <option value="incoming">对象指向当前人物</option>
                </select>
                <select
                  value={relationForm.related_type}
                  onChange={(event) =>
                    setRelationForm((current) => ({ ...current, related_type: event.target.value, related_id: "" }))
                  }
                  className="brutal-input w-full text-base"
                >
                  <option value="entity">实体</option>
                  <option value="event">事件</option>
                  <option value="note">卷宗</option>
                </select>
              </div>
              <select
                value={relationForm.related_id}
                onChange={(event) => setRelationForm((current) => ({ ...current, related_id: event.target.value }))}
                className="brutal-input w-full text-base"
              >
                <option value="">选择关联对象</option>
                {relatedOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
              <select
                value={relationForm.relation_type}
                onChange={(event) => setRelationForm((current) => ({ ...current, relation_type: event.target.value }))}
                className="brutal-input w-full text-base"
              >
                {relationTypeOptions.map((relationType) => (
                  <option key={relationType} value={relationType}>
                    {relationType}
                  </option>
                ))}
              </select>
              <button
                type="submit"
                disabled={busy === "relation"}
                className="brutal-action brutal-action-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                {editingRelationId ? "保存关系修改" : "写入人物关系"}
              </button>
            </form>
          </Panel>

          <Panel className="p-6" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.16em]">当前图谱关系</p>
            <div className="mt-5 space-y-4">
              {(context?.relations ?? []).map((relation) => (
                <Panel key={relation.id} className="p-5" tone="default">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-black uppercase tracking-[0.16em]">
                        {relation.direction === "outgoing" ? "人物 -> 对象" : "对象 -> 人物"}
                      </p>
                      <p className="mt-3 text-2xl font-black">{relation.peer.label}</p>
                      <p className="mt-2 text-sm font-bold">{relation.relation_type}</p>
                    </div>
                    <span className="brutal-chip">{relation.peer.object_type}</span>
                  </div>
                  <div className="mt-5 flex flex-wrap gap-3">
                    <Link href={relation.peer.href} className="brutal-action brutal-action-secondary text-sm">
                      查看对象
                    </Link>
                    <button
                      type="button"
                      className="brutal-action brutal-action-info text-sm"
                      onClick={() => beginRelationEdit(relation)}
                    >
                      编辑关系
                    </button>
                    <button
                      type="button"
                      disabled={busy === `relation-${relation.id}`}
                      className="brutal-action border-ember bg-ember text-sm disabled:cursor-not-allowed disabled:opacity-60"
                      onClick={() => removeRelation(relation.id)}
                    >
                      删除关系
                    </button>
                  </div>
                </Panel>
              ))}
              {context && context.relations.length === 0 ? (
                <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
                  当前人物还没有额外图谱关系。事件挂接会在时间线和关联事件里单独展示。
                </div>
              ) : null}
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
