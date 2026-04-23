"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { Card } from "@/components/ui/card";
import { AuthResponse } from "@/lib/auth";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";

export function SmartCutDisabledView() {
  const router = useRouter();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const workspace = useUserWorkspaceData(user?.username);

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
  }, [router]);

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  return (
    <UserWorkspaceShell
      activeItem="smart-cut"
      currentUser={user?.username ?? "..."}
      headline={user?.company_name ? `你好，${user.company_name}，智能剪气口正在重构中` : "智能剪气口正在重构中"}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <Card className="flex min-h-[640px] items-center justify-center rounded-[32px] border-[#e5dacd] bg-[#f8f5ef] shadow-panel">
        <div className="max-w-2xl space-y-4 text-center">
          <p className="text-2xl font-semibold text-[#241714]">Smart Cut 入口已关闭</p>
          <p className="text-sm leading-7 text-stone-500">
            当前线上 Smart Cut 正在做任务卡模型重构。旧版隐藏草稿、试听和生成入口已经全部下线，避免继续产生分裂状态。
          </p>
          <p className="text-sm leading-7 text-stone-500">
            已完成任务仍可在左侧「任务列表」查看和下载。新的重构版本上线后，这里会恢复为新的显式任务入口。
          </p>
        </div>
      </Card>
    </UserWorkspaceShell>
  );
}
