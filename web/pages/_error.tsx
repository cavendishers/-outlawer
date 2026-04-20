import Link from "next/link";
import { useEffect } from "react";

type ErrorPageProps = {
  statusCode?: number;
};

export default function ErrorPage({ statusCode }: ErrorPageProps) {
  useEffect(() => {
    if (statusCode) {
      console.error(`Next.js error page rendered with status ${statusCode}`);
    }
  }, [statusCode]);

  return (
    <main className="min-h-screen bg-paper px-4 py-12 text-ink">
      <div className="mx-auto max-w-3xl border-4 border-ink bg-white p-8 shadow-brutal">
        <p className="text-sm font-black uppercase tracking-[0.2em]">Error</p>
        <h1 className="mt-3 text-4xl font-black">页面渲染失败</h1>
        <p className="mt-4 text-lg font-bold leading-relaxed">
          这是备用错误页。你可以先返回首页，再从图谱工作台重新进入目标节点。
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/" className="brutal-action brutal-action-secondary">
            返回首页
          </Link>
          <Link href="/graph" className="brutal-action brutal-action-primary">
            打开图谱工作台
          </Link>
        </div>
      </div>
    </main>
  );
}

ErrorPage.getInitialProps = ({ res, err }: { res?: { statusCode?: number }; err?: { statusCode?: number } }) => {
  const statusCode = res?.statusCode || err?.statusCode || 404;
  return { statusCode };
};
