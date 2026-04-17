"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { SmartCutScriptEditor } from "@/components/smart-cut/script-editor";
import {
  createSmartCutTask,
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

const STATUS_LABELS: Record<string, string> = {
  waiting_upload: "待上传素材",
  ready_analyze: "待开始分析",
  analyzing: "分析中",
  waiting_user: "待人工确认",
  ready_finalize: "待最终输出",
  previewing: "试听生成中",
  preview_failed: "试听失败",
  finalizing: "最终输出中",
  finalize_failed: "最终输出失败",
  success: "已完成",
  failed: "失败",
};

const STAGE_LABELS: Record<string, string> = {
  upload: "上传与分析",
  analyze: "上传与分析",
  user_select: "删除线调稿与试听",
  preview: "删除线调稿与试听",
  finalize: "最终输出",
  complete: "已完成",
};

function labelStatus(status: string | null | undefined) {
  if (!status) return "待同步";
  return STATUS_LABELS[status] ?? "处理中";
}

function labelStage(stage: string | null | undefined) {
  if (!stage) return "等待推进";
  return STAGE_LABELS[stage] ?? "处理中";
}

function formatTaskSummary(task: Pick<SmartCutTaskSummary, "status" | "current_stage">) {
  return `${labelStatus(task.status)} · ${labelStage(task.current_stage)}`;
}

export function SmartCutLandingPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<SmartCutTaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const workspace = useUserWorkspaceData(user?.username);

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

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

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
    <UserWorkspaceShell
      activeItem="smart-cut"
      currentUser={user?.username ?? "..."}
      headline={user ? `你好，${user.username}，小马AI准备就绪~` : undefined}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <section className="rounded-[32px] border border-[#e1d7c7] bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.92),_rgba(247,239,226,0.92)_48%,_rgba(241,229,209,0.96))] p-6 shadow-panel lg:p-7">
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="text-xs tracking-[0.28em] text-stone-500">智能气口剪辑工作台</p>
            <h1 className="mt-3 text-4xl font-semibold leading-tight text-[#231815]">三段式智能气口剪辑工作台</h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-stone-600">
              这里负责上传原视频、调整删除线脚本、生成试听，并把最终视频任务送入统一任务队列。最终下载与结果追踪会继续放在任务中心。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button className="h-11 px-5" disabled={creating} onClick={createTask} type="button">
                {creating ? "创建中..." : "开始新任务"}
              </Button>
              <Button className="h-11 px-5" onClick={() => router.push("/tasks")} type="button" variant="secondary">
                打开任务中心
              </Button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            {[
              ["操作边界", "上传与分析 / 调稿与试听 / 最终输出"],
              ["页面角色", "这里只负责前端控制台，不承担结果下载。"],
              ["结果去向", "最终视频状态和下载统一回到任务中心查看。"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-[26px] border border-white/70 bg-white/80 p-4 backdrop-blur">
                <p className="text-xs tracking-[0.24em] text-stone-500">{label}</p>
                <p className="mt-3 text-base font-semibold leading-7 text-[#231815]">{value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="rounded-[32px] border-[#e1d7c7] bg-[#fdf9f2] p-6 shadow-panel" data-testid="smart-cut-recent-tasks">
          <p className="text-xs tracking-[0.28em] text-stone-500">固定三段流程</p>
          <h2 className="mt-3 text-2xl font-semibold text-[#231815]">上传与分析 / 删除线调稿与试听 / 最终输出</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {[
              ["第一段", "上传与分析", "上传视频与标准文案，启动分析并拿到删除线脚本。"],
              ["第二段", "删除线调稿与试听", "只在前端调整删除范围并生成试听，不直接出最终视频。"],
              ["第三段", "最终输出", "确认输出规格与 AI 投喂后，把最终任务送入任务中心。"],
            ].map(([eyebrow, title, description]) => (
              <div key={title} className="rounded-[24px] border border-[#e1d7c7] bg-white p-4">
                <p className="text-xs tracking-[0.24em] text-stone-500">{eyebrow}</p>
                <p className="mt-3 text-base font-semibold text-[#231815]">{title}</p>
                <p className="mt-3 text-sm leading-7 text-stone-600">{description}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="rounded-[32px] border-[#e1d7c7] bg-[#fdf9f2] p-6 shadow-panel">
          <p className="text-xs tracking-[0.28em] text-stone-500">最近任务</p>
          <h2 className="mt-3 text-2xl font-semibold text-[#231815]">最近任务</h2>
          {error ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
          <div className="mt-5 space-y-3">
            {loading ? (
              <p className="text-sm text-stone-500">正在读取任务…</p>
            ) : tasks.length === 0 ? (
              <div className="rounded-[24px] border border-[#e1d7c7] bg-white p-4 text-sm text-stone-500">还没有任务，先新建一个智能气口剪辑任务。</div>
            ) : (
              tasks.slice(0, 5).map((task) => (
                <button
                  key={task.id}
                  className="block w-full rounded-[24px] border border-[#e1d7c7] bg-white p-4 text-left transition hover:bg-[#faf2e7]"
                  data-testid={`smart-cut-recent-task-${task.id}`}
                  onClick={() => router.push(`/smart-cut/${task.id}`)}
                  type="button"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-[#231815]">{task.id}</p>
                    <span className={`rounded-full px-3 py-1 text-xs ${statusTone(task.status)}`}>{labelStatus(task.status)}</span>
                  </div>
                  <p className="mt-2 text-sm text-stone-500">{formatTaskSummary(task)}</p>
                  <p className="mt-3 text-xs tracking-[0.2em] text-stone-400">{formatTime(task.updated_at)}</p>
                </button>
              ))
            )}
          </div>
        </Card>
      </section>
    </UserWorkspaceShell>
  );
}

export function SmartCutWorkspace({ taskId }: { taskId: string }) {
  const router = useRouter();
  const [task, setTask] = useState<SmartCutTask | null>(null);
  const [currentUser, setCurrentUser] = useState<string>("...");
  const [edits, setEdits] = useState<SmartCutEdit[]>([]);
  const [scriptDraft, setScriptDraft] = useState("");
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [outputMode, setOutputMode] = useState<"original" | "vertical_1080p">("original");
  const [feedToAi, setFeedToAi] = useState(true);
  const [busyAction, setBusyAction] = useState<"upload" | "analyze" | "preview" | "finalize" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const workspace = useUserWorkspaceData(currentUser);

  const latestEdit = edits[0] ?? null;

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

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
    setCurrentUser(authPayload.user.username);

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
      setNotice("分析任务已提交，页面会自动刷新结果。");
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

  const headerTitle = useMemo(() => (task ? `任务 ${task.id}` : "智能气口剪辑"), [task]);
  const taskStatusLabel = task ? labelStatus(task.status) : "待同步";
  const taskStageLabel = task ? labelStage(task.current_stage) : "等待推进";
  const latestAudioLabel = latestEdit?.audio_b_url ? "已有试听音频" : "尚未生成试听";
  const scriptStatusLabel = task?.analyze_script ? "已收到分析脚本" : "等待分析返回脚本";

  return (
    <UserWorkspaceShell
      activeItem="smart-cut"
      currentUser={currentUser}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <section className="rounded-[32px] border border-[#e1d7c7] bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.96),_rgba(251,244,235,0.96)_42%,_rgba(244,236,223,0.98))] p-6 shadow-panel lg:p-7">
        <div className="flex flex-col gap-4 border-b border-[#e3d8c7] pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs tracking-[0.3em] text-stone-500">智能气口剪辑任务操作台</p>
            <h1 className="mt-3 text-3xl font-semibold leading-tight text-[#231815] lg:text-4xl">{headerTitle}</h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-stone-600">
              当前页面只负责上传与分析、删除线调稿与试听、最终输出三段工作流。点击“生成视频”后，最终状态与下载会转交到任务中心。
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

        <div className="mt-6 grid gap-4 lg:grid-cols-4">
          {[
            ["当前状态", taskStatusLabel],
            ["当前阶段", taskStageLabel],
            ["脚本状态", scriptStatusLabel],
            ["试听状态", latestAudioLabel],
          ].map(([label, value]) => (
            <div key={label} className="rounded-[24px] border border-white/80 bg-white/80 px-4 py-4 backdrop-blur">
              <p className="text-xs tracking-[0.22em] text-stone-500">{label}</p>
              <p className="mt-3 text-lg font-semibold text-[#231815]">{value}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
          <div className="space-y-6">
            <Card className="rounded-[32px] border-[#eadfce] bg-[#fffaf2] p-6 lg:p-7">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs tracking-[0.24em] text-stone-500">第一段</p>
                  <h2 className="mt-2 text-2xl font-semibold text-[#231815]">上传与分析</h2>
                  <p className="mt-3 text-sm leading-7 text-stone-600">先上传原视频和标准文案，再启动分析。上传输入并开始分析后，系统会返回删除线脚本。</p>
                </div>
                {task ? <span className={`rounded-full px-3 py-2 text-xs font-semibold ${statusTone(task.status)}`}>{`${taskStatusLabel} · ${taskStageLabel}`}</span> : null}
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-[26px] border border-[#eadfce] bg-white p-4">
                  <label className="text-xs tracking-[0.22em] text-stone-500">原视频文件</label>
                  <Input className="mt-3 cursor-pointer" disabled={!canUpload || busyAction === "upload"} onChange={(event) => setVideoFile(event.target.files?.[0] ?? null)} type="file" />
                  <p className="mt-3 text-sm text-stone-500">{videoFile?.name ?? task?.original_video_tos_key ?? "尚未选择视频"}</p>
                </div>
                <div className="rounded-[26px] border border-[#eadfce] bg-white p-4">
                  <label className="text-xs tracking-[0.22em] text-stone-500">参考文案文件</label>
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

            <section className="rounded-[32px] border border-[#eadfce] bg-[#fffaf2] p-6 shadow-panel lg:p-7">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs tracking-[0.24em] text-stone-500">第二段</p>
                  <h2 className="mt-2 text-2xl font-semibold text-[#231815]">删除线调稿与试听</h2>
                  <p className="mt-3 text-sm leading-7 text-stone-600">这一段只处理删除线调稿与试听结果，不在这里直接出最终视频。</p>
                </div>
                <div className="rounded-[22px] border border-[#eadfce] bg-white px-4 py-3 text-sm text-stone-500">
                  {latestEdit ? `最近试听更新于 ${formatTime(latestEdit.updated_at)}` : "暂无试听结果"}
                </div>
              </div>

              <div className="mt-5">
                {task?.analyze_script ? (
                  <SmartCutScriptEditor
                    disabled={busyAction === "preview" || task.status === "previewing" || task.status === "finalizing"}
                    onScriptChange={setScriptDraft}
                    script={scriptDraft || task.analyze_script}
                  />
                ) : (
                  <div className="rounded-[28px] border border-dashed border-[#dccab6] bg-white px-5 py-8 text-sm leading-7 text-stone-500">
                    分析脚本还没有返回。先完成“上传与分析”，拿到脚本后，这里会出现删除线调稿台。
                  </div>
                )}
              </div>

              <Card className="mt-5 rounded-[28px] border-[#eadfce] bg-white p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-xs tracking-[0.22em] text-stone-500">试听结果面板</p>
                    <h3 className="mt-2 text-xl font-semibold text-[#231815]">生成试听</h3>
                    <p className="mt-2 text-sm leading-7 text-stone-600">每次提交都会基于当前删除线脚本重新生成试听音轨，方便你快速确认删改效果。</p>
                  </div>
                  <Button className="h-11 px-5" disabled={!canPreview || busyAction !== null} onClick={handlePreview} type="button">
                    {busyAction === "preview" ? "生成中..." : "生成试听"}
                  </Button>
                </div>

                <div className="mt-5 rounded-[24px] border border-[#eadfce] bg-[#fffaf2] p-4">
                  {latestEdit?.audio_b_url ? (
                    <div className="space-y-4">
                      <p className="text-sm text-stone-500">最近一次试听结果：{formatTime(latestEdit.updated_at)}</p>
                      <audio className="w-full" controls src={latestEdit.audio_b_url} />
                    </div>
                  ) : (
                    <p className="text-sm leading-7 text-stone-500">生成试听后，这里会出现试听播放器。</p>
                  )}
                </div>
              </Card>
            </section>
          </div>

          <div className="space-y-5">
            <Card className="rounded-[32px] border-[#eadfce] bg-[#2b201d] p-6 text-stone-100 shadow-panel lg:p-7">
              <p className="text-xs tracking-[0.24em] text-stone-300">任务总览</p>
              <h2 className="mt-3 text-3xl font-semibold">当前任务控制台</h2>
              <div className="mt-5 space-y-3">
                {[
                  ["任务编号", task?.id ?? "等待同步"],
                  ["最后更新", task ? formatTime(task.updated_at) : "等待同步"],
                  ["任务去向", "最终结果统一回到任务中心查看与下载"],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-[22px] border border-white/10 bg-white/5 px-4 py-4">
                    <p className="text-xs tracking-[0.2em] text-stone-300">{label}</p>
                    <p className="mt-2 text-base font-semibold text-white">{value}</p>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="rounded-[32px] border-[#eadfce] bg-[#fffaf2] p-6 lg:p-7">
              <p className="text-xs tracking-[0.24em] text-stone-500">第三段</p>
              <h2 className="mt-3 text-2xl font-semibold text-[#231815]">最终输出</h2>
              <p className="mt-3 text-sm leading-7 text-stone-600">确认输出规格后提交最终任务。这里保留投喂 AI 的开关，但最终状态与下载继续在任务中心承接。</p>

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

              <div className="mt-5 rounded-[26px] border border-dashed border-[#dccab6] bg-white px-4 py-4 text-sm leading-7 text-stone-500">
                按 0415 版边界，点击“生成视频”后，最终结果会继续在任务中心查看和下载。
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
              ) : null}
            </Card>

            {notice ? <p className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</p> : null}
            {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
            {task?.error_message ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">后端错误：{task.error_message}</p> : null}
          </div>
        </div>
      </section>
    </UserWorkspaceShell>
  );
}
