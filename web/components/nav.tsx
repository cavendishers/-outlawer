"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const primaryItems = [
  { href: "/", label: "首页" },
  { href: "/inbox", label: "导入" },
  { href: "/search", label: "搜索" },
];

const knowledgeItems = [
  { href: "/library", label: "档案" },
  { href: "/people", label: "人物" },
  { href: "/events", label: "事件" },
  { href: "/timeline", label: "图谱" },
];

const secondaryItems = [
  { href: "/review", label: "审核" },
  { href: "/operations", label: "运维" },
  { href: "/graph", label: "工作台" },
];

export function Navigation() {
  const pathname = usePathname();
  const knowledgeActive = knowledgeItems.some((item) => item.href === pathname);
  const secondaryActive = secondaryItems.some((item) => item.href === pathname);

  return (
    <nav className="flex flex-wrap items-start gap-3 text-sm font-bold uppercase tracking-[0.16em]">
      {primaryItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={`nav-pill ${
            pathname === item.href ? "nav-pill-active" : ""
          }`}
        >
          {item.label}
        </Link>
      ))}
      <NavMenu label="知识库" active={knowledgeActive} items={knowledgeItems} pathname={pathname} />
      <NavMenu label="更多" active={secondaryActive} items={secondaryItems} pathname={pathname} align="right" />
    </nav>
  );
}

type NavMenuProps = {
  active: boolean;
  align?: "left" | "right";
  items: Array<{ href: string; label: string }>;
  label: string;
  pathname: string;
};

function NavMenu({ active, align = "left", items, label, pathname }: NavMenuProps) {
  return (
    <details className="group relative">
      <summary
        className={`nav-pill cursor-pointer list-none select-none marker:hidden ${
          active ? "nav-pill-active" : ""
        }`}
      >
        {label}
      </summary>
      <div
        className={`absolute z-20 mt-3 min-w-36 space-y-2 border-4 border-ink bg-paper p-3 shadow-brutal ${
          align === "right" ? "right-0" : "left-0"
        }`}
      >
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`block border-2 border-ink px-3 py-2 text-sm font-black shadow-brutalTiny ${
              pathname === item.href ? "bg-neon" : "bg-canvas"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>
    </details>
  );
}
