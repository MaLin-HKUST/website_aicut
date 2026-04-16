"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SmartCutScriptEditor } from "@/components/smart-cut/script-editor";
import {
  createSmartCutTask,
  formatTaskStatus,
  getSmartCutEdits,
  getSmartCutTask,
  listSmartCutTasks,
  SmartCutEdit,
  SmartCutTask,
  SmartCutTaskSummary,
  startAnalyze,
  startFinalize,
  startPreview,
  uploadDirectInputs,
} from "@/lib/smart-cut";

type AuthResponse = {
  user: {
    username: string;
    role: "admin" | "user";
  };
};

function formatTime(value: string) {
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function statusTone(status: string) {
  if (status === "success") return "bg-emerald-100 text-emerald-700";
  if (status === "failed") return "bg-red-100 text-red-700";
  if (status.includes("preview") || status.includes("finalize")) return "bg-amber-100 text-amber-700";
  return "bg-stone-100 text-stone-700";
}

export function SmartCutLandingPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<SmartCutTaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);

  useEffect(() => {
    async function bootstrap() {
      const authResponse = await fetch("/api/proxy/auth/me");
      if (!authResponse.ok) {
        router.replace("/login");
        return;
      }

      const authPayload = (await authResponse.json()) as AuthResponse;
      if (authPayload.user.role === "admin") {
        router.replace("/admin");
        return;
      }
      setUser(authPayload.user);

      try {
        const taskList = await listSmartCutTasks(authPayload.user.username);
        setTasks(taskList);
      } catch (err) {
        setError(err instanceof Error ? err.message : "读取任务失败");
      } finally {
        setLoading(false);
      }
    }

    void bootstrap();
  }, [router]);

  async function createTask() {
    if (!user) return;
    setCreating(true);
    setError(null);
    try {
      const task = await createSmartCutTask(user.username);
      router.push(`/smart-cut/${task.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="min-h-screen p-4 lg:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="relative overflow-hidden rounded-[40px] border border-[#e5dacd] bg-[#f7efe2] px-5 py-6 shadow-panel lg:px-8 lg:py-8">
          <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-48 bg-[radial-gradient(circle_at_top,rgba(196,99,61,0.24),transparent_58%)]" />
          <div className="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-stone-500">Smart Cut</p>
              <h1 className="mt-3 text-3xl font-semibold leading-tight text-[#241714] lg:text-5xl">三段式智能气口剪辑工作台</h1>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-stone-600">
                这里负责上传原视频、调整删除线脚本、生成试听，并把最终视频任务送入统一任务队列。最终下载与结果追踪会继续放在任务中心。
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button className="h-11 px-5" disabled={creating} onClick={createTask} type="button">
                {creating ? "创建中..." : "开始新任务"}
              </Button>
              <Button className="h-11 px-5" onClick={() => router.push("/welcome")} type="button" variant="secondary">
                返回工作台
              </Button>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card className="rounded-[32px] border-[#eadfce] bg-[#fffaf2] p-6 lg:p-7">
            <p className="text-xs uppercase tracking-[0.3em] text-stone-500">Workflow</p>
            <h2 className="mt-3 text-2xl font-semibold text-[#231815]">固定三段</h2>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {[
                ["Analyze", "上传视频与标准文案，启动分析，拿到 script。"],
                ["Preview", "只在前端看删除线并调整，生成试听音轨。"],
                ["Finalize", "确认输出规格与 AI 投喂，把最终视频任务提交到任务中心。"],
              ].map(([title, description]) => (
                <div key={title} className="rounded-[24px] border border-[#eadfce] bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.28em] text-stone-500">{title}</p>
                  <p className="mt-3 text-base font-semibold text-[#231815]">{title}</p>
                  <p className="mt-3 text-sm leading-7 text-stone-600">{description}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="rounded-[32px] border-[#eadfce] bg-[#2b201d] p-6 text-stone-100 lg:p-7">
            <p className="text-xs uppercase tracking-[0.3em] text-stone-300">Recent Tasks</p>
            <h2 className="mt-3 text-2xl font-semibold">最近任务</h2>
            {error ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
            <div className="mt-5 space-y-3">
              {loading ? (
                <p className="text-sm text-stone-300">正在读取任务…</p>
              ) : tasks.length === 0 ? (
                <div className="rounded-[24px] border border-white/10 bg-black/15 p-4 text-sm text-stone-300">还没有任务，先创建一个 Smart Cut 任务。</div>
              ) : (
                tasks.slice(0, 5).map((task) => (
                  <button
                    key={task.id}
                    className="block w-full rounded-[24px] border border-white/10 bg-black/15 p-4 text-left transition hover:bg-black/25"
                    onClick={() => router.push(`/smart-cut/${task.id}`)}
                    type="button"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold">{task.id}</p>
                      <span className={`rounded-full px-3 py-1 text-xs ${statusTone(task.status)}`}>{task.status}</span>
                    </div>
                    <p className="mt-2 text-sm text-stone-300">{task.current_stage ?? "pending"}</p>
                    <p className="mt-3 text-xs uppercase tracking-[0.2em] text-stone-400">{formatTime(task.updated_at)}</p>
                  </button>
                ))
              )}
            </div>
          </Card>
        </section>
      </div>
    </main>
  );
}

export function SmartCutWorkspace({ taskId }: { taskId: string }) {
  const router = useRouter();
  const [task, setTask] = useState<SmartCutTask | null>(null);
  const [edits, setEdits] = useState<SmartCutEdit[]>([]);
  const [scriptDraft, setScriptDraft] = useState("");
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [outputMode, setOutputMode] = useState<"original" | "vertical_1080p">("original");
  const [feedToAi, setFeedToAi] = useState(true);
  const [busyAction, setBusyAction] = useState<"upload" | "analyze" | "preview" | "finalize" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const latestEdit = edits[0] ?? null;

  async function bootstrap() {
    const authResponse = await fetch("/api/proxy/auth/me");
    if (!authResponse.ok) {
      router.replace("/login");
      return;
    }

    const authPayload = (await authResponse.json()) as AuthResponse;
    if (authPayload.user.role === "admin") {
      router.replace("/admin");
      return;
    }

    const [taskData, editData] = await Promise.all([getSmartCutTask(taskId), getSmartCutEdits(taskId).catch(() => [])]);

    setTask(taskData);
    setEdits(editData);
    setOutputMode(taskData.output_mode ?? "original");
    setFeedToAi(taskData.feed_to_ai ?? true);

    const sourceScript = editData[0]?.edited_script ?? taskData.analyze_script ?? "";
    if (sourceScript) {
      setScriptDraft(sourceScript);
    }
  }

  useEffect(() => {
    void bootstrap().catch((err) => {
      setError(err instanceof Error ? err.message : "读取任务失败");
    });
  }, [taskId]);

  useEffect(() => {
    if (!task) return;
    if (!["analyzing", "previewing", "finalizing"].includes(task.status)) return;

    const timer = window.setInterval(() => {
      void bootstrap().catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [task?.status]);

  const canUpload = task && task.status === "waiting_upload";
  const canAnalyze = task && task.status === "ready_analyze";
  const canPreview = task && ["waiting_user", "preview_failed"].includes(task.status) && scriptDraft.length > 0;
  const canFinalize = task && ["waiting_user", "finalize_failed"].includes(task.status);

  async function handleUpload() {
    if (!task || !videoFile || !referenceFile) return;
    setBusyAction("upload");
    setError(null);
    setNotice(null);

    try {
      const nextTask = await uploadDirectInputs(task.id, videoFile, referenceFile);
      setTask(nextTask);
      setNotice("输入文件已上传，可以开始分析。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleAnalyze() {
    if (!task) return;
    setBusyAction("analyze");
    setError(null);
    setNotice(null);
    try {
      const nextTask = await startAnalyze(task.id);
      setTask(nextTask);
      setNotice("Analyze 已提交，页面会自动刷新结果。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "启动分析失败");
    } finally {
      setBusyAction(null);
    }
  }

  async function handlePreview() {
    if (!task) return;
    setBusyAction("preview");
    setError(null);
    setNotice(null);
    try {
      const nextTask = await startPreview(task.id, scriptDraft);
      setTask(nextTask);
      setEdits(await getSmartCutEdits(task.id).catch(() => edits));
      setNotice("试听任务已提交，页面会自动刷新音频结果。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成试听失败");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleFinalize() {
    if (!task) return;
    setBusyAction("finalize");
    setError(null);
    setNotice(null);
    try {
      const nextTask = await startFinalize(task.id, { outputMode, feedToAi });
      setTask(nextTask);
      setNotice("生成视频任务已提交。按照 0415 规划，最终状态与下载会继续由任务中心接管。");
      router.push(`/tasks?taskId=${task.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "提交生成视频失败");
    } finally {
      setBusyAction(null);
    }
  }

  const headerTitle = useMemo(() => (task ? `任务 ${task.id}` : "Smart Cut"), [task]);

  return (
    <main className="min-h-screen p-4 lg:p-8">
      <div className="mx-auto max-w-7xl">
        <section className="relative overflow-hidden rounded-[40px] border border-[#e5dacd] bg-[#f7efe2] px-5 py-6 shadow-panel lg:px-8 lg:py-8">
          <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-48 bg-[radial-gradient(circle_at_top,rgba(196,99,61,0.24),transparent_58%)]" />
          <div className="relative flex flex-col gap-4 border-b border-[#dfcfbe] pb-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-stone-500">Smart Cut Workspace</p>
              <h1 className="mt-3 text-3xl font-semibold leading-tight text-[#241714] lg:text-5xl">{headerTitle}</h1>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-stone-600">
                Smart Cut 页面只负责三段工作流。点击“生成视频”后，最终状态与下载会转交到任务中心。
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button className="h-11 px-5" onClick={() => router.push("/smart-cut")} type="button" variant="secondary">
                返回任务入口
              </Button>
              <Button className="h-11 px-5" onClick={() => void bootstrap()} type="button" variant="ghost">
                刷新状态
              </Button>
            </div>
          </div>

          <div className="relative mt-6 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-6">
              <Card className="rounded-[32px] border-[#eadfce] bg-[#fffaf2] p-6 lg:p-7">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-stone-500">Analyze</p>
                    <h2 className="mt-2 text-2xl font-semibold text-[#231815]">上传输入并开始分析</h2>
                  </div>
                  {task ? <span className={`rounded-full px-3 py-2 text-xs font-semibold ${statusTone(task.status)}`}>{formatTaskStatus(task)}</span> : null}
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <div className="rounded-[26px] border border-[#eadfce] bg-white p-4">
                    <label className="text-xs uppercase tracking-[0.28em] text-stone-500">原视频文件</label>
                    <Input className="mt-3 cursor-pointer" disabled={!canUpload || busyAction === "upload"} onChange={(event) => setVideoFile(event.target.files?.[0] ?? null)} type="file" />
                    <p className="mt-3 text-sm text-stone-500">{videoFile?.name ?? task?.original_video_tos_key ?? "尚未选择视频"}</p>
                  </div>
                  <div className="rounded-[26px] border border-[#eadfce] bg-white p-4">
                    <label className="text-xs uppercase tracking-[0.28em] text-stone-500">参考文案文件</label>
                    <Input className="mt-3 cursor-pointer" disabled={!canUpload || busyAction === "upload"} onChange={(event) => setReferenceFile(event.target.files?.[0] ?? null)} type="file" />
                    <p className="mt-3 text-sm text-stone-500">{referenceFile?.name ?? task?.reference_text_tos_key ?? "尚未选择文案"}</p>
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  <Button className="h-11 px-5" disabled={!canUpload || !videoFile || !referenceFile || busyAction !== null} onClick={handleUpload} type="button">
                    {busyAction === "upload" ? "上传中..." : "上传输入文件"}
                  </Button>
                  <Button className="h-11 px-5" disabled={!canAnalyze || busyAction !== null} onClick={handleAnalyze} type="button" variant="secondary">
                    {busyAction === "analyze" ? "分析中..." : "开始分析"}
                  </Button>
                </div>
              </Card>

              {task?.analyze_script ? (
                <SmartCutScriptEditor
                  disabled={busyAction === "preview" || task.status === "previewing" || task.status === "finalizing"}
                  onScriptChange={setScriptDraft}
                  script={scriptDraft || task.analyze_script}
                />
              ) : null}
            </div>

            <div className="space-y-5">
              <Card className="rounded-[32px] border-[#eadfce] bg-[#fffaf2] p-6 lg:p-7">
                <p className="text-xs uppercase tracking-[0.3em] text-stone-500">Preview</p>
                <h2 className="mt-3 text-2xl font-semibold text-[#231815]">生成试听</h2>
                <p className="mt-3 text-sm leading-7 text-stone-600">Preview 只处理删除线调稿与试听结果，不在这里直接出最终视频。</p>

                <div className="mt-5 flex flex-wrap gap-3">
                  <Button className="h-11 px-5" disabled={!canPreview || busyAction !== null} onClick={handlePreview} type="button">
                    {busyAction === "preview" ? "生成中..." : "生成试听"}
                  </Button>
                </div>

                <div className="mt-5 rounded-[26px] border border-[#eadfce] bg-white p-4">
                  {latestEdit?.audio_b_url ? (
                    <div className="space-y-4">
                      <p className="text-sm text-stone-500">最近一次试听结果：{formatTime(latestEdit.updated_at)}</p>
                      <audio className="w-full" controls src={latestEdit.audio_b_url} />
                    </div>
                  ) : (
                    <p className="text-sm leading-7 text-stone-500">生成试听后，这里会出现 `audio_b` 播放器。</p>
                  )}
                </div>
              </Card>

              <Card className="rounded-[32px] border-[#eadfce] bg-[#fffaf2] p-6 lg:p-7">
                <p className="text-xs uppercase tracking-[0.3em] text-stone-500">Finalize</p>
                <h2 className="mt-3 text-2xl font-semibold text-[#231815]">提交最终视频任务</h2>

                <div className="mt-5 space-y-3 rounded-[26px] border border-[#eadfce] bg-white p-4">
                  <label className="flex items-center gap-3 text-sm text-[#231815]">
                    <input checked={outputMode === "original"} className="h-4 w-4 accent-[#c4633d]" onChange={() => setOutputMode("original")} type="radio" />
                    原始尺寸
                  </label>
                  <label className="flex items-center gap-3 text-sm text-[#231815]">
                    <input checked={outputMode === "vertical_1080p"} className="h-4 w-4 accent-[#c4633d]" onChange={() => setOutputMode("vertical_1080p")} type="radio" />
                    1080P 竖屏
                  </label>
                  <label className="mt-4 flex items-center gap-3 text-sm text-[#231815]">
                    <input checked={feedToAi} className="h-4 w-4 accent-[#c4633d]" onChange={(event) => setFeedToAi(event.target.checked)} type="checkbox" />
                    投喂本文案给 AI
                  </label>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  <Button className="h-11 px-5" disabled={!canFinalize || busyAction !== null} onClick={handleFinalize} type="button">
                    {busyAction === "finalize" ? "提交中..." : "生成视频"}
                  </Button>
                </div>

                {task?.final_video_url ? (
                  <a className="mt-5 inline-flex text-sm font-semibold text-[#9a5d3c] underline" href={task.final_video_url} target="_blank">
                    当前任务已完成，可直接下载视频
                  </a>
                ) : (
                  <p className="mt-5 text-sm leading-7 text-stone-500">按 0415 版边界，点击生成视频后，最终结果会继续在任务中心查看和下载。</p>
                )}
              </Card>

              {notice ? <p className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</p> : null}
              {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
              {task?.error_message ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">后端错误：{task.error_message}</p> : null}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
