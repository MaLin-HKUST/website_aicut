"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { UserWorkspaceShell } from "@/components/user-workspace-shell";

type AuthResponse = {
  user: {
    username: string;
    role: "admin" | "user";
    company_name: string | null;
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
  }, [router]);

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  // 点击文案生成语音时跳转
  useEffect(() => {
    if (typeof window !== "undefined") {
      // 监听按钮点击，直接跳转
      const handleClick = (e: MouseEvent) => {
        const target = e.target as HTMLElement;
        if (target.textContent?.includes("文案生成语音")) {
          router.push("/tts");
        }
      };
      document.addEventListener("click", handleClick);
      return () => document.removeEventListener("click", handleClick);
    }
  }, [router]);

  return (
    <UserWorkspaceShell
      activeItem="文案生成语音"
      companyName={user?.company_name ?? user?.username ?? null}
      onLogout={logout}
    >
      {/* 空内容，点击左侧按钮直接跳转 */}
      <div className="flex h-[60vh] items-center justify-center">
        <p className="text-slate-400">请点击左侧「文案生成语音」开始使用</p>
      </div>
    </UserWorkspaceShell>
  );
}
