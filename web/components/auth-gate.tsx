"use client";

import Link from "next/link";
import { ReactNode, useEffect, useState } from "react";

import { getToken } from "@/lib/api";
import { Panel } from "@/components/panel";

export function AuthGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(Boolean(getToken()));
    setReady(true);
  }, []);

  if (!ready) {
    return <div className="text-lg font-bold">系统校准中...</div>;
  }

  if (!authed) {
    return (
      <Panel className="p-8 max-w-xl" tone="default">
        <p className="text-2xl font-black uppercase">Access Denied</p>
        <p className="mt-4 text-lg">你还没有登录。先进入控制面板，拿到访问令牌。</p>
        <Link
          href="/login"
          className="brutal-action brutal-action-primary mt-6"
        >
          去登录
        </Link>
      </Panel>
    );
  }

  return <>{children}</>;
}
