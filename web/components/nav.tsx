"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const primaryItems = [
  { href: "/", label: "首页" },
  { href: "/inbox", label: "导入" },
  { href: "/search", label: "搜索" },
];

const knowledgeItems = [
  { href: "/library", label: "档案", match: ["/library", "/notes", "/story/note"] },
  { href: "/people", label: "人物", match: ["/people", "/story/entity", "/character-cards"] },
  { href: "/events", label: "事件", match: ["/events"] },
  { href: "/timeline", label: "时间线", match: ["/timeline"] },
];

const secondaryItems = [
  { href: "/graph", label: "图谱工作台", match: ["/graph"] },
  { href: "/review", label: "审核", match: ["/review"] },
  { href: "/operations", label: "运维", match: ["/operations"] },
];

export function Navigation() {
  const pathname = usePathname();
  const knowledgeActive = knowledgeItems.some((item) => isActivePath(pathname, item));
  const secondaryActive = secondaryItems.some((item) => isActivePath(pathname, item));

  return (
    <nav className="flex flex-wrap items-start gap-3 text-sm font-bold uppercase tracking-[0.16em]">
      {primaryItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={`nav-pill ${
            isActivePath(pathname, item) ? "nav-pill-active" : ""
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
  items: NavItem[];
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
              isActivePath(pathname, item) ? "bg-neon" : "bg-canvas"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>
    </details>
  );
}

type NavItem = {
  href: string;
  label: string;
  match?: string[];
};

function isActivePath(pathname: string, item: NavItem): boolean {
  const candidates = item.match ?? [item.href];
  return candidates.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}
