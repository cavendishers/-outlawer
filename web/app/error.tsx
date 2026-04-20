"use client";

import Link from "next/link";
import { useEffect } from "react";

import { Panel } from "@/components/panel";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
      <Panel className="p-6 md:p-8" tone="danger">
        <p className="text-sm font-black uppercase tracking-[0.2em]">Runtime Error</p>
        <h1 className="mt-3 font-display text-[clamp(2.4rem,5vw,4.8rem)] leading-[0.9]">图谱链路中断</h1>
        <p className="mt-4 text-lg font-bold leading-relaxed">
          当前页面遇到异常。你可以先重试，或回到首页重新进入图谱工作台。
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" onClick={reset} className="brutal-action brutal-action-primary">
            重新加载
          </button>
          <Link href="/" className="brutal-action brutal-action-secondary">
            返回首页
          </Link>
        </div>
      </Panel>

      <Panel className="p-6" tone="default">
        <p className="text-xs font-black uppercase tracking-[0.16em]">Hint</p>
        <p className="mt-4 text-base font-bold leading-relaxed">
          如果这个错误是在打开新图谱工作台时出现，先检查后端 `/api/v1/graph/workspace` 是否可达，再刷新页面。
        </p>
      </Panel>
    </main>
  );
}
