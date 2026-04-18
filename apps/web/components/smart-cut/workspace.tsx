"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { SmartCutScriptEditor } from "@/components/smart-cut/script-editor";
import { AuthResponse } from "@/lib/auth";
import {
  createSmartCutTask,
  getSmartCutEdits,
  getSmartCutTask,
  listSmartCutTasks,
  SmartCutEdit,
  SmartCutTask,
  startAnalyze,
  startFinalize,
  startPreview,
  uploadDirectInputs,
} from "@/lib/smart-cut";

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

export function SmartCutLandingPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

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

      try {
        const createdTask = await createSmartCutTask(authPayload.user.username);
        router.replace(`/smart-cut/${createdTask.id}`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "读取任务失败");
      }
    }

    void bootstrap().catch((err) => {
      setError(err instanceof Error ? err.message : "打开智能气口剪辑失败");
    });
  }, [router]);

  return (
    <Card className="flex min-h-[640px] items-center justify-center rounded-[32px] border-[#e5dacd] bg-[#f8f5ef] shadow-panel">
      <div className="space-y-4 text-center">
        <p className="text-lg font-medium text-stone-500">正在打开智能气口剪辑工作台…</p>
        {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
      </div>
    </Card>
  );
}

export function SmartCutWorkspace({ taskId }: { taskId: string }) {
  const router = useRouter();
  const [task, setTask] = useState<SmartCutTask | null>(null);
  const [currentUser, setCurrentUser] = useState<AuthResponse["user"] | null>(null);
  const [edits, setEdits] = useState<SmartCutEdit[]>([]);
  const [scriptDraft, setScriptDraft] = useState("");
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [outputMode, setOutputMode] = useState<"original" | "vertical_1080p">("original");
  const [feedToAi, setFeedToAi] = useState(true);
  const [editorTab, setEditorTab] = useState<"script" | "groundtruth">("script");
  const [busyAction, setBusyAction] = useState<"upload" | "analyze" | "preview" | "finalize" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const workspace = useUserWorkspaceData(currentUser?.username);

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
    setCurrentUser(authPayload.user);

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

  const taskStatusLabel = task ? labelStatus(task.status) : "待同步";
  const taskStageLabel = task ? labelStage(task.current_stage) : "等待推进";
  const uploadSummary = videoFile?.name ?? task?.original_video_tos_key ?? "尚未上传";
  const referenceSummary = referenceFile?.name ?? task?.reference_text_tos_key ?? "尚未上传";
  const previewReady = Boolean(latestEdit?.audio_b_url);
  const downloadReady = Boolean(task?.final_video_url);
  const stageOneLabel = canPreview ? "可生成试听" : canAnalyze ? "待开始分析" : "待上传素材";
  const stageTwoLabel = canFinalize ? "可生成视频" : previewReady ? "待确认规格" : "等待试听完成";

  return (
    <UserWorkspaceShell
      activeItem="smart-cut"
      currentUser={currentUser?.username ?? "..."}
      headline={currentUser?.company_name ? `你好，${currentUser.company_name}，小马AI准备就绪~` : undefined}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <section className="rounded-[32px] border border-[#dde1ea] bg-[#f7f9fc] p-6 shadow-[0_8px_24px_rgba(78,91,117,0.06)]">
        <div className="grid gap-6 xl:grid-cols-[1.7fr_0.62fr]">
          <div className="space-y-5">
            <Card className="rounded-[30px] border-[#dbe4f4] bg-white p-5 shadow-sm">
              <p className="text-sm font-semibold text-[#243444]">左侧主工作区</p>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <label className="flex cursor-pointer flex-col items-center justify-center rounded-[22px] border border-[#8bc0ff] bg-[#edf5ff] px-4 py-5 text-center text-[18px] font-semibold leading-snug text-[#3e86f6]">
                  上传视频
                  <span className="mt-1 text-[15px] font-semibold">（前端直传 TOS）</span>
                  <Input className="hidden" disabled={busyAction === "upload"} onChange={(event) => setVideoFile(event.target.files?.[0] ?? null)} type="file" />
                </label>
                <label className="flex cursor-pointer flex-col items-center justify-center rounded-[22px] border border-[#8bc0ff] bg-[#edf5ff] px-4 py-5 text-center text-[18px] font-semibold leading-snug text-[#3e86f6]">
                  上传标准文案
                  <Input className="hidden" disabled={busyAction === "upload"} onChange={(event) => setReferenceFile(event.target.files?.[0] ?? null)} type="file" />
                </label>
                <button
                  className="rounded-[22px] border border-[#c9b8ff] bg-[#f7f1ff] px-4 py-5 text-center text-[18px] font-semibold leading-snug text-[#7c57f4] transition disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!canAnalyze || busyAction !== null}
                  onClick={handleAnalyze}
                  type="button"
                >
                  开始分析
                  <span className="mt-1 block text-[15px] font-semibold">（生成 script 预览）</span>
                </button>
              </div>

              <div className="mt-5 space-y-3">
                <div className="flex flex-wrap items-center gap-4 rounded-[18px] border border-[#d9dee8] bg-white px-5 py-3 text-[15px]">
                  <span className="font-medium text-[#394150]">视频文件：{uploadSummary}</span>
                  <span className="text-[#4ec28c]">状态：{task?.original_video_tos_key || videoFile ? "已上传到 TOS" : "待上传"}</span>
                  <span className="ml-auto text-[#f1a33e]">{videoFile ? "重新上传 / 删除" : "选择文件"}</span>
                </div>
                <div className="flex flex-wrap items-center gap-4 rounded-[18px] border border-[#d9dee8] bg-white px-5 py-3 text-[15px]">
                  <span className="font-medium text-[#394150]">标准文案：{referenceSummary}</span>
                  <span className="text-[#4ec28c]">状态：{task?.reference_text_tos_key || referenceFile ? "已上传" : "待上传"}</span>
                  <span className="ml-auto text-[#f1a33e]">{referenceFile ? "重新上传 / 删除" : "选择文件"}</span>
                </div>
              </div>
            </Card>

            <Card className="rounded-[30px] border-[#c9dcff] bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="text-[18px] font-semibold text-[#2f3848]">脚本预览与编辑（前端显示删除线；后端转为大括号）</h2>
                </div>
                <label className="flex items-center gap-3 text-sm text-[#465067]">
                  <input checked={feedToAi} className="h-4 w-4 accent-[#4b86ff]" onChange={(event) => setFeedToAi(event.target.checked)} type="checkbox" />
                  投喂本文案给 AI
                </label>
              </div>

              <div className="mt-4 flex gap-3">
                <button
                  className={`rounded-full px-4 py-2 text-sm font-medium ${editorTab === "script" ? "bg-[#eaf3ff] text-[#4a85f6]" : "border border-[#dde4ef] bg-white text-stone-500"}`}
                  onClick={() => setEditorTab("script")}
                  type="button"
                >
                  script 预览
                </button>
                <button
                  className={`rounded-full px-4 py-2 text-sm font-medium ${editorTab === "groundtruth" ? "bg-[#eef2f7] text-[#667085]" : "border border-[#dde4ef] bg-white text-stone-500"}`}
                  onClick={() => setEditorTab("groundtruth")}
                  type="button"
                >
                  GroundTruth
                </button>
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-[1.28fr_0.72fr]">
                <div className="rounded-[22px] border border-[#dbe4f4] bg-[#fcfdff] p-4">
                  {editorTab === "script" ? (
                    task?.analyze_script ? (
                      <SmartCutScriptEditor
                        disabled={busyAction === "preview" || task.status === "previewing" || task.status === "finalizing"}
                        onScriptChange={setScriptDraft}
                        script={scriptDraft || task.analyze_script}
                      />
                    ) : (
                      <div className="min-h-[260px] rounded-[18px] border border-[#dfe6f2] bg-white px-5 py-5 text-[16px] leading-9 text-[#313b4a]">
                        <p className="text-stone-400">示例：</p>
                        <p className="mt-3">今天我来讲一下这个功能，</p>
                        <p className="line-through decoration-2">这个地方先删了要删掉，</p>
                        <p>后面这一句保留继续生成试听。</p>
                      </div>
                    )
                  ) : (
                    <div className="min-h-[260px] rounded-[18px] border border-[#dfe6f2] bg-white px-5 py-5 text-[15px] leading-8 text-stone-500">
                      GroundTruth 结果会在后端产物可用时展示。
                    </div>
                  )}
                </div>

                <div className="rounded-[22px] border border-[#ffd978] bg-[#fff7da] px-5 py-5">
                  <p className="text-[18px] font-semibold text-[#f2a11f]">交互说明</p>
                  <ul className="mt-3 space-y-2 text-sm leading-7 text-[#535b69]">
                    <li>用户可直接调整删除范围</li>
                    <li>生成试听前：删除线 -&gt; 大括号</li>
                    <li>生成视频时记录 Pair 数据</li>
                    <li>生成完成后回传 TOS 下载链接</li>
                  </ul>
                </div>
              </div>
            </Card>
          </div>

          <div className="space-y-4">
            <button
              className="w-full rounded-[22px] border border-[#ffbb5f] bg-[#fff8ed] px-5 py-4 text-[18px] font-semibold text-[#f2a11f] transition disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canPreview || busyAction !== null}
              onClick={handlePreview}
              type="button"
            >
              阶段 1：生成试听
            </button>

            <Card className="rounded-[24px] border-[#cfb9ff] bg-[#f6f2ff] p-5 shadow-sm">
              <p className="text-[18px] font-semibold text-[#7c57f4]">试听播放器</p>
              <p className="mt-2 text-sm text-stone-500">Step A 音频 / Step B 剪气口后音频</p>
              <div className="mt-4">
                {latestEdit?.audio_b_url ? (
                  <audio className="w-full" controls src={latestEdit.audio_b_url} />
                ) : (
                  <div className="rounded-[16px] bg-white px-4 py-5 text-sm text-stone-500">生成试听后，这里显示播放器。</div>
                )}
              </div>
            </Card>

            <Card className="rounded-[24px] border-[#d9dee8] bg-white p-5 shadow-sm">
              <p className="text-[18px] font-semibold text-[#2f3848]">输出视频规格</p>
              <div className="mt-4 space-y-3 text-[16px] text-[#465067]">
                <label className="flex items-center gap-3">
                  <input checked={outputMode === "vertical_1080p"} className="h-4 w-4 accent-[#4b86ff]" onChange={() => setOutputMode("vertical_1080p")} type="radio" />
                  1080P 竖屏（生成前做 normalize）
                </label>
                <label className="flex items-center gap-3">
                  <input checked={outputMode === "original"} className="h-4 w-4 accent-[#4b86ff]" onChange={() => setOutputMode("original")} type="radio" />
                  原始尺寸（不做 normalize）
                </label>
              </div>
            </Card>

            <button
              className="w-full rounded-[22px] border border-[#ffbb5f] bg-[#fff8ed] px-5 py-4 text-[18px] font-semibold text-[#f2a11f] transition disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!canFinalize || busyAction !== null}
              onClick={handleFinalize}
              type="button"
            >
              阶段 2：生成视频
            </button>

            <Card className="rounded-[24px] border-[#96edc4] bg-[#edfff5] p-5 shadow-sm">
              <p className="text-[18px] font-semibold text-[#18b667]">下载视频</p>
              <p className="mt-2 text-sm text-stone-500">生成完成后显示 TOS 下载链接</p>
              <div className="mt-4 text-sm leading-7 text-[#248a60]">
                {downloadReady ? (
                  <a className="underline" href={task?.final_video_url ?? "#"} target="_blank">
                    {task?.final_video_tos_key ?? "点击下载"}
                  </a>
                ) : (
                  <span>当前还没有可下载的视频结果。</span>
                )}
              </div>
            </Card>

            {notice ? <p className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</p> : null}
            {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
            {task?.error_message ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">后端错误：{task.error_message}</p> : null}
          </div>
        </div>

        <p className="mt-5 text-xs leading-6 text-stone-400">
          数据记录：标准文案 / 输入视频 / 输入视频 ASR / 输出 script / 用户修改后 script，在点击“生成视频”时写入公司专属 TOS 路径。
        </p>
      </section>
    </UserWorkspaceShell>
  );
}
