import Link from "next/link";

import { Panel } from "@/components/panel";

export default function NotFound() {
  return (
    <main className="space-y-5">
      <section className="workbench-header">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="workbench-title">未找到页面</h1>
              <span className="workbench-stamp bg-ember">404</span>
            </div>
            <p className="workbench-lede">
              当前地址没有匹配到卷宗、人物或事件页面。可以返回首页，或从图谱工作台重新选择可追踪路径。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/" className="tool-action bg-canvas">
              返回首页
            </Link>
            <Link href="/graph" className="tool-action bg-neon">
              进入图谱工作台
            </Link>
          </div>
        </div>
      </section>

      <Panel className="p-5" tone="default">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-black">恢复路径</h2>
          <span className="workbench-stamp bg-canvas">入口建议</span>
        </div>
        <div className="mt-4 space-y-3 text-sm font-bold leading-relaxed md:text-base">
          <p>1. 回到图谱工作台重新选择锚点。</p>
          <p>2. 或从人物、事件、档案列表重新打开记录。</p>
          <p>3. 如果是刚被合并或重写的节点，优先去审核或校对页确认最新状态。</p>
        </div>
      </Panel>
    </main>
  );
}
