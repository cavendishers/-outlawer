"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch, setToken } from "@/lib/api";
import { Panel } from "@/components/panel";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123456");
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const data = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(data.access_token);
      router.push("/inbox");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    }
  }

  return (
    <main className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
      <Panel className="p-8" tone="story">
        <p className="font-display text-6xl uppercase">Access Gate</p>
        <p className="mt-6 max-w-xl text-xl font-bold leading-relaxed">
          登录后你将进入知识引擎的内环。默认种子账号已经准备好，先拿到令牌，再开始导入卷宗。
        </p>
      </Panel>

      <Panel className="p-8" tone="default">
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="text-sm font-black uppercase">Username</label>
          <input
            className="brutal-input text-lg"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
          <label className="text-sm font-black uppercase">Password</label>
          <input
            type="password"
            className="brutal-input text-lg"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button className="brutal-action brutal-action-primary mt-2 w-fit text-lg">
            进入内环
          </button>
          {error ? <p className="text-sm font-bold text-red-950">{error}</p> : null}
        </form>
      </Panel>
    </main>
  );
}
