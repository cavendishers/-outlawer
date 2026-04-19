"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, startTransition, useEffect, useMemo, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type EventCurationContext = {
  event: {
    id: string;
    title: string;
    summary: string | null;
    description: string | null;
    event_type: string | null;
    status: string;
    start_time: string | null;
    end_time: string | null;
    time_precision: string | null;
    time_text: string | null;
    timeline_sort_time: string | null;
    location_text: string | null;
    source_note_id: string | null;
    source_note_title: string | null;
    confidence_score: number | null;
  };
  participants: Array<{
    id: string;
    display_name: string;
    entity_type: string;
    role: string | null;
    relation_type: string;
    confidence_score: number | null;
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
  stats: {
    participant_count: number;
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
  "occurs_before",
  "occurs_after",
  "source_of",
  "located_in",
  "blocks",
  "supports",
];

function toInputDateTime(value: string | null): string {
  if (!value) return "";
  return value.slice(0, 16);
}

function optionLabelForEvent(event: EventOption): string {
  return [event.time_text, event.event_type, event.title].filter(Boolean).join(" / ");
}

export default function EventCurationPage() {
  const params = useParams<{ id: string }>();
  const eventId = params?.id;
  const [context, setContext] = useState<EventCurationContext | null>(null);
  const [entities, setEntities] = useState<EntityOption[]>([]);
  const [events, setEvents] = useState<EventOption[]>([]);
  const [notes, setNotes] = useState<NoteOption[]>([]);
  const [eventForm, setEventForm] = useState({
    title: "",
    summary: "",
    description: "",
    event_type: "",
    status: "active",
    time_precision: "unknown",
    time_text: "",
    location_text: "",
    start_time: "",
    end_time: "",
    timeline_sort_time: "",
  });
  const [participantForm, setParticipantForm] = useState({
    entity_id: "",
    role: "参与者",
    relation_type: "participates_in",
  });
  const [relationForm, setRelationForm] = useState({
    direction: "outgoing",
    related_type: "event",
    related_id: "",
    relation_type: "related_to",
  });
  const [editingRelationId, setEditingRelationId] = useState("");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!eventId) return;
    Promise.all([
      apiFetch<EventCurationContext>(`/curation/events/${eventId}`),
      apiFetch<{ items: EntityOption[] }>("/entities?page_size=100"),
      apiFetch<{ items: EventOption[] }>("/events?page_size=100"),
      apiFetch<{ items: NoteOption[] }>("/notes?page_size=100"),
    ])
      .then(([contextData, entityData, eventData, noteData]) => {
        startTransition(() => {
          setContext(contextData);
          setEntities(entityData.items);
          setEvents(eventData.items);
          setNotes(noteData.items);
          setEventForm({
            title: contextData.event.title,
            summary: contextData.event.summary ?? "",
            description: contextData.event.description ?? "",
            event_type: contextData.event.event_type ?? "",
            status: contextData.event.status ?? "active",
            time_precision: contextData.event.time_precision ?? "unknown",
            time_text: contextData.event.time_text ?? "",
            location_text: contextData.event.location_text ?? "",
            start_time: toInputDateTime(contextData.event.start_time),
            end_time: toInputDateTime(contextData.event.end_time),
            timeline_sort_time: toInputDateTime(contextData.event.timeline_sort_time),
          });
          setError("");
        });
      })
      .catch((err) => {
        startTransition(() => {
          setError(err instanceof Error ? err.message : "事件校对上下文加载失败");
        });
      });
  }, [eventId]);

  const relatedOptions = useMemo(() => {
    if (relationForm.related_type === "entity") {
      return entities.map((entity) => ({
        id: entity.id,
        label: `${entity.display_name} / ${entity.entity_type}`,
      }));
    }
    if (relationForm.related_type === "note") {
      return notes.map((note) => ({
        id: note.id,
        label: [note.primary_time?.slice(0, 10), note.title].filter(Boolean).join(" / "),
      }));
    }
    return events
      .filter((event) => event.id !== eventId)
      .map((event) => ({
        id: event.id,
        label: optionLabelForEvent(event),
      }));
  }, [entities, eventId, events, notes, relationForm.related_type]);

  async function refreshContext() {
    if (!eventId) return;
    const data = await apiFetch<EventCurationContext>(`/curation/events/${eventId}`);
    startTransition(() => {
      setContext(data);
      setEventForm((current) => ({
        ...current,
        title: data.event.title,
        summary: data.event.summary ?? "",
        description: data.event.description ?? "",
        event_type: data.event.event_type ?? "",
        status: data.event.status ?? "active",
        time_precision: data.event.time_precision ?? "unknown",
        time_text: data.event.time_text ?? "",
        location_text: data.event.location_text ?? "",
        start_time: toInputDateTime(data.event.start_time),
        end_time: toInputDateTime(data.event.end_time),
        timeline_sort_time: toInputDateTime(data.event.timeline_sort_time),
      }));
    });
  }

  async function handleEventSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!eventId) return;
    setBusy("event");
    try {
      await apiFetch(`/curation/events/${eventId}`, {
        method: "PATCH",
        body: JSON.stringify(eventForm),
      });
      await refreshContext();
      startTransition(() => {
        setMessage("事件字段已保存，并同步更新时间线投影。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "事件保存失败");
      });
    } finally {
      setBusy("");
    }
  }

  async function handleParticipantSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!eventId || !participantForm.entity_id) return;
    setBusy("participant");
    try {
      await apiFetch(`/curation/events/${eventId}/participants`, {
        method: "POST",
        body: JSON.stringify(participantForm),
      });
      await refreshContext();
      startTransition(() => {
        setMessage("参与人物已更新。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "参与人物保存失败");
      });
    } finally {
      setBusy("");
    }
  }

  async function removeParticipant(entityId: string) {
    if (!eventId || !window.confirm("确认移除这个参与人物吗？")) return;
    setBusy(`participant-${entityId}`);
    try {
      await apiFetch(`/curation/events/${eventId}/participants/${entityId}`, { method: "DELETE" });
      await refreshContext();
      startTransition(() => {
        setMessage("参与人物已移除。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "移除参与人物失败");
      });
    } finally {
      setBusy("");
    }
  }

  async function handleRelationSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!eventId || !relationForm.related_id) return;
    setBusy("relation");
    try {
      await apiFetch(
        editingRelationId ? `/curation/events/${eventId}/relations/${editingRelationId}` : `/curation/events/${eventId}/relations`,
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
          related_type: "event",
          related_id: "",
          relation_type: "related_to",
        });
        setMessage(editingRelationId ? "图谱关系已更新。" : "图谱关系已写入。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : editingRelationId ? "图谱关系更新失败" : "图谱关系保存失败");
      });
    } finally {
      setBusy("");
    }
  }

  function beginRelationEdit(relation: EventCurationContext["relations"][number]) {
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
        related_type: "event",
        related_id: "",
        relation_type: "related_to",
      });
    });
  }

  async function removeRelation(relationId: string) {
    if (!eventId || !window.confirm("确认删除这条图谱关系吗？")) return;
    setBusy(`relation-${relationId}`);
    try {
      await apiFetch(`/curation/events/${eventId}/relations/${relationId}`, { method: "DELETE" });
      await refreshContext();
      startTransition(() => {
        if (editingRelationId === relationId) {
          setEditingRelationId("");
          setRelationForm({
            direction: "outgoing",
            related_type: "event",
            related_id: "",
            relation_type: "related_to",
          });
        }
        setMessage("图谱关系已删除。");
        setError("");
      });
    } catch (err) {
      startTransition(() => {
        setError(err instanceof Error ? err.message : "删除图谱关系失败");
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
            <p className="text-sm font-black uppercase tracking-[0.2em]">Graph Curation</p>
            <h1 className="mt-3 font-display text-[clamp(2.4rem,5vw,4.8rem)] leading-[0.9]">
              {context?.event.title ?? "事件校对台"}
            </h1>
            <p className="mt-4 max-w-3xl text-lg font-bold leading-relaxed">
              这里用于修正 AI 抽取后的事件字段、参与人物和额外图谱关系。原始素材不会被覆盖，修改只作用于结构化知识层。
            </p>
            {context?.event.id ? (
              <Link href={`/events/${context.event.id}`} className="brutal-action brutal-action-secondary mt-6">
                返回事件详情
              </Link>
            ) : null}
          </Panel>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <Panel className="p-5" tone="info">
              <p className="text-xs font-black uppercase tracking-[0.16em]">参与人物</p>
              <p className="mt-3 text-5xl font-black">{context?.stats.participant_count ?? 0}</p>
            </Panel>
            <Panel className="p-5" tone="signal">
              <p className="text-xs font-black uppercase tracking-[0.16em]">额外关系</p>
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

        <Panel className="p-6 md:p-8" tone="default">
          <form className="space-y-5" onSubmit={handleEventSubmit}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-black uppercase tracking-[0.16em]">事件字段校对</p>
              <button
                type="submit"
                disabled={busy === "event"}
                className="brutal-action brutal-action-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                保存事件字段
              </button>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <label className="block text-xs font-black uppercase tracking-[0.16em]">
                标题
                <input
                  value={eventForm.title}
                  onChange={(event) => setEventForm((current) => ({ ...current, title: event.target.value }))}
                  className="brutal-input mt-2 w-full text-base normal-case tracking-normal"
                />
              </label>
              <label className="block text-xs font-black uppercase tracking-[0.16em]">
                地点
                <input
                  value={eventForm.location_text}
                  onChange={(event) => setEventForm((current) => ({ ...current, location_text: event.target.value }))}
                  className="brutal-input mt-2 w-full text-base normal-case tracking-normal"
                />
              </label>
              <label className="block text-xs font-black uppercase tracking-[0.16em]">
                类型
                <input
                  value={eventForm.event_type}
                  onChange={(event) => setEventForm((current) => ({ ...current, event_type: event.target.value }))}
                  className="brutal-input mt-2 w-full text-base normal-case tracking-normal"
                />
              </label>
              <label className="block text-xs font-black uppercase tracking-[0.16em]">
                状态
                <input
                  value={eventForm.status}
                  onChange={(event) => setEventForm((current) => ({ ...current, status: event.target.value }))}
                  className="brutal-input mt-2 w-full text-base normal-case tracking-normal"
                />
              </label>
              <label className="block text-xs font-black uppercase tracking-[0.16em]">
                时间文本
                <input
                  value={eventForm.time_text}
                  onChange={(event) => setEventForm((current) => ({ ...current, time_text: event.target.value }))}
                  className="brutal-input mt-2 w-full text-base normal-case tracking-normal"
                />
              </label>
              <label className="block text-xs font-black uppercase tracking-[0.16em]">
                时间精度
                <select
                  value={eventForm.time_precision}
                  onChange={(event) => setEventForm((current) => ({ ...current, time_precision: event.target.value }))}
                  className="brutal-input mt-2 w-full text-base normal-case tracking-normal"
                >
                  <option value="unknown">unknown</option>
                  <option value="year">year</option>
                  <option value="month">month</option>
                  <option value="day">day</option>
                  <option value="time">time</option>
                </select>
              </label>
              <label className="block text-xs font-black uppercase tracking-[0.16em]">
                开始时间
                <input
                  type="datetime-local"
                  value={eventForm.start_time}
                  onChange={(event) => setEventForm((current) => ({ ...current, start_time: event.target.value }))}
                  className="brutal-input mt-2 w-full text-base normal-case tracking-normal"
                />
              </label>
              <label className="block text-xs font-black uppercase tracking-[0.16em]">
                结束时间
                <input
                  type="datetime-local"
                  value={eventForm.end_time}
                  onChange={(event) => setEventForm((current) => ({ ...current, end_time: event.target.value }))}
                  className="brutal-input mt-2 w-full text-base normal-case tracking-normal"
                />
              </label>
              <label className="block text-xs font-black uppercase tracking-[0.16em]">
                时间线排序时间
                <input
                  type="datetime-local"
                  value={eventForm.timeline_sort_time}
                  onChange={(event) => setEventForm((current) => ({ ...current, timeline_sort_time: event.target.value }))}
                  className="brutal-input mt-2 w-full text-base normal-case tracking-normal"
                />
              </label>
            </div>

            <label className="block text-xs font-black uppercase tracking-[0.16em]">
              摘要
              <textarea
                value={eventForm.summary}
                onChange={(event) => setEventForm((current) => ({ ...current, summary: event.target.value }))}
                className="brutal-input mt-2 min-h-28 w-full text-base normal-case tracking-normal"
              />
            </label>
            <label className="block text-xs font-black uppercase tracking-[0.16em]">
              描述
              <textarea
                value={eventForm.description}
                onChange={(event) => setEventForm((current) => ({ ...current, description: event.target.value }))}
                className="brutal-input mt-2 min-h-40 w-full text-base normal-case tracking-normal"
              />
            </label>
          </form>
        </Panel>

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel className="p-6" tone="info">
            <p className="text-sm font-black uppercase tracking-[0.16em]">新增 / 更新参与人物</p>
            <form className="mt-5 space-y-4" onSubmit={handleParticipantSubmit}>
              <select
                value={participantForm.entity_id}
                onChange={(event) => setParticipantForm((current) => ({ ...current, entity_id: event.target.value }))}
                className="brutal-input w-full text-base"
              >
                <option value="">选择人物或实体</option>
                {entities.map((entity) => (
                  <option key={entity.id} value={entity.id}>
                    {entity.display_name} / {entity.entity_type}
                  </option>
                ))}
              </select>
              <input
                value={participantForm.role}
                onChange={(event) => setParticipantForm((current) => ({ ...current, role: event.target.value }))}
                className="brutal-input w-full text-base"
                placeholder="角色，例如：负责人、参与者、见证者"
              />
              <input
                value={participantForm.relation_type}
                onChange={(event) => setParticipantForm((current) => ({ ...current, relation_type: event.target.value }))}
                className="brutal-input w-full text-base"
                placeholder="关系类型，例如：participates_in"
              />
              <button
                type="submit"
                disabled={busy === "participant"}
                className="brutal-action brutal-action-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                写入参与关系
              </button>
            </form>
          </Panel>

          <Panel className="p-6" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.16em]">当前参与人物</p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {(context?.participants ?? []).map((participant) => (
                <Panel key={participant.id} className="p-5" tone="default">
                  <p className="text-xs font-black uppercase tracking-[0.16em]">{participant.entity_type}</p>
                  <p className="mt-3 text-2xl font-black">{participant.display_name}</p>
                  <p className="mt-3 text-sm font-bold">{participant.role || participant.relation_type}</p>
                  <button
                    type="button"
                    disabled={busy === `participant-${participant.id}`}
                    className="brutal-action mt-5 border-ember bg-ember text-sm disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={() => removeParticipant(participant.id)}
                  >
                    移除
                  </button>
                </Panel>
              ))}
              {context && context.participants.length === 0 ? (
                <div className="surface-inset border-4 border-dashed border-ink p-5 text-base font-bold">
                  当前事件还没有参与人物。
                </div>
              ) : null}
            </div>
          </Panel>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel className="p-6" tone="story">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-black uppercase tracking-[0.16em]">
                {editingRelationId ? "编辑图谱关系" : "新增图谱关系"}
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
                  <option value="outgoing">当前事件指向对象</option>
                  <option value="incoming">对象指向当前事件</option>
                </select>
                <select
                  value={relationForm.related_type}
                  onChange={(event) =>
                    setRelationForm((current) => ({ ...current, related_type: event.target.value, related_id: "" }))
                  }
                  className="brutal-input w-full text-base"
                >
                  <option value="event">事件</option>
                  <option value="entity">实体</option>
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
                {editingRelationId ? "保存关系修改" : "写入图谱关系"}
              </button>
            </form>
          </Panel>

          <Panel className="p-6" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.16em]">当前额外关系</p>
            <div className="mt-5 space-y-4">
              {(context?.relations ?? []).map((relation) => (
                <Panel key={relation.id} className="p-5" tone="default">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-black uppercase tracking-[0.16em]">
                        {relation.direction === "outgoing" ? "事件 -> 对象" : "对象 -> 事件"}
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
                  当前事件没有额外图谱关系。参与人物关系会在上方单独维护。
                </div>
              ) : null}
            </div>
          </Panel>
        </section>
      </main>
    </AuthGate>
  );
}
