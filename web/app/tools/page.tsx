"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Panel } from "@/components/panel";
import { apiFetch, clearToken, getToken } from "@/lib/api";

const toolLinks = [
  {
    label: "导入卷宗",
    description: "录入文本材料，启动 AI 解析、归类和图谱编排。",
    href: "/inbox",
    tone: "signal" as const,
  },
  {
    label: "统一搜索",
    description: "把关键词、相似卷宗、人物和事件命中收拢到一个检索页里。",
    href: "/search",
    tone: "info" as const,
  },
  {
    label: "档案库",
    description: "浏览已经归档的原始记录与风格化卷宗。",
    href: "/library",
    tone: "default" as const,
  },
  {
    label: "人物索引",
    description: "查看人物节点、身份卡和相关时间线片段。",
    href: "/people",
    tone: "info" as const,
  },
  {
    label: "事件图谱",
    description: "进入事件、关系和全局时间线视角。",
    href: "/timeline",
    tone: "story" as const,
  },
];

const serviceLabels: Record<string, string> = {
  database: "数据库",
  object_storage: "对象存储",
  redis: "Redis",
  broker: "RabbitMQ",
};

type AuthMe = {
  id: string;
  username: string;
  display_name: string;
  status: string;
};

type ServiceState = {
  status: string;
  detail: string;
};

type HealthState = {
  status: string;
  services: Record<string, ServiceState>;
};

type NoteItem = {
  id: string;
  title: string;
  status: string;
  primary_time: string | null;
};

type JobItem = {
  id: string;
  job_type: string;
  status: string;
  target_type: string;
  target_id: string;
  error_message: string | null;
  retry_count: number;
  created_at: string | null;
  finished_at: string | null;
};

type ListResponse<T> = {
  items: T[];
};

export default function ToolsPage() {
  const [authed, setAuthed] = useState(false);
  const [health, setHealth] = useState<HealthState | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [me, setMe] = useState<AuthMe | null>(null);
  const [counts, setCounts] = useState({
    notes: 0,
    entities: 0,
    events: 0,
    timeline: 0,
  });
  const [recentNotes, setRecentNotes] = useState<NoteItem[]>([]);
  const [recentJobs, setRecentJobs] = useState<JobItem[]>([]);

  useEffect(() => {
    const hasToken = Boolean(getToken());
    setAuthed(hasToken);

    apiFetch<HealthState>("/health")
      .then((data) => {
        setHealth(data);
        setHealthError(false);
      })
      .catch(() => {
        setHealth(null);
        setHealthError(true);
      });

    if (!hasToken) {
      setMe(null);
      setCounts({ notes: 0, entities: 0, events: 0, timeline: 0 });
      setRecentNotes([]);
      setRecentJobs([]);
      return;
    }

    Promise.all([
      apiFetch<AuthMe>("/auth/me"),
      apiFetch<ListResponse<NoteItem>>("/notes"),
      apiFetch<ListResponse<{ id: string }>>("/entities"),
      apiFetch<ListResponse<{ id: string }>>("/events"),
      apiFetch<ListResponse<{ id: string }>>("/timeline"),
      apiFetch<ListResponse<JobItem>>("/jobs?limit=4"),
    ])
      .then(([user, notes, entities, events, timeline, jobs]) => {
        setMe(user);
        setCounts({
          notes: notes.items.length,
          entities: entities.items.length,
          events: events.items.length,
          timeline: timeline.items.length,
        });
        setRecentNotes(notes.items.slice(0, 4));
        setRecentJobs(jobs.items);
      })
      .catch(() => {
        setAuthed(false);
        setMe(null);
        setCounts({ notes: 0, entities: 0, events: 0, timeline: 0 });
        setRecentNotes([]);
        setRecentJobs([]);
      });
  }, []);

  function handleLogout() {
    clearToken();
    setAuthed(false);
    setMe(null);
    setRecentNotes([]);
    setRecentJobs([]);
  }

  const healthTone = healthError
    ? "danger"
    : health?.status === "healthy"
      ? "success"
      : health?.status === "degraded"
        ? "time"
        : "time";

  const healthLabel = healthError
    ? "异常"
    : health?.status === "healthy"
      ? "在线"
      : health?.status === "degraded"
        ? "降级"
        : "检查中";

  function formatStamp(value: string | null): string {
    if (!value) return "未记录";
    return value.slice(0, 16).replace("T", " ");
  }

  return (
    <main className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <Panel className="p-6 md:p-8" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.2em]">Tool Console</p>
          <h1 className="mt-3 font-display text-[clamp(2.5rem,6vw,5rem)] leading-[0.9]">工具台</h1>
          <p className="mt-4 max-w-3xl text-lg font-bold leading-relaxed">
            这里是所有操作入口的控制台。登录只是访问能力的一部分，真正的工具入口应该把导入、档案、人物和图谱集中起来。
          </p>
        </Panel>

        <Panel className="p-6" tone={authed ? "success" : "time"}>
          <p className="text-xs font-black uppercase tracking-[0.16em]">访问状态</p>
          <p className="mt-3 text-4xl font-black">{authed ? "已登录" : "未登录"}</p>
          <p className="mt-4 text-sm font-bold leading-relaxed">
            {authed ? "当前浏览器已经持有访问令牌，可以进入受保护页面。" : "先登录后再进入导入、档案和图谱页面。"}
          </p>
          {me ? (
            <div className="mt-5 flex flex-wrap gap-2">
              <span className="brutal-chip">{me.display_name || me.username}</span>
              <span className="brutal-chip">{me.status}</span>
            </div>
          ) : null}
          <div className="mt-5 flex flex-wrap gap-3">
            <Link href="/login" className="brutal-action brutal-action-primary">
              {authed ? "切换账号" : "去登录"}
            </Link>
            {authed ? (
              <button type="button" onClick={handleLogout} className="brutal-action brutal-action-secondary">
                退出登录
              </button>
            ) : null}
          </div>
        </Panel>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Panel className="p-5" tone={healthTone}>
          <p className="text-xs font-black uppercase tracking-[0.16em]">API 状态</p>
          <p className="mt-3 text-4xl font-black">{healthLabel}</p>
          <p className="mt-3 text-sm font-bold leading-relaxed">
            {health?.status === "degraded"
              ? "API 可达，但部分基础服务处于降级状态。"
              : "后端健康检查接口用于确认当前 API 和基础依赖是否可达。"}
          </p>
        </Panel>

        <Panel className="p-5" tone="default">
          <p className="text-xs font-black uppercase tracking-[0.16em]">档案卷宗</p>
          <p className="mt-3 text-4xl font-black">{counts.notes}</p>
          <p className="mt-3 text-sm font-bold leading-relaxed">
            已经进入知识库并可继续追踪的笔记数量。
          </p>
        </Panel>

        <Panel className="p-5" tone="info">
          <p className="text-xs font-black uppercase tracking-[0.16em]">人物节点</p>
          <p className="mt-3 text-4xl font-black">{counts.entities}</p>
          <p className="mt-3 text-sm font-bold leading-relaxed">
            当前已抽取并可进入人物详情页的实体数量。
          </p>
        </Panel>

        <Panel className="p-5" tone="story">
          <p className="text-xs font-black uppercase tracking-[0.16em]">事件 / 时间线</p>
          <p className="mt-3 text-4xl font-black">
            {counts.events} / {counts.timeline}
          </p>
          <p className="mt-3 text-sm font-bold leading-relaxed">
            事件节点与时间线条目已经沉淀后的当前规模。
          </p>
        </Panel>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Object.entries(serviceLabels).map(([key, label]) => {
          const service = health?.services?.[key];
          const tone =
            service?.status === "healthy" ? "success" : service?.status === "error" || healthError ? "danger" : "time";
          return (
            <Panel key={key} className="p-5" tone={tone}>
              <p className="text-xs font-black uppercase tracking-[0.16em]">{label}</p>
              <p className="mt-3 text-3xl font-black">
                {service?.status === "healthy" ? "正常" : service?.status === "error" ? "异常" : "待检查"}
              </p>
              <p className="mt-3 break-all text-sm font-bold leading-relaxed">
                {service?.detail ?? "等待健康检查返回详情。"}
              </p>
            </Panel>
          );
        })}
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {toolLinks.map((item) => (
          <Link key={item.href} href={item.href}>
            <Panel className="h-full p-5 transition-transform hover:-translate-y-1" tone={item.tone}>
              <p className="text-xs font-black uppercase tracking-[0.16em]">Action</p>
              <p className="mt-3 text-3xl font-black">{item.label}</p>
              <p className="mt-3 text-base font-bold leading-relaxed">{item.description}</p>
            </Panel>
          </Link>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel className="p-6" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.16em]">最近卷宗</p>
          <div className="mt-5 space-y-3">
            {recentNotes.length ? (
              recentNotes.map((note) => (
                <Link key={note.id} href={`/notes/${note.id}`} className="block">
                  <div className="surface-inset border-4 border-ink p-4 transition-transform hover:-translate-y-1">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs font-black uppercase tracking-[0.14em]">{note.status}</p>
                      <p className="text-xs font-black uppercase tracking-[0.14em]">
                        {note.primary_time?.slice(0, 10) ?? "未校时"}
                      </p>
                    </div>
                    <p className="mt-3 text-xl font-black">{note.title}</p>
                  </div>
                </Link>
              ))
            ) : (
              <div className="surface-inset border-4 border-dashed border-ink p-4 text-base font-bold">
                暂时还没有可展示的卷宗，先去导入一条文本试试。
              </div>
            )}
          </div>
        </Panel>

        <Panel className="p-6" tone="info">
          <p className="text-sm font-black uppercase tracking-[0.16em]">最近任务</p>
          <div className="mt-5 space-y-3">
            {recentJobs.length ? (
              recentJobs.map((job) => (
                <div key={job.id} className="surface-inset border-4 border-ink p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs font-black uppercase tracking-[0.14em]">
                      {job.job_type} / {job.target_type}
                    </p>
                    <span className="border-2 border-ink bg-white px-2 py-1 text-xs font-black uppercase tracking-[0.12em]">
                      {job.status}
                    </span>
                  </div>
                  <p className="mt-3 text-lg font-black">{job.target_id}</p>
                  <p className="mt-3 text-sm font-bold leading-relaxed">
                    创建时间 {formatStamp(job.created_at)}
                    {job.finished_at ? ` / 完成 ${formatStamp(job.finished_at)}` : ""}
                  </p>
                  {job.error_message ? (
                    <p className="mt-2 text-sm font-bold text-red-950">{job.error_message}</p>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="surface-inset border-4 border-dashed border-ink p-4 text-base font-bold">
                当前没有最近任务记录。导入卷宗后，这里会出现解析任务。
              </div>
            )}
          </div>
        </Panel>
      </section>

      <section className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <Panel className="p-6" tone="default">
          <p className="text-sm font-black uppercase tracking-[0.16em]">这个工具页是做什么的</p>
          <p className="mt-4 text-2xl font-black">它是总控台，不是登录页。</p>
          <p className="mt-4 text-base font-bold leading-relaxed">
            之前首页的“工具”直接跳到登录，会让人误以为这个模块只有认证功能。现在它的职责是汇总访问状态、系统健康和各业务入口，让首页模块语义更完整。
          </p>
        </Panel>

        <Panel className="p-6" tone="info">
          <p className="text-sm font-black uppercase tracking-[0.16em]">推荐使用顺序</p>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="surface-inset border-4 border-ink p-4">
              <p className="text-xs font-black uppercase tracking-[0.14em]">01 登录</p>
              <p className="mt-2 text-xl font-black">拿到访问令牌</p>
            </div>
            <div className="surface-inset border-4 border-ink p-4">
              <p className="text-xs font-black uppercase tracking-[0.14em]">02 导入</p>
              <p className="mt-2 text-xl font-black">把原始卷宗送进知识引擎</p>
            </div>
            <div className="surface-inset border-4 border-ink p-4">
              <p className="text-xs font-black uppercase tracking-[0.14em]">03 档案</p>
              <p className="mt-2 text-xl font-black">检查摘要和风格化视图</p>
            </div>
            <div className="surface-inset border-4 border-ink p-4">
              <p className="text-xs font-black uppercase tracking-[0.14em]">04 图谱</p>
              <p className="mt-2 text-xl font-black">进入人物、事件和时间线联动</p>
            </div>
          </div>
        </Panel>
      </section>
    </main>
  );
}
