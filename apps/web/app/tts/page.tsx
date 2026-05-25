"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { AuthResponse } from "@/lib/auth";
import { KDT_TTS_VOICES, KdtTtsVoiceName } from "@/lib/tts-voices";

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
  const [selectedVoice, setSelectedVoice] = useState<KdtTtsVoiceName>("康迪");
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
        body: JSON.stringify({ text, voice_name: selectedVoice }),
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
      headline={user?.company_name ? `你好，${user.company_name}，小马AI准备就绪~` : undefined}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <section className="rounded-[34px] border border-[#e3e3df] bg-[#f0f2f4] p-5 shadow-[0_10px_28px_rgba(60,66,74,0.05)] lg:p-6">
        <div className="grid gap-5 xl:grid-cols-[1.34fr_0.66fr]">
          <form className="space-y-5" onSubmit={onSubmit}>
            <Card className="rounded-[32px] border-[#e3e3df] bg-[#fffefb] p-5 shadow-[0_8px_20px_rgba(60,66,74,0.04)]">
              <div className="flex flex-col gap-4 border-b border-[#e3e0d9] pb-5 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-[11px] tracking-[0.28em] text-stone-400">任务操作页</p>
                  <h2 className="mt-3 max-w-[540px] text-[44px] font-semibold leading-[1.02] text-[#241714]">
                    把文案直接转成音频
                  </h2>
                </div>
                <div className="rounded-full bg-[#243444] px-5 py-2.5 text-sm font-semibold text-white">
                  本月累计TOKEN：{usageCredits}
                </div>
              </div>

              <div className="mt-5 rounded-[28px] border border-[#e3dfd7] bg-white px-4 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[11px] tracking-[0.24em] text-stone-400">输入文案</p>
                    <p className="mt-2 text-[15px] text-stone-500">{characterCount} characters</p>
                  </div>
                </div>

                <div className="mt-5 border-t border-dashed border-[#e6e0d6] pt-5">
                  <p className="text-[11px] tracking-[0.42em] text-stone-400">S C R I P T</p>
                  <textarea
                    id="tts-text"
                    className="mt-4 min-h-[360px] w-full resize-none rounded-[28px] border border-[#d7cfc3] bg-[#fffefb] px-5 py-5 text-[16px] leading-9 text-[#2a1f1b] outline-none transition placeholder:text-stone-400 focus:border-[#243444] focus:ring-1 focus:ring-[#243444]/10"
                    maxLength={9999}
                    onChange={onTextChange}
                    placeholder="输入你要转成语音的文案"
                    required
                    value={text}
                  />

                  <div className="mt-4 flex items-center justify-between text-[14px] text-stone-500">
                    <p>{characterCount} characters</p>
                    <p>当前账号：{user?.username ?? "..."}</p>
                  </div>
                </div>
              </div>

              {error ? <p className="mt-5 rounded-[20px] bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

              <div className="mt-6 flex flex-wrap gap-3">
                <Button className="h-12 rounded-full bg-[#bf6b45] px-8 text-base text-white hover:bg-[#ab5d39]" disabled={submitting} type="submit">
                  {submitting ? "生成中..." : "生成音频"}
                </Button>
              </div>
            </Card>
          </form>

          <div className="space-y-5">
            <Card className="rounded-[28px] border-[#d8d9d5] bg-[#243444] p-5 text-white shadow-[0_10px_22px_rgba(36,52,68,0.12)]">
              <label className="text-[11px] tracking-[0.24em] text-slate-200" htmlFor="tts-voice">
                当前音色
              </label>
              <select
                className="mt-4 h-12 w-full rounded-[18px] border border-white/20 bg-white px-4 text-[18px] font-semibold text-[#243444] outline-none transition focus:border-white focus:ring-2 focus:ring-white/30 disabled:cursor-not-allowed disabled:opacity-70"
                disabled={submitting}
                id="tts-voice"
                onChange={(event) => setSelectedVoice(event.target.value as KdtTtsVoiceName)}
                value={selectedVoice}
              >
                {KDT_TTS_VOICES.map((voice) => (
                  <option key={voice.value} value={voice.value}>
                    {voice.label}
                  </option>
                ))}
              </select>
              <p className="mt-3 text-sm text-slate-200/80">选择音色</p>
            </Card>

            <Card className="rounded-[28px] border-[#e3e3df] bg-[#fffefb] p-5 shadow-[0_8px_20px_rgba(60,66,74,0.04)]">
              <p className="text-[11px] tracking-[0.24em] text-stone-400">生成结果</p>
              <h3 className="mt-3 text-[30px] font-semibold leading-none text-[#241714]">输出预览</h3>
              <div className="mt-5 min-h-[360px] rounded-[26px] border border-dashed border-[#ddd7cc] bg-[#fcfbf8] p-6" data-testid="tts-result-panel">
                {audioUrl ? (
                  <div className="space-y-4">
                    <div className="rounded-[22px] bg-[#f7efe5] p-4">
                      <p className="text-[11px] tracking-[0.28em] text-stone-400">文件</p>
                      <p className="mt-2 break-all text-lg font-semibold text-[#231815]">{audioFileName}</p>
                    </div>
                    <audio className="w-full" controls src={audioUrl} />
                    <a download={audioFileName ?? "tts-audio.mp3"} href={audioUrl}>
                      <Button className="h-11 w-full bg-[#243444] text-base text-white hover:bg-[#2d4052]" type="button">
                        下载音频
                      </Button>
                    </a>
                  </div>
                ) : (
                  <div className="space-y-4 py-10 text-center">
                    <p className="text-[17px] font-semibold text-[#241714]">还没有生成音频</p>
                    <p className="mx-auto max-w-[240px] text-sm leading-7 text-stone-500">点击左侧生成按钮后，这里会显示播放器和下载入口。</p>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      </section>
    </UserWorkspaceShell>
  );
}
