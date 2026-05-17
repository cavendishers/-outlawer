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
    <main className="space-y-5">
      <section className="workbench-header">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="workbench-title">页面异常</h1>
              <span className="workbench-stamp bg-ember">需要恢复</span>
            </div>
            <p className="workbench-lede">
              当前页面渲染时遇到错误。可以重试当前页面，或回到首页重新进入对应工作台。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={reset} className="tool-action bg-neon">
              重新加载
            </button>
            <Link href="/" className="tool-action bg-canvas">
              返回首页
            </Link>
          </div>
        </div>
      </section>

      <Panel className="p-5" tone="default">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-black">排查提示</h2>
          <span className="workbench-stamp bg-canvas">图谱工作台</span>
        </div>
        <p className="mt-4 text-sm font-bold leading-relaxed md:text-base">
          如果这个错误是在打开新图谱工作台时出现，先检查后端 `/api/v1/graph/workspace` 是否可达，再刷新页面。
        </p>
      </Panel>
    </main>
  );
}
