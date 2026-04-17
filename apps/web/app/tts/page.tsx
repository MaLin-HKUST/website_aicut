"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";

type AuthResponse = {
  user: {
    username: string;
    role: "admin" | "user";
  };
};

type GenerateAudioResponse = {
  audio_base64: string;
  mime_type: string;
  file_name: string;
  usage_credits: number;
  usage_characters: number;
};

const EXAMPLE_COPY = [
  "今晚的直播脚本已经整理好了，请你用干净、稳定、自然的叙述方式读出来。",
  "欢迎来到新一期产品介绍，我们会在三分钟内带你快速了解本次升级亮点。",
  "这段语音用于视频口播，请保持节奏清晰、停顿自然、结尾收得干净。",
];

const FIXED_VOICE_LABEL = "MiniMax HD 固定音色";

function base64ToBlob(base64: string, mimeType: string) {
  const binary = atob(base64);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new Blob([bytes], { type: mimeType });
}

export default function TTSPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const [text, setText] = useState(EXAMPLE_COPY[0]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioFileName, setAudioFileName] = useState<string | null>(null);
  const [usageCredits, setUsageCredits] = useState(EXAMPLE_COPY[0].length);
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成音频失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <UserWorkspaceShell
      activeItem="tts"
      currentUser={user?.username ?? "..."}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <section className="rounded-[40px] border border-[#e5dacd] bg-[#f7efe2] p-8 shadow-panel">
        <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
          <form className="space-y-5" onSubmit={onSubmit}>
            <Card className="rounded-[32px] border-[#e5dacd] bg-white p-7 shadow-panel">
              <div className="rounded-[28px] bg-[#f3f0ea] p-5">
                <div className="flex flex-col gap-4 border-b border-[#e6dccf] pb-5 xl:flex-row xl:items-center xl:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-stone-500">任务操作页</p>
                    <h2 className="mt-3 text-5xl font-semibold leading-tight text-[#241714]">把文案直接转成音频</h2>
                  </div>
                  <div className="rounded-full bg-[#213c56] px-5 py-3 text-sm font-semibold text-white">
                    本月累计TOKEN：{usageCredits}
                  </div>
                </div>

                <div className="mt-5 rounded-[28px] border border-[#d9d0c1] bg-white p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-stone-500">输入文案</p>
                      <p className="mt-2 text-sm text-stone-500">{characterCount} characters</p>
                    </div>
                    <div className="rounded-full bg-[#213c56] px-5 py-3 text-xs font-semibold uppercase tracking-[0.24em] text-white">
                      固定音色
                    </div>
                  </div>

                  <div className="mt-5 border-t border-dashed border-[#e8ddcf] pt-5">
                    <p className="text-xs uppercase tracking-[0.32em] text-stone-500">Script</p>
                    <textarea
                      id="tts-text"
                      className="mt-4 min-h-[360px] w-full resize-none rounded-[28px] border border-[#d8cebf] bg-[#fffdfa] px-5 py-5 text-[17px] leading-9 text-foreground outline-none transition focus:border-[#213c56] focus:ring-2 focus:ring-[#213c56]/15"
                      maxLength={9999}
                      onChange={onTextChange}
                      placeholder="输入你要转成语音的文案"
                      required
                      value={text}
                    />

                    <div className="mt-4 flex items-center justify-between text-sm text-stone-500">
                      <p>{characterCount} characters</p>
                      <p>Signed in as {user?.username ?? "..."}</p>
                    </div>
                  </div>
                </div>

                {error ? <p className="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

                <div className="mt-6 flex flex-wrap gap-3">
                  <Button className="h-12 rounded-full px-8 text-base" disabled={submitting} type="submit">
                    {submitting ? "生成中..." : "生成音频"}
                  </Button>
                  <Button
                    className="h-12 rounded-full px-8 text-base"
                    disabled={submitting}
                    onClick={() => updateText(EXAMPLE_COPY[1])}
                    type="button"
                    variant="secondary"
                  >
                    替换示例文案
                  </Button>
                </div>
              </div>
            </Card>
          </form>

          <div className="space-y-5">
            <Card className="rounded-[32px] border-[#e5dacd] bg-[#213c56] p-6 text-white">
              <p className="text-xs uppercase tracking-[0.28em] text-slate-200">当前音色</p>
              <p className="mt-4 text-3xl font-semibold">{FIXED_VOICE_LABEL}</p>
            </Card>

            <Card className="rounded-[32px] border-[#e5dacd] bg-white p-6 shadow-panel">
              <p className="text-xs uppercase tracking-[0.28em] text-stone-500">生成结果</p>
              <h3 className="mt-3 text-4xl font-semibold text-[#241714]">输出预览</h3>
              <div className="mt-6 rounded-[28px] border border-dashed border-[#dccab6] bg-[#fbf8f3] p-5" data-testid="tts-result-panel">
                {audioUrl ? (
                  <div className="space-y-4">
                    <div className="rounded-[22px] bg-[#f7efe5] p-4">
                      <p className="text-xs uppercase tracking-[0.28em] text-stone-500">文件</p>
                      <p className="mt-2 break-all text-lg font-semibold text-[#231815]">{audioFileName}</p>
                    </div>
                    <audio className="w-full" controls src={audioUrl} />
                    <a download={audioFileName ?? "tts-audio.mp3"} href={audioUrl}>
                      <Button className="h-11 w-full text-base" type="button">
                        下载音频
                      </Button>
                    </a>
                  </div>
                ) : (
                  <div className="space-y-3 py-10 text-center">
                    <p className="text-2xl font-semibold text-[#241714]">还没有生成音频</p>
                    <p className="text-sm leading-7 text-stone-500">点击左侧生成按钮后，这里会显示播放器和下载入口。</p>
                  </div>
                )}
              </div>
            </Card>

            <Card className="rounded-[32px] border-[#2b201d] bg-[#2b201d] p-6 text-stone-100 shadow-panel">
              <p className="text-xs uppercase tracking-[0.3em] text-stone-300">Prompt Ideas</p>
              <h3 className="mt-3 text-3xl font-semibold">快速替换常用文案</h3>
              <div className="mt-5 space-y-3">
                {EXAMPLE_COPY.map((sample) => (
                  <button
                    key={sample}
                    className="w-full rounded-[24px] border border-white/10 bg-white/5 p-4 text-left text-sm leading-8 text-stone-200 transition hover:bg-white/10"
                    onClick={() => updateText(sample)}
                    type="button"
                  >
                    {sample}
                  </button>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </section>
    </UserWorkspaceShell>
  );
}
