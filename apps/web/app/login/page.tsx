"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type LoginResponse = {
  user: {
    username: string;
    role: "admin" | "user";
  };
};

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/proxy/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? "Login failed");
      }

      const payload = (await response.json()) as LoginResponse;
      router.push(payload.user.role === "admin" ? "/admin" : "/welcome");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="grid w-full max-w-5xl gap-8 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="rounded-[36px] bg-[#2f241f] p-10 text-stone-100 shadow-panel">
          <p className="mb-4 text-sm uppercase tracking-[0.35em] text-stone-300">联系我们</p>
          <h1 className="max-w-md text-4xl font-semibold leading-tight">
            小马AI剪辑<br/>
            营销视频剪辑智能体
          </h1>
          <p className="mt-6 max-w-lg text-sm leading-7 text-stone-300">
            帮助企业完成视频剪辑的痛点<br/>
            线上营销的放大器<br/>
            重塑线上营销的打法
          </p>
        </section>

        <Card className="p-8 lg:p-10">
          <div className="mb-8">
            <h2 className="text-3xl font-semibold">登录</h2>
          </div>

          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="login-username">
                用户名
              </label>
              <Input
                id="login-username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="admin"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="login-password">
                密码
              </label>
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter password"
                required
              />
            </div>

            {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

            <Button className="w-full" disabled={submitting} type="submit">
              {submitting ? "登录中..." : "登录"}
            </Button>
          </form>
        </Card>
      </div>
    </main>
  );
}
