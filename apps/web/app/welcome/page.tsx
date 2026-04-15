"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

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
    <main className="min-h-screen p-6 lg:p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <section className="overflow-hidden rounded-[36px] bg-[#221814] p-8 text-stone-100 shadow-panel lg:p-10">
          <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-stone-300">Audio Workspace</p>
              <h1 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight">
                Hello{user ? `, ${user.username}` : ""}. 把文案直接转成可试听、可下载的音频。
              </h1>
              <p className="mt-5 max-w-xl text-sm leading-7 text-stone-300">
                这里先开放一个固定 HD 音色工作台。你输入文案，系统会直接调用 MiniMax 生成语音，并显示本次
                AITOKEN 消耗。
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button className="h-12 px-6 text-base" onClick={() => router.push("/tts")}>
                  文案生成语音
                </Button>
                <Button className="h-12 px-6 text-base text-stone-100 ring-white/20 hover:bg-white/10" variant="ghost" onClick={logout}>
                  Logout
                </Button>
              </div>
            </div>

            <Card className="border-white/10 bg-white/10 p-6 text-left text-stone-100 backdrop-blur">
              <p className="text-xs uppercase tracking-[0.28em] text-stone-300">Launch Panel</p>
              <div className="mt-5 space-y-4">
                <div className="rounded-[24px] border border-white/10 bg-black/15 p-4">
                  <p className="text-sm text-stone-300">功能</p>
                  <p className="mt-2 text-xl font-semibold">文案生成语音</p>
                </div>
                <div className="rounded-[24px] border border-white/10 bg-black/15 p-4">
                  <p className="text-sm text-stone-300">模式</p>
                  <p className="mt-2 text-xl font-semibold">MiniMax HD 固定音色</p>
                </div>
                <div className="rounded-[24px] border border-white/10 bg-black/15 p-4">
                  <p className="text-sm text-stone-300">结果</p>
                  <p className="mt-2 text-xl font-semibold">在线试听 + 下载音频</p>
                </div>
              </div>
            </Card>
          </div>
        </section>
      </div>
    </main>
  );
}
