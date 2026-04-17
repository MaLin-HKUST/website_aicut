"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";

type AuthResponse = {
  user: {
    username: string;
    role: "admin" | "user";
  };
};

export default function WelcomePage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);

  useEffect(() => {
    async function bootstrap() {
      const response = await fetch("/api/proxy/auth/me");
      if (!response.ok) {
        router.replace("/login");
        return;
      }

      const payload = (await response.json()) as AuthResponse;
      if (payload.user.role === "admin") {
        router.replace("/admin");
        return;
      }
      setUser(payload.user);
    }

    void bootstrap();
  }, []);

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  return (
    <UserWorkspaceShell onLogout={logout} title="Audio Workspace">
      <section className="rounded-[32px] border border-[#e1d7c7] bg-[#fdf9f2] p-6 shadow-panel">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-stone-500">Audio Workspace</p>
            <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-tight text-[#231815]">
              Hello{user ? `, ${user.username}` : ""}. 把文案直接转成可试听、可下载的音频。
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-stone-600">
              这里继续保留现有 TTS 工作台，同时新增 Smart Cut 和统一任务中心入口。Smart Cut 负责三段式粗剪工作流，
              任务中心负责统一查看状态、失败和最终下载。
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button className="h-11 px-5" onClick={() => router.push("/smart-cut")} type="button">
              智能气口剪辑
            </Button>
            <Button className="h-11 px-5" onClick={() => router.push("/tasks")} type="button" variant="secondary">
              任务中心
            </Button>
            <Button className="h-11 px-5" onClick={() => router.push("/tts")} type="button" variant="secondary">
              文案生成语音
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <Card className="rounded-[32px] border-[#e1d7c7] bg-[#fdf9f2] p-6 shadow-panel">
          <p className="text-xs uppercase tracking-[0.28em] text-stone-500">Workspace Mode</p>
          <div className="mt-5 space-y-4">
            <div className="rounded-[24px] border border-[#e1d7c7] bg-white p-4">
              <p className="text-sm text-stone-500">功能</p>
              <p className="mt-2 text-xl font-semibold text-[#231815]">智能气口剪辑</p>
            </div>
            <div className="rounded-[24px] border border-[#e1d7c7] bg-white p-4">
              <p className="text-sm text-stone-500">功能</p>
              <p className="mt-2 text-xl font-semibold text-[#231815]">任务中心</p>
            </div>
            <div className="rounded-[24px] border border-[#e1d7c7] bg-white p-4">
              <p className="text-sm text-stone-500">功能</p>
              <p className="mt-2 text-xl font-semibold text-[#231815]">文案生成语音</p>
            </div>
          </div>
        </Card>

        <Card className="rounded-[32px] border-[#e1d7c7] bg-[#fdf9f2] p-6 shadow-panel">
          <p className="text-xs uppercase tracking-[0.28em] text-stone-500">Current Scope</p>
          <div className="mt-5 space-y-4">
            <div className="rounded-[24px] border border-[#e1d7c7] bg-white p-4">
              <p className="text-sm text-stone-500">模式</p>
              <p className="mt-2 text-xl font-semibold text-[#231815]">Smart Cut 三段工作流 + TTS 工作台</p>
            </div>
            <div className="rounded-[24px] border border-[#e1d7c7] bg-white p-4">
              <p className="text-sm text-stone-500">结果</p>
              <p className="mt-2 text-xl font-semibold text-[#231815]">任务跟踪 + 最终下载</p>
            </div>
          </div>
        </Card>
      </section>
    </UserWorkspaceShell>
  );
}
