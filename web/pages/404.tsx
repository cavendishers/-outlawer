import Link from "next/link";

export default function Custom404() {
  return (
    <main className="min-h-screen bg-paper px-4 py-12 text-ink">
      <div className="mx-auto max-w-3xl border-4 border-ink bg-white p-8 shadow-brutal">
        <p className="text-sm font-black uppercase tracking-[0.2em]">404</p>
        <h1 className="mt-3 text-4xl font-black">页面失联</h1>
        <p className="mt-4 text-lg font-bold leading-relaxed">
          当前链接没有找到对应内容。你可以回到首页、图谱工作台，或者重新打开具体节点。
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
