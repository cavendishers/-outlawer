import Link from "next/link";

import { Panel } from "@/components/panel";

const primaryActions = [
  { label: "导入新卷宗", href: "/inbox", tone: "bg-neon", description: "文本、图片、音频、视频统一入口" },
  { label: "统一搜索", href: "/search", tone: "bg-canvas", description: "关键词、人物、事件、相似内容一起查" },
  { label: "图谱工作台", href: "/graph", tone: "bg-canvas", description: "从节点关系和时间线继续追踪" },
];

const focusAreas = [
  { label: "档案", href: "/library", value: "原文与分析", note: "查看卷宗、AI 运行记录和风格化版本" },
  { label: "事件", href: "/events", value: "时间驱动", note: "按事件清单进入关联视图和校对台" },
  { label: "人物", href: "/people", value: "角色索引", note: "追踪人物时间线、别名和人物卡" },
  { label: "审核", href: "/review", value: "质量入口", note: "处理合并候选、校正抽取误差" },
];

const workflow = [
  "导入原始材料",
  "AI 解析人物 / 事件 / 关系",
  "人工审核并修正",
  "沉淀为图谱与故事视图",
];

export default function Home() {
  return (
    <main className="space-y-5">
      <section className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="border-4 border-ink bg-bone p-5 shadow-brutal md:p-6">
          <div className="flex flex-wrap gap-2">
            <span className="workbench-stamp bg-neon">知识库工作台</span>
            <span className="workbench-stamp bg-canvas">AI 解析</span>
            <span className="workbench-stamp bg-gold">图谱驱动</span>
          </div>
          <h1 className="mt-4 text-[clamp(2.6rem,6vw,5.8rem)] font-black leading-none tracking-[-0.07em]">
            把材料变成可追踪的知识网络
          </h1>
          <p className="mt-4 max-w-3xl text-base font-bold leading-relaxed text-muted md:text-lg">
            这里不是单纯存笔记，而是把每份材料拆成原始资产、结构化知识、人物档案、事件链路和风格化展示。先导入，再校正，最后让图谱自己长出来。
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {primaryActions.map((action) => (
              <Link key={action.href} href={action.href} className={`tool-action ${action.tone}`}>
                {action.label}
              </Link>
            ))}
          </div>
        </div>

        <Panel className="p-5" tone="quiet" intensity="quiet">
          <p className="section-kicker">下一步怎么走</p>
          <div className="mt-4 space-y-3">
            {primaryActions.map((action, index) => (
              <Link key={action.href} href={action.href} className="block border-4 border-ink bg-canvas p-4 shadow-brutalSoft transition-transform hover:-translate-y-1">
                <div className="flex items-center justify-between gap-3">
                  <span className="workbench-stamp bg-gold">{index + 1}</span>
                  <span className="text-xs font-black tracking-[0.12em] text-muted">{action.description}</span>
                </div>
                <p className="mt-3 text-2xl font-black leading-tight">{action.label}</p>
              </Link>
            ))}
          </div>
        </Panel>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {focusAreas.map((area) => (
          <Link key={area.href} href={area.href} className="dense-record grid-cols-1">
            <div className="dense-record-body block">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="workbench-stamp bg-canvas">{area.value}</span>
                <span className="text-xs font-black text-muted">{area.label}</span>
              </div>
              <p className="mt-4 text-3xl font-black leading-none tracking-[-0.04em]">{area.label}</p>
              <p className="mt-3 text-sm font-bold leading-relaxed text-muted">{area.note}</p>
            </div>
          </Link>
        ))}
      </section>

      <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <Panel className="p-5" tone="time" intensity="quiet">
          <p className="section-kicker">处理流程</p>
          <div className="mt-4 grid gap-3">
            {workflow.map((item, index) => (
              <div key={item} className="flex items-center gap-3 border-4 border-ink bg-canvas p-3 shadow-brutalSoft">
                <span className="workbench-stamp bg-neon">{index + 1}</span>
                <p className="text-base font-black">{item}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel className="p-5" tone="story" intensity="quiet">
          <p className="section-kicker">产品原则</p>
          <p className="mt-4 text-xl font-black leading-snug">
            先保留原始材料，再生成结构化知识；先让 AI 给出草案，再让人工校正成为长期资产。
          </p>
          <p className="body-copy mt-4">
            后续页面会继续按这个原则收敛：列表页负责筛选和定位，详情页负责结论与下一步动作，调试信息默认折叠，校对入口保持可见。
          </p>
        </Panel>
      </section>
    </main>
  );
}
