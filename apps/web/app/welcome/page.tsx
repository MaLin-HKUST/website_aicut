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
  }, []);

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  return (
    <UserWorkspaceShell
      activeItem="tts"
      currentUser={user?.username ?? "..."}
      headline={user?.company_name ? `你好，${user.company_name}，小马AI准备就绪~` : undefined}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <Card className="flex min-h-[640px] items-center justify-center rounded-[32px] border-[#e5dacd] bg-[#f8f5ef] shadow-panel">
        <div className="space-y-4 text-center">
          <p className="text-lg font-medium text-stone-400">请点击左侧「文案生成语音」开始使用</p>
          <p className="text-sm text-stone-400">后续你也可以通过左侧任务栏进入智能气口剪辑和任务列表。</p>
        </div>
      </Card>
    </UserWorkspaceShell>
  );
}
