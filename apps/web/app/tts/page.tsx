"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { UserWorkspaceShell } from "@/components/user-workspace-shell";

type AuthResponse = {
  user: {
    username: string;
    role: "admin" | "user";
    company_name: string | null;
  };
};

type UserUsageResponse = {
  credits_used: number;
  credits_limit: number | null;
};

type GenerateAudioResponse = {
  audio_base64: string;
  mime_type: string;
  file_name: string;
  usage_credits: number;
  usage_characters: number;
  monthly_total_used: number;
  monthly_limit: number | null;
};

const EXAMPLE_COPY = [
  "今晚的直播脚本已经整理好了，请你用干净、稳定、自然的叙述方式读出来。",
  "欢迎来到新一期产品介绍，我们会在三分钟内带你快速了解本次升级亮点。",
  "这段语音用于视频口播，请保持节奏清晰、停顿自然、结尾收得干净。",
];

const DEFAULT_TEXT = "";

const FIXED_VOICE_LABEL = "MiniMax HD 固定音色";

function base64ToBlob(base64: string, mimeType: string) {
  const binary = atob(base64);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new Blob([bytes], { type: mimeType });
}

export default function TTSPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const [text, setText] = useState(DEFAULT_TEXT);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioFileName, setAudioFileName] = useState<string | null>(null);
  const [usageCredits, setUsageCredits] = useState(0);
  const [monthlyTotal, setMonthlyTotal] = useState(0);
  const [monthlyLimit, setMonthlyLimit] = useState<number | null>(null);

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
      
      // 加载当前用户月度消耗
      const usageRes = await fetch("/api/proxy/user/usage");
      if (usageRes.ok) {
        const usage = (await usageRes.json()) as UserUsageResponse;
        setMonthlyTotal(usage.credits_used);
        setMonthlyLimit(usage.credits_limit);
      }
    }

    void bootstrap();
  }, [router]);

  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  const characterCount = useMemo(() => text.length, [text]);

  function updateText(nextText: string) {
    setText(nextText);
    setUsageCredits(nextText.length);
    setError(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
      setAudioFileName(null);
    }
  }

  function onTextChange(event: ChangeEvent<HTMLTextAreaElement>) {
    updateText(event.target.value);
  }

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/proxy/user/tts/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? "生成音频失败");
      }

      const payload = (await response.json()) as GenerateAudioResponse;
      const blob = base64ToBlob(payload.audio_base64, payload.mime_type);
      const nextAudioUrl = URL.createObjectURL(blob);

      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }

      setAudioUrl(nextAudioUrl);
      setAudioFileName(payload.file_name);
      setUsageCredits(payload.usage_credits);
      setMonthlyTotal(payload.monthly_total_used);
      setMonthlyLimit(payload.monthly_limit);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成音频失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <UserWorkspaceShell
      activeItem="文案生成语音"
      companyName={user?.company_name ?? user?.username ?? null}
      onLogout={logout}
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <form onSubmit={onSubmit}>
          <Card className="rounded-[28px] border-[#cad4de] bg-white p-6 lg:p-7">
            <div className="rounded-[24px] bg-[#f3f7fb] p-5">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-slate-500">任务操作页</p>
                  <h2 className="mt-3 text-3xl font-semibold text-[#17202a]">把文案直接转成音频</h2>
                </div>
                <div className="rounded-full bg-[#18364e] px-4 py-2 text-sm text-white">
                  本月累计TOKEN：{monthlyTotal.toLocaleString()}{monthlyLimit ? ` / ${monthlyLimit.toLocaleString()}` : ""}
                </div>
              </div>

              <div className="mt-5 rounded-[24px] border border-[#cad4de] bg-white p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">输入文案</p>
                    <p className="mt-2 text-sm text-slate-600">{characterCount} characters</p>
                  </div>
                  <div className="rounded-full bg-[#18364e] px-4 py-2 text-xs uppercase tracking-[0.24em] text-white">固定音色</div>
                </div>

                <label className="mt-4 block text-xs uppercase tracking-[0.28em] text-slate-500" htmlFor="tts-text">
                  Script
                </label>
                <textarea
                  id="tts-text"
                  className="mt-3 min-h-[360px] w-full resize-none rounded-[24px] border border-[#cad4de] bg-[#fbfdff] px-5 py-4 text-base leading-8 text-foreground outline-none transition focus:border-[#18364e] focus:ring-2 focus:ring-[#18364e]/15"
                  maxLength={9999}
                  onChange={onTextChange}
                  placeholder="输入你要转成语音的文案"
                  required
                  value={text}
                />
              </div>
            </div>

            {error ? <p className="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

            <div className="mt-6 flex flex-wrap gap-3">
              <Button className="h-12 px-7 bg-[#18364e] text-base hover:bg-[#102739]" disabled={submitting} type="submit">
                {submitting ? "生成中..." : "生成音频"}
              </Button>
            </div>
          </Card>
        </form>

        <div className="space-y-4">
          <Card className="rounded-[28px] border-[#cad4de] bg-[#18364e] p-5 text-white">
            <p className="text-xs uppercase tracking-[0.28em] text-slate-300">当前音色</p>
            <p className="mt-3 text-xl font-semibold">康迪</p>
          </Card>

          <Card className="rounded-[28px] border-[#cad4de] bg-white p-5">
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500">生成结果</p>
            <h2 className="mt-3 text-2xl font-semibold text-[#17202a]">输出预览</h2>
            <div className="mt-5 rounded-[24px] border border-dashed border-[#cad4de] bg-[#f6f9fc] p-4" data-testid="tts-result-panel">
              {audioUrl ? (
                <div className="space-y-4">
                  <div className="rounded-[20px] bg-white p-4">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">文件</p>
                    <p className="mt-2 break-all text-lg font-semibold text-[#17202a]">{audioFileName}</p>
                  </div>
                  <audio className="w-full" controls src={audioUrl} />
                  <a download={audioFileName ?? "tts-audio.mp3"} href={audioUrl}>
                    <Button className="h-11 w-full bg-[#18364e] hover:bg-[#102739]" type="button">
                      下载音频
                    </Button>
                  </a>
                </div>
              ) : (
                <div className="space-y-3 py-8 text-center">
                  <p className="text-base font-semibold text-[#17202a]">还没有生成音频</p>
                  <p className="text-sm leading-7 text-slate-500">点击左侧生成按钮后，这里会显示播放器和下载入口。</p>
                </div>
              )}
            </div>
          </Card>


        </div>
      </div>
    </UserWorkspaceShell>
  );
}
