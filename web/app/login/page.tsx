"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch, setToken } from "@/lib/api";
import { Panel } from "@/components/panel";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
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
    <main className="space-y-5">
      <section className="workbench-header">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="workbench-title">登录</h1>
              <span className="workbench-stamp bg-peach">受保护页面</span>
            </div>
            <p className="workbench-lede">
              使用访问令牌进入导入、档案、审核和图谱工作台；默认种子账号可用于本地开发验证。
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
        <Panel className="p-5" tone="story">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-black">访问说明</h2>
            <span className="workbench-stamp bg-canvas">Bearer Token</span>
          </div>
          <div className="mt-4 space-y-3 text-sm font-bold leading-relaxed md:text-base">
            <p>登录成功后，令牌会保存在当前浏览器，用于访问受保护的后台页面。</p>
            <p>如果需要切换账号，可从工具台退出后重新登录。</p>
          </div>
        </Panel>

        <Panel className="p-5" tone="default">
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <label className="grid gap-2 text-sm font-black">
              <span>账号</span>
              <input
                className="brutal-input text-base"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>
            <label className="grid gap-2 text-sm font-black">
              <span>密码</span>
              <input
                type="password"
                className="brutal-input text-base"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button className="tool-action w-fit bg-neon">
              登录并进入导入页
            </button>
            {error ? <p className="text-sm font-bold text-red-950">{error}</p> : null}
          </form>
        </Panel>
      </section>
    </main>
  );
}
