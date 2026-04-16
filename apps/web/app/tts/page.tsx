"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

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
    <main className="min-h-screen p-4 lg:p-8">
      <div className="mx-auto max-w-7xl">
        <section className="relative overflow-hidden rounded-[40px] border border-[#e5dacd] bg-[#f7efe2] px-5 py-6 shadow-panel lg:px-8 lg:py-8">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-48 bg-[radial-gradient(circle_at_top,rgba(196,99,61,0.24),transparent_58%)]"
          />
          <div className="relative flex flex-col gap-4 border-b border-[#dfcfbe] pb-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-stone-500">Text To Speech</p>
              <h1 className="mt-3 text-3xl font-semibold leading-tight text-[#241714] lg:text-5xl">
                输入文案，直接生成可用音频。
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-stone-600">
                中间工作区保留了最核心的操作链路：输入文案、查看 credit 消耗、生成音频、在线试听并下载。
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button className="h-11 px-5" onClick={() => router.push("/welcome")} type="button" variant="secondary">
                返回工作台
              </Button>
              <Button className="h-11 px-5" variant="ghost" onClick={logout}>
                Logout
              </Button>
            </div>
          </div>

          <div className="relative mt-6 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <form className="space-y-5" onSubmit={onSubmit}>
              <Card className="rounded-[32px] border-[#eadfce] bg-[#fffaf2] p-6 lg:p-7">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-stone-500">Credit Usage Preview</p>
                    <p className="mt-2 text-2xl font-semibold text-[#231815]">音色AITOKEN消耗：{usageCredits}</p>
                  </div>
                  <div className="rounded-full border border-[#e5d7c5] bg-white px-4 py-2 text-xs uppercase tracking-[0.24em] text-stone-500">
                    HD · 1 Character = 1 Credit
                  </div>
                </div>

                <div className="mt-5 rounded-[28px] border border-[#e7dac9] bg-white p-4">
                  <div className="flex items-center justify-between gap-3 border-b border-dashed border-[#eadfce] pb-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.28em] text-stone-500">Voice</p>
                      <p className="mt-2 text-lg font-semibold text-[#231815]">{FIXED_VOICE_LABEL}</p>
                    </div>
                    <div className="rounded-full bg-[#f5ebdf] px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#9a5d3c]">
                      Fixed
                    </div>
                  </div>

                  <label className="mt-4 block text-xs uppercase tracking-[0.28em] text-stone-500" htmlFor="tts-text">
                    Script
                  </label>
                  <textarea
                    id="tts-text"
                    className="mt-3 min-h-[360px] w-full resize-none rounded-[24px] border border-[#eadfce] bg-[#fffdf9] px-5 py-4 text-base leading-8 text-foreground outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20"
                    maxLength={9999}
                    onChange={onTextChange}
                    placeholder="输入你要转成语音的文案"
                    required
                    value={text}
                  />

                  <div className="mt-3 flex items-center justify-between text-sm text-stone-500">
                    <p>{characterCount} characters</p>
                    <p>Signed in as {user?.username ?? "..."}</p>
                  </div>
                </div>

                {error ? <p className="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

                <div className="mt-6 flex flex-wrap gap-3">
                  <Button className="h-12 px-7 text-base" disabled={submitting} type="submit">
                    {submitting ? "生成中..." : "生成音频"}
                  </Button>
                  <Button
                    className="h-12 px-7 text-base"
                    disabled={submitting}
                    onClick={() => updateText(EXAMPLE_COPY[1])}
                    type="button"
                    variant="secondary"
                  >
                    替换示例文案
                  </Button>
                </div>
              </Card>
            </form>

            <div className="space-y-5">
              <Card className="rounded-[32px] border-[#eadfce] bg-[#fffaf2] p-6 lg:p-7">
                <p className="text-xs uppercase tracking-[0.3em] text-stone-500">Output</p>
                <h2 className="mt-3 text-2xl font-semibold text-[#231815]">生成结果</h2>
                <p className="mt-3 text-sm leading-7 text-stone-600">
                  生成成功后，音频会出现在这里。你可以直接试听，也可以下载到本地继续用于视频口播。
                </p>

                <div className="mt-6 rounded-[28px] border border-dashed border-[#dccab6] bg-white p-5" data-testid="tts-result-panel">
                  {audioUrl ? (
                    <div className="space-y-4">
                      <div className="rounded-[22px] bg-[#f7efe5] p-4">
                        <p className="text-xs uppercase tracking-[0.28em] text-stone-500">File</p>
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
                    <div className="space-y-3 py-8 text-center">
                      <p className="text-base font-semibold text-[#231815]">还没有生成音频</p>
                      <p className="text-sm leading-7 text-stone-500">
                        点击左侧的生成按钮后，这里会显示播放器和下载入口。
                      </p>
                    </div>
                  )}
                </div>
              </Card>

              <Card className="rounded-[32px] border-[#eadfce] bg-[#2b201d] p-6 text-stone-100 lg:p-7">
                <p className="text-xs uppercase tracking-[0.3em] text-stone-300">Prompt Ideas</p>
                <h2 className="mt-3 text-2xl font-semibold">快速替换常用文案</h2>
                <div className="mt-5 space-y-3">
                  {EXAMPLE_COPY.map((sample) => (
                    <button
                      key={sample}
                      className="w-full rounded-[24px] border border-white/10 bg-white/5 p-4 text-left text-sm leading-7 text-stone-200 transition hover:bg-white/10"
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
      </div>
    </main>
  );
}
