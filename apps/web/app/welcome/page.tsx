"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Card } from "@/components/ui/card";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { AuthResponse } from "@/lib/auth";

export default function WelcomePage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const workspace = useUserWorkspaceData(user?.username, user?.company_id);

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
    <UserWorkspaceShell
      activeItem="marketing-video"
      currentUser={user?.username ?? "..."}
      headline={user?.company_name ? `你好，${user.company_name}，小马AI准备就绪~` : undefined}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <Card className="min-h-[640px] rounded-[32px] border-[#e5dacd] bg-[#f8f5ef] p-5 shadow-panel sm:p-7">
        <div className="mx-auto flex h-full max-w-5xl flex-col justify-center gap-5">
          <div className="text-center">
            <p className="text-xs tracking-[0.24em] text-stone-500">工作台入口</p>
            <h2 className="mt-3 text-[28px] font-semibold text-[#241714]">选择你要开始的任务</h2>
            <p className="mt-3 text-sm leading-7 text-stone-500">营销视频先开放 TONGAN 标准模式；Smart Cut 和文案生成语音保持原入口。</p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <button
              className="rounded-[28px] border border-[#e4dacb] bg-white p-5 text-left shadow-sm transition hover:bg-[#fffaf5]"
              onClick={() => router.push("/marketing-video")}
              type="button"
            >
              <p className="text-sm tracking-[0.2em] text-stone-500">TONGAN</p>
              <p className="mt-3 text-xl font-semibold text-[#241714]">生成营销视频</p>
              <p className="mt-3 text-sm leading-7 text-stone-500">上传 TXT 文案，创建标准营销视频任务。</p>
            </button>
            <button
              className="rounded-[28px] border border-[#e4dacb] bg-white p-5 text-left shadow-sm transition hover:bg-[#fffaf5]"
              onClick={() => router.push("/smart-cut")}
              type="button"
            >
              <p className="text-sm tracking-[0.2em] text-stone-500">SMART CUT</p>
              <p className="mt-3 text-xl font-semibold text-[#241714]">智能剪气口</p>
              <p className="mt-3 text-sm leading-7 text-stone-500">围绕显式主任务卡继续剪辑流程。</p>
            </button>
            <button
              className="rounded-[28px] border border-[#e4dacb] bg-white p-5 text-left shadow-sm transition hover:bg-[#fffaf5]"
              onClick={() => router.push("/tts")}
              type="button"
            >
              <p className="text-sm tracking-[0.2em] text-stone-500">TTS</p>
              <p className="mt-3 text-xl font-semibold text-[#241714]">文案生成语音</p>
              <p className="mt-3 text-sm leading-7 text-stone-500">输入文案并生成语音素材。</p>
            </button>
          </div>
        </div>
      </Card>
    </UserWorkspaceShell>
  );
}
