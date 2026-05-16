"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { API_BASE, apiFetch, getToken } from "@/lib/api";

type CharacterCard = {
  id: string;
  source_entity_id: string;
  status: string;
  title: string;
  card_format: string;
  card_version: string;
  mode: string;
  spec_json: {
    data?: Record<string, unknown>;
    [key: string]: unknown;
  };
  source_snapshot_json: Record<string, unknown>;
  avatar_asset_id: string | null;
  avatar_url: string | null;
  role_image_asset_id: string | null;
  role_image_url: string | null;
  export_asset_id: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type CardData = {
  name?: string;
  description?: string;
  personality?: string;
  scenario?: string;
  first_mes?: string;
  mes_example?: string;
  creator_notes?: string;
  system_prompt?: string;
  post_history_instructions?: string;
  alternate_greetings?: string[];
  tags?: string[];
  character_book?: {
    entries?: Array<{
      id?: number;
      keys?: string[];
      comment?: string;
      content?: string;
      enabled?: boolean;
    }>;
  };
};

const editableFields: Array<{ key: keyof CardData; label: string; rows: number }> = [
  { key: "description", label: "Description", rows: 8 },
  { key: "personality", label: "Personality", rows: 4 },
  { key: "scenario", label: "Scenario", rows: 4 },
  { key: "first_mes", label: "First Message", rows: 5 },
  { key: "mes_example", label: "Message Example", rows: 7 },
  { key: "creator_notes", label: "Creator Notes", rows: 4 },
  { key: "system_prompt", label: "System Prompt", rows: 4 },
  { key: "post_history_instructions", label: "Post History Instructions", rows: 4 },
];

function compactText(value: string | undefined, maxLength: number): string {
  const compact = (value ?? "").replace(/\s+/g, " ").trim();
  if (compact.length <= maxLength) return compact;
  return `${compact.slice(0, maxLength - 1).trim()}...`;
}

export default function CharacterCardPage() {
  const params = useParams<{ id: string }>();
  const [card, setCard] = useState<CharacterCard | null>(null);
  const [draftData, setDraftData] = useState<CardData>({});
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("draft");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [avatarGenerating, setAvatarGenerating] = useState(false);
  const [roleImageGenerating, setRoleImageGenerating] = useState(false);
  const [avatarJob, setAvatarJob] = useState<{ generationId: string; status: string } | null>(null);
  const [roleImageJob, setRoleImageJob] = useState<{ generationId: string; status: string } | null>(null);
  const [avatarObjectUrl, setAvatarObjectUrl] = useState<string | null>(null);
  const [roleImageObjectUrl, setRoleImageObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.id) return;
    apiFetch<CharacterCard>(`/character-cards/${params.id}`)
      .then((data) => {
        setCard(data);
        setTitle(data.title);
        setStatus(data.status);
        setDraftData((data.spec_json.data ?? {}) as CardData);
        setError("");
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "人物卡载入失败");
      });
  }, [params]);

  useEffect(() => {
    if (!card?.avatar_asset_id) {
      setAvatarObjectUrl(null);
      return;
    }
    let revoked = false;
    const token = getToken();
    fetch(`${API_BASE}/character-cards/${card.id}/avatar`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) throw new Error("头像加载失败");
        return response.blob();
      })
      .then((blob) => {
        if (revoked) return;
        const nextUrl = URL.createObjectURL(blob);
        setAvatarObjectUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return nextUrl;
        });
      })
      .catch(() => {
        if (!revoked) setAvatarObjectUrl(null);
      });
    return () => {
      revoked = true;
      setAvatarObjectUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return null;
      });
    };
  }, [card?.avatar_asset_id, card?.id]);

  useEffect(() => {
    if (!card?.role_image_asset_id) {
      setRoleImageObjectUrl(null);
      return;
    }
    let revoked = false;
    const token = getToken();
    fetch(`${API_BASE}/character-cards/${card.id}/role-image`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) throw new Error("角色图加载失败");
        return response.blob();
      })
      .then((blob) => {
        if (revoked) return;
        const nextUrl = URL.createObjectURL(blob);
        setRoleImageObjectUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return nextUrl;
        });
      })
      .catch(() => {
        if (!revoked) setRoleImageObjectUrl(null);
      });
    return () => {
      revoked = true;
      setRoleImageObjectUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return null;
      });
    };
  }, [card?.role_image_asset_id, card?.id]);

  const characterBookEntries = useMemo(
    () => draftData.character_book?.entries ?? [],
    [draftData.character_book?.entries],
  );
  const previewDescription = compactText(draftData.description, 360);
  const previewPersonality = compactText(draftData.personality, 180);
  const previewScenario = compactText(draftData.scenario, 160);
  const previewFirstMessage = compactText(draftData.first_mes, 220);
  const previewTags = draftData.tags ?? [];

  function updateField(key: keyof CardData, value: string) {
    setDraftData((current) => ({ ...current, [key]: value }));
  }

  function updateName(value: string) {
    setDraftData((current) => ({ ...current, name: value }));
  }

  function updateTags(value: string) {
    setDraftData((current) => ({
      ...current,
      tags: value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    }));
  }

  function buildSpec() {
    return {
      ...(card?.spec_json ?? { spec: "chara_card_v2", spec_version: "2.0" }),
      spec: "chara_card_v2",
      spec_version: String(card?.spec_json?.spec_version ?? "2.0"),
      data: draftData,
    };
  }

  async function saveCard(nextStatus?: string) {
    if (!card) return;
    setSaving(true);
    try {
      const updated = await apiFetch<CharacterCard>(`/character-cards/${card.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title,
          status: nextStatus ?? status,
          spec_json: buildSpec(),
        }),
      });
      setCard(updated);
      setTitle(updated.title);
      setStatus(updated.status);
      setDraftData((updated.spec_json.data ?? {}) as CardData);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function regenerateCard(mode: "faithful" | "creative") {
    if (!card) return;
    setRegenerating(true);
    try {
      const updated = await apiFetch<CharacterCard>(`/character-cards/${card.id}/regenerate`, {
        method: "POST",
        body: JSON.stringify({
          mode,
          include_story_view: true,
          include_character_book: true,
          style: "sillytavern",
          language: "zh-CN",
        }),
      });
      setCard(updated);
      setTitle(updated.title);
      setStatus(updated.status);
      setDraftData((updated.spec_json.data ?? {}) as CardData);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "再生成失败");
    } finally {
      setRegenerating(false);
    }
  }

  async function downloadJson() {
    if (!card) return;
    await saveCard();
    const token = getToken();
    const response = await fetch(`${API_BASE}/character-cards/${card.id}/export.json`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      setError("导出失败");
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${draftData.name || title || "character-card"}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function refreshCard() {
    if (!card) return;
    const updated = await apiFetch<CharacterCard>(`/character-cards/${card.id}`);
    setCard(updated);
    setTitle(updated.title);
    setStatus(updated.status);
    setDraftData((updated.spec_json.data ?? {}) as CardData);
  }

  async function generateAvatar() {
    if (!card) return;
    setAvatarGenerating(true);
    setAvatarJob(null);
    try {
      await saveCard();
      const result = await apiFetch<{
        card: CharacterCard;
        generation_id: string;
        job_id: string;
        status: string;
      }>(`/character-cards/${card.id}/generate-avatar`, {
        method: "POST",
        body: JSON.stringify({
          model: "gpt-image-2-square",
          aspect_ratio: "1:1",
          image_size: "1K",
        }),
      });
      setCard(result.card);
      setAvatarJob({ generationId: result.generation_id, status: result.status });
      await pollAvatarGeneration(result.generation_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "头像生成失败");
    } finally {
      setAvatarGenerating(false);
    }
  }

  async function pollAvatarGeneration(generationId: string) {
    for (let attempt = 0; attempt < 80; attempt += 1) {
      const generation = await apiFetch<{ status: string; result_asset_ids: string[] }>(`/image-generations/${generationId}`);
      setAvatarJob({ generationId, status: generation.status });
      if (generation.status === "completed") {
        await refreshCard();
        setError("");
        return;
      }
      if (generation.status === "failed") {
        throw new Error("头像生成任务失败");
      }
      await new Promise((resolve) => window.setTimeout(resolve, 3000));
    }
    throw new Error("头像生成等待超时");
  }

  async function generateRoleImage() {
    if (!card) return;
    setRoleImageGenerating(true);
    setRoleImageJob(null);
    try {
      await saveCard();
      const result = await apiFetch<{
        card: CharacterCard;
        generation_id: string;
        job_id: string;
        status: string;
      }>(`/character-cards/${card.id}/generate-role-image`, {
        method: "POST",
        body: JSON.stringify({
          model: "gpt-image-2-three-four",
          aspect_ratio: "3:4",
          image_size: "1K",
        }),
      });
      setCard(result.card);
      setRoleImageJob({ generationId: result.generation_id, status: result.status });
      await pollRoleImageGeneration(result.generation_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "人物角色图生成失败");
    } finally {
      setRoleImageGenerating(false);
    }
  }

  async function pollRoleImageGeneration(generationId: string) {
    for (let attempt = 0; attempt < 100; attempt += 1) {
      const generation = await apiFetch<{ status: string; result_asset_ids: string[] }>(`/image-generations/${generationId}`);
      setRoleImageJob({ generationId, status: generation.status });
      if (generation.status === "completed") {
        await refreshCard();
        setError("");
        return;
      }
      if (generation.status === "failed") {
        throw new Error("人物角色图生成任务失败");
      }
      await new Promise((resolve) => window.setTimeout(resolve, 3000));
    }
    throw new Error("人物角色图生成等待超时");
  }

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1fr_360px]">
          <Panel className="p-6 md:p-8" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.16em]">SillyTavern Card</p>
            <input
              className="mt-3 w-full border-4 border-ink bg-paper p-3 text-3xl font-black outline-none"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="人物卡标题"
            />
            <div className="mt-5 flex flex-wrap gap-3">
              <button className="brutal-action brutal-action-primary" type="button" onClick={() => saveCard()} disabled={saving}>
                {saving ? "保存中..." : "保存"}
              </button>
              <button className="brutal-action brutal-action-info" type="button" onClick={() => saveCard("ready")} disabled={saving}>
                标记 Ready
              </button>
              <button className="brutal-action brutal-action-secondary" type="button" onClick={downloadJson} disabled={!card || saving}>
                导出 JSON
              </button>
              <button className="brutal-action brutal-action-secondary" type="button" onClick={() => regenerateCard("faithful")} disabled={regenerating}>
                事实再生成
              </button>
              <button className="brutal-action brutal-action-secondary" type="button" onClick={() => regenerateCard("creative")} disabled={regenerating}>
                创作再生成
              </button>
            </div>
          </Panel>

          <Panel className="p-6" tone="info">
            <p className="text-xs font-black uppercase tracking-[0.16em]">状态</p>
            <p className="mt-3 text-4xl font-black">{status}</p>
            <p className="mt-3 text-sm font-bold">格式 {card?.card_version ?? "..."}</p>
            {avatarJob ? (
              <p className="mt-3 text-xs font-black uppercase tracking-[0.16em]">
                avatar {avatarJob.status}
              </p>
            ) : null}
            {roleImageJob ? (
              <p className="mt-2 text-xs font-black uppercase tracking-[0.16em]">
                role image {roleImageJob.status}
              </p>
            ) : null}
            {card ? (
              <Link className="brutal-action brutal-action-secondary mt-5 inline-flex" href={`/story/entity/${card.source_entity_id}`}>
                返回人物故事
              </Link>
            ) : null}
          </Panel>
        </section>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        <section className="grid gap-6 xl:grid-cols-[1fr_420px]">
          <div className="space-y-5">
            <Panel className="p-5" tone="default">
              <label className="text-sm font-black uppercase tracking-[0.16em]">Name</label>
              <input
                className="mt-3 w-full border-4 border-ink bg-paper p-3 text-xl font-black outline-none"
                value={draftData.name ?? ""}
                onChange={(event) => updateName(event.target.value)}
              />
            </Panel>

            {editableFields.map((field) => (
              <Panel key={field.key} className="p-5" tone="default">
                <label className="text-sm font-black uppercase tracking-[0.16em]">{field.label}</label>
                <textarea
                  className="mt-3 w-full resize-y border-4 border-ink bg-paper p-3 text-sm font-semibold leading-relaxed outline-none"
                  rows={field.rows}
                  value={String(draftData[field.key] ?? "")}
                  onChange={(event) => updateField(field.key, event.target.value)}
                />
              </Panel>
            ))}

            <Panel className="p-5" tone="default">
              <label className="text-sm font-black uppercase tracking-[0.16em]">Tags</label>
              <input
                className="mt-3 w-full border-4 border-ink bg-paper p-3 text-sm font-bold outline-none"
                value={(draftData.tags ?? []).join(", ")}
                onChange={(event) => updateTags(event.target.value)}
              />
            </Panel>
          </div>

          <div className="space-y-5">
            <Panel className="overflow-hidden bg-ink text-white" tone="default">
              <div className="border-b-4 border-ink bg-white p-4 text-ink">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.16em]">GPT Role Image</p>
                    <h2 className="mt-1 text-2xl font-black">人物角色图</h2>
                  </div>
                  <button
                    className="brutal-action brutal-action-primary justify-center px-3 py-2 text-sm disabled:opacity-60"
                    type="button"
                    onClick={generateRoleImage}
                    disabled={!card || roleImageGenerating || saving}
                  >
                    {roleImageGenerating ? "生成中..." : "生成角色图"}
                  </button>
                </div>
                <p className="mt-3 text-sm font-bold">
                  会用当前人物卡文本生成完整酒馆风格角色卡图；如果已有头像，会作为参考图保持角色一致。
                </p>
              </div>
              <div className="bg-[#14121f] p-4">
                <div className="relative aspect-[3/4] overflow-hidden border-4 border-white/70 bg-[#090914]">
                  {roleImageObjectUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={roleImageObjectUrl} alt={`${draftData.name ?? "角色"}人物角色图`} className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full items-center justify-center p-8 text-center">
                      <div>
                        <p className="text-xs font-black uppercase tracking-[0.18em] text-aqua">No Generated Role Image</p>
                        <p className="mt-3 text-3xl font-black leading-tight">{draftData.name || "未命名角色"}</p>
                        <p className="mt-3 text-sm font-bold leading-relaxed text-white/70">
                          点击生成后，这里会显示由 GPT/SyGPT 产出的完整人物角色图。
                        </p>
                      </div>
                    </div>
                  )}
                </div>
                {roleImageJob ? (
                  <p className="mt-3 text-xs font-black uppercase tracking-[0.16em] text-aqua">
                    generation {roleImageJob.status}
                  </p>
                ) : null}
              </div>
            </Panel>

            <Panel className="overflow-hidden bg-white" tone="default">
              <div className="grid min-h-[520px] grid-rows-[auto_1fr_auto]">
                <div className="grid grid-cols-[132px_1fr] border-b-4 border-ink bg-ink text-white">
                  <div className="aspect-square overflow-hidden border-r-4 border-ink bg-paper">
                    {avatarObjectUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={avatarObjectUrl} alt={`${draftData.name ?? "角色"}头像`} className="h-full w-full object-cover" />
                    ) : (
                      <div className="flex h-full items-center justify-center bg-aqua p-4 text-center text-xs font-black uppercase tracking-[0.16em] text-ink">
                        No Avatar
                      </div>
                    )}
                  </div>
                  <div className="flex min-w-0 flex-col justify-between p-4">
                    <div>
                      <p className="text-xs font-black uppercase tracking-[0.18em] text-aqua">SillyTavern V2</p>
                      <h2 className="mt-2 break-words text-3xl font-black leading-none">
                        {draftData.name || "未命名角色"}
                      </h2>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <span className="border-2 border-white bg-neon px-2 py-1 text-xs font-black uppercase tracking-[0.12em] text-ink">
                        {card?.mode ?? "draft"}
                      </span>
                      <span className="border-2 border-white bg-white px-2 py-1 text-xs font-black uppercase tracking-[0.12em] text-ink">
                        {status}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="space-y-4 bg-paper p-4">
                  <section className="border-4 border-ink bg-white p-4">
                    <p className="text-xs font-black uppercase tracking-[0.16em]">Description</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm font-semibold leading-relaxed">
                      {previewDescription || "暂无描述。"}
                    </p>
                  </section>

                  <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
                    <div className="border-4 border-ink bg-peach p-4">
                      <p className="text-xs font-black uppercase tracking-[0.16em]">Personality</p>
                      <p className="mt-2 text-sm font-bold leading-relaxed">{previewPersonality || "暂无人格设定。"}</p>
                    </div>
                    <div className="border-4 border-ink bg-aqua p-4">
                      <p className="text-xs font-black uppercase tracking-[0.16em]">Scenario</p>
                      <p className="mt-2 text-sm font-bold leading-relaxed">{previewScenario || "暂无场景。"}</p>
                    </div>
                  </section>

                  <section className="border-4 border-ink bg-gold p-4">
                    <p className="text-xs font-black uppercase tracking-[0.16em]">First Message</p>
                    <p className="mt-2 text-sm font-black leading-relaxed">{previewFirstMessage || "暂无开场白。"}</p>
                  </section>
                </div>

                <div className="border-t-4 border-ink bg-white p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-black uppercase tracking-[0.16em]">Character Book</p>
                      <p className="mt-1 text-2xl font-black">{characterBookEntries.length} entries</p>
                    </div>
                    <button
                      className="brutal-action brutal-action-primary justify-center px-3 py-2 text-sm disabled:opacity-60"
                      type="button"
                      onClick={generateAvatar}
                      disabled={!card || avatarGenerating || saving}
                    >
                      {avatarGenerating ? "生成中..." : "生成头像"}
                    </button>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {previewTags.slice(0, 8).map((tag) => (
                      <span key={tag} className="brutal-chip">
                        {tag}
                      </span>
                    ))}
                    {previewTags.length === 0 ? <span className="brutal-chip">untagged</span> : null}
                  </div>
                </div>
              </div>
            </Panel>

            <Panel className="p-5" tone="info">
              <p className="text-sm font-black uppercase tracking-[0.16em]">Character Book</p>
              <p className="mt-3 text-4xl font-black">{characterBookEntries.length}</p>
              <div className="mt-4 space-y-3">
                {characterBookEntries.slice(0, 6).map((entry, index) => (
                  <div key={`${entry.id ?? index}-${entry.comment ?? "entry"}`} className="border-4 border-ink bg-paper p-3">
                    <p className="text-xs font-black uppercase tracking-[0.14em]">{entry.comment ?? "entry"}</p>
                    <p className="mt-2 text-sm font-bold">{(entry.keys ?? []).join(" / ")}</p>
                    <p className="mt-2 text-xs font-semibold leading-relaxed">{entry.content}</p>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel className="p-5" tone="default">
              <p className="text-sm font-black uppercase tracking-[0.16em]">Source Snapshot</p>
              <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap text-xs font-semibold leading-relaxed">
                {JSON.stringify(card?.source_snapshot_json ?? {}, null, 2)}
              </pre>
            </Panel>
          </div>
        </section>
      </main>
    </AuthGate>
  );
}
