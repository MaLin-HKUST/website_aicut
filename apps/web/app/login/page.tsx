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
          <p className="mb-4 text-sm uppercase tracking-[0.35em] text-stone-300">Website AICut</p>
          <h1 className="max-w-md text-4xl font-semibold leading-tight">
            A minimal cloud-ready admin bootstrap for your internal video platform.
          </h1>
          <p className="mt-6 max-w-lg text-sm leading-7 text-stone-300">
            This slice focuses only on login, admin routing, company and user setup, and material metadata.
          </p>
        </section>

        <Card className="p-8 lg:p-10">
          <div className="mb-8">
            <p className="text-sm uppercase tracking-[0.3em] text-stone-500">Sign In</p>
            <h2 className="mt-2 text-3xl font-semibold">Enter your account</h2>
            <p className="mt-2 text-sm text-stone-500">Admin goes to the control panel. Other users go to the welcome page.</p>
          </div>

          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="login-username">
                Username
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
                Password
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
              {submitting ? "Signing in..." : "Login"}
            </Button>
          </form>
        </Card>
      </div>
    </main>
  );
}
