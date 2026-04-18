import Link from "next/link";

import { Panel } from "@/components/panel";

const modules = [
  { index: "01", label: "工具", href: "/tools", tone: "paper" as const },
  { index: "02", label: "搜索", href: "/search", tone: "aqua" as const },
  { index: "03", label: "档案", href: "/library", tone: "paper" as const },
  { index: "04", label: "图谱", href: "/timeline", tone: "peach" as const },
  { index: "05", label: "导入", href: "/inbox", tone: "neon" as const },
  { index: "06", label: "事件", href: "/events", tone: "paper" as const },
];

export default function Home() {
  return (
    <main className="grid gap-8 lg:grid-cols-[1.55fr_1fr]">
      <section className="flex flex-col justify-between gap-6">
        <div>
          <p className="font-display text-[clamp(3.5rem,8vw,7rem)] uppercase leading-[0.88]">Outlawer</p>
          <p className="font-display text-[clamp(3.2rem,7vw,6rem)] leading-[0.9]">法外狂徒</p>
          <p className="mt-6 max-w-3xl text-[clamp(1.2rem,2vw,2.2rem)] font-black leading-snug">
            规矩是给台面上的人看的，法外狂徒只对结果负责。
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          {["已观察", "听说", "推测"].map((item, index) => (
            <Panel key={item} className="px-5 py-4 text-lg font-black" tone={index === 1 ? "aqua" : "paper"}>
              {item}
            </Panel>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-4">
        {modules.map((module) => (
          <Link key={module.label} href={module.href}>
            <Panel className="px-5 py-5 transition-transform hover:-translate-y-1" tone={module.tone}>
              <p className="text-xs font-black uppercase tracking-[0.2em]">{module.index}</p>
              <p className="mt-2 text-4xl font-black">{module.label}</p>
            </Panel>
          </Link>
        ))}
      </section>
    </main>
  );
}
