import Link from "next/link";

import { Panel } from "@/components/panel";

export default function NotFound() {
  return (
    <main className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
      <Panel className="p-6 md:p-8" tone="danger">
        <p className="text-sm font-black uppercase tracking-[0.2em]">404 / Lost Node</p>
        <h1 className="mt-3 font-display text-[clamp(2.4rem,5vw,4.8rem)] leading-[0.9]">目标节点失联</h1>
        <p className="mt-4 text-lg font-bold leading-relaxed">
          当前页面没有找到对应的卷宗、人物或事件。你可以回到图谱主入口，重新选择一条可追踪的路径。
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/" className="brutal-action brutal-action-secondary">
            返回首页
          </Link>
          <Link href="/graph" className="brutal-action brutal-action-primary">
            进入图谱工作台
          </Link>
        </div>
      </Panel>

      <Panel className="p-6" tone="default">
        <p className="text-xs font-black uppercase tracking-[0.16em]">Recovery Path</p>
        <div className="mt-4 space-y-3 text-base font-bold leading-relaxed">
          <p>1. 回到图谱工作台重新选择锚点。</p>
          <p>2. 或从人物、事件、档案列表重新打开记录。</p>
          <p>3. 如果是刚被合并或重写的节点，优先去审核或校对页确认最新状态。</p>
        </div>
      </Panel>
    </main>
  );
}
