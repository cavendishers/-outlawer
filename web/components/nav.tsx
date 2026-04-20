"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "首页" },
  { href: "/inbox", label: "导入" },
  { href: "/search", label: "搜索" },
  { href: "/review", label: "审核" },
  { href: "/operations", label: "运维" },
  { href: "/library", label: "档案" },
  { href: "/people", label: "人物" },
  { href: "/events", label: "事件" },
  { href: "/timeline", label: "图谱" },
];

export function Navigation() {
  const pathname = usePathname();
  return (
    <nav className="flex flex-wrap gap-3 text-sm font-bold uppercase tracking-[0.16em]">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={`border-4 border-ink px-3 py-2 font-black shadow-brutal transition-transform hover:-translate-y-1 ${
            pathname === item.href ? "bg-neon" : "bg-white"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
