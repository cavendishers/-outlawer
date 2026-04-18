export type CandidateObjectSummary = {
  id: string;
  label: string;
  href: string;
  stats: Record<string, number>;
  data?: Record<string, unknown> | null;
};

export type MergeCandidateItem = {
  id: string;
  object_type: string;
  status: string;
  score: number;
  reason: Record<string, unknown> | null;
  reviewed_at: string | null;
  review_note: string | null;
  source: CandidateObjectSummary | null;
  candidate: CandidateObjectSummary | null;
};

export type EntityTimelineFragment = {
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
};

export function formatCandidateScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function candidateTypeLabel(objectType: string): string {
  if (objectType === "entity") return "人物候选";
  if (objectType === "event") return "事件候选";
  return "候选";
}

export function summarizeCandidateReason(reason: Record<string, unknown> | null | undefined): string[] {
  if (!reason) return [];

  const tags: string[] = [];
  const signals = toStringArray(reason.signals);
  const reasons = toStringArray(reason.reasons);
  const sharedParticipants = toStringArray(reason.shared_participants);
  const sharedFields = toStringArray(reason.shared_fields);

  tags.push(...signals.slice(0, 3));
  tags.push(...reasons.slice(0, 3));
  tags.push(...sharedParticipants.slice(0, 2).map((value) => `共享人物:${value}`));
  tags.push(...sharedFields.slice(0, 2).map((value) => `共享字段:${value}`));

  const location = typeof reason.location === "string" ? reason.location : null;
  if (location) tags.push(`地点:${location}`);

  const timeDistance = typeof reason.distance_days === "number" ? reason.distance_days : null;
  if (timeDistance !== null) tags.push(`时间差:${timeDistance}天`);

  return [...new Set(tags)].slice(0, 6);
}

export function summaryStatTags(summary: CandidateObjectSummary | null): string[] {
  if (!summary) return [];
  return Object.entries(summary.stats || {})
    .filter(([, value]) => typeof value === "number")
    .map(([key, value]) => `${value} ${humanizeStatKey(key)}`);
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && Boolean(item.trim()));
}

function humanizeStatKey(key: string): string {
  const map: Record<string, string> = {
    related_note_count: "关联卷宗",
    related_event_count: "关联事件",
    participant_count: "参与角色",
    linked_note_count: "挂接卷宗",
  };
  return map[key] ?? key.replaceAll("_", " ");
}
