"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { SmartCutScriptEditor, SmartCutScriptEditorHandle } from "@/components/smart-cut/script-editor";
import { AuthResponse } from "@/lib/auth";
import { logoutUser } from "@/lib/logout";
import {
  createSmartCutTask,
  ensureCurrentSmartCutDraft,
  getCurrentSmartCutDraft,
  getSmartCutEdits,
  getSmartCutTask,
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

function formatPercent(value: number) {
  return `${Math.max(0, Math.min(100, Math.round(value)))}%`;
}

function summarizeUploadName(value: string | null | undefined) {
  if (!value) return "尚未上传";
  const cleaned = value.split("?")[0]?.split("#")[0] ?? value;
  return cleaned.split("/").filter(Boolean).pop() ?? "尚未上传";
}

function draftCacheKey(username: string) {
  return `smart-cut:draft-task:${username}`;
}

function writeCachedDraftTaskId(username: string, taskId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(draftCacheKey(username), taskId);
}

function clearCachedDraftTaskId(username: string) {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(draftCacheKey(username));
}

function isBusyStatus(status: string | null | undefined) {
  return status ? ["analyzing", "previewing", "finalizing"].includes(status) : false;
}

function buildWorkspaceBanner(args: {
  busyAction: "upload" | "analyze" | "preview" | "finalize" | null;
  task: SmartCutTask | null;
  uploadState: "idle" | "uploading" | "success" | "error";
  canAnalyze: boolean;
  hasAudioA: boolean;
  hasAudioB: boolean;
  submittedTaskTitle: string | null;
}) {
  const { busyAction, task, uploadState, canAnalyze, hasAudioA, hasAudioB, submittedTaskTitle } = args;

  if (uploadState === "uploading" || busyAction === "upload") {
    return {
      title: "正在上传素材",
      detail: "视频和标准文案会进入当前会话草稿，上传完成后即可开始分析。",
    };
  }
  if (busyAction === "analyze" || task?.status === "analyzing") {
    return {
      title: "正在收到您的信息并处理中……",
      detail: "分析完成后，当前页面会直接显示删除线脚本和 audio_a。",
    };
  }
  if (busyAction === "preview" || task?.status === "previewing") {
    return {
      title: "正在生成试听",
      detail: "试听完成后，这里会切换到最新的 audio_b 播放器。",
    };
  }
  if (busyAction === "finalize" || task?.status === "finalizing") {
    return {
      title: "正在生成视频",
      detail: "当前任务会转入任务列表，工作台将回到下一条草稿的起点。",
    };
  }
  if (!task && submittedTaskTitle) {
    return {
      title: "任务已转入任务列表",
      detail: `${submittedTaskTitle} 已作为正式任务加入任务列表，当前工作台已清空，可以继续开始下一条。`,
    };
  }
  if (hasAudioB) {
    return {
      title: "试听生成完成",
      detail: "你可以继续调整删除线，或者直接开始生成视频。",
    };
  }
  if (hasAudioA) {
    return {
      title: "分析完成，可调整删除线",
      detail: "当前页已经回显删除线脚本和首版 audio_a，可直接进入试听。",
    };
  }
  if (canAnalyze) {
    return {
      title: "素材已就绪，等待开始分析",
      detail: "当前会话草稿已恢复，点击“开始分析”即可继续。",
    };
  }
  return {
    title: "等待上传视频和标准文案",
    detail: "进入 /smart-cut 不会自动建任务；第一次真正上传时才会确保草稿存在。",
  };
}

export function SmartCutWorkspace({ taskId }: { taskId?: string }) {
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
  const [editorControls, setEditorControls] = useState({
    canMarkDelete: false,
    canRestore: false,
    canClear: false,
    selectedCount: 0,
  });
  const [busyAction, setBusyAction] = useState<"upload" | "analyze" | "preview" | "finalize" | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadState, setUploadState] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [lastSubmittedTaskTitle, setLastSubmittedTaskTitle] = useState<string | null>(null);
  const [inputResetToken, setInputResetToken] = useState(0);
  const workspace = useUserWorkspaceData(currentUser?.username, currentUser?.company_id);
  const scriptEditorRef = useRef<SmartCutScriptEditorHandle>(null);

  const latestEdit = edits[0] ?? null;

  async function logout() {
    await logoutUser(currentUser?.username);
    if (currentUser?.username) {
      clearCachedDraftTaskId(currentUser.username);
    }
    router.replace("/login");
    router.refresh();
  }

  async function hydrateTask(nextTaskId: string, username?: string) {
    const [taskData, editData] = await Promise.all([getSmartCutTask(nextTaskId), getSmartCutEdits(nextTaskId).catch(() => [])]);

    setTask(taskData);
    setEdits(editData);
    setLastSubmittedTaskTitle(null);
    setOutputMode(taskData.output_mode ?? "original");
    setFeedToAi(taskData.feed_to_ai ?? true);

    const sourceScript = editData[0]?.edited_script ?? taskData.analyze_script ?? "";
    setScriptDraft(sourceScript);
    if (username) {
      writeCachedDraftTaskId(username, taskData.id);
    }
    return taskData;
  }

  function clearDraftWorkspace(username?: string) {
    if (username) {
      clearCachedDraftTaskId(username);
    }
    setTask(null);
    setEdits([]);
    setScriptDraft("");
    setVideoFile(null);
    setReferenceFile(null);
    setOutputMode("original");
    setFeedToAi(true);
    setEditorTab("script");
    setEditorControls({
      canMarkDelete: false,
      canRestore: false,
      canClear: false,
      selectedCount: 0,
    });
    setBusyAction(null);
    setUploadProgress(0);
    setUploadState("idle");
    setNotice(null);
    setError(null);
    setLastSubmittedTaskTitle(null);
    setInputResetToken((value) => value + 1);
  }

  function resetWorkspaceForNextDraft(taskTitle: string) {
    setTask(null);
    setEdits([]);
    setScriptDraft("");
    setVideoFile(null);
    setReferenceFile(null);
    setOutputMode("original");
    setFeedToAi(true);
    setEditorTab("script");
    setEditorControls({
      canMarkDelete: false,
      canRestore: false,
      canClear: false,
      selectedCount: 0,
    });
    setBusyAction(null);
    setUploadProgress(0);
    setUploadState("idle");
    setError(null);
    setNotice(null);
    setLastSubmittedTaskTitle(taskTitle);
    setInputResetToken((value) => value + 1);
  }

  async function bootstrap() {
    setLoading(true);
    if (!taskId) {
      setTask(null);
      setEdits([]);
      setScriptDraft("");
      setError(null);
      setNotice(null);
      setBusyAction(null);
      setUploadProgress(0);
      setUploadState("idle");
      setLastSubmittedTaskTitle(null);
    }
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

    try {
      if (taskId) {
        await hydrateTask(taskId, authPayload.user.username);
        return;
      }

      const draftLookup = await getCurrentSmartCutDraft(authPayload.user.username);
      if (draftLookup.task) {
        await hydrateTask(draftLookup.task.id, authPayload.user.username);
        return;
      }

      clearDraftWorkspace(authPayload.user.username);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void bootstrap().catch((err) => {
      setError(err instanceof Error ? err.message : "读取任务失败");
      setLoading(false);
    });
  }, [taskId]);

  useEffect(() => {
    if (!task) return;
    if (!isBusyStatus(task.status)) return;

    const timer = window.setInterval(() => {
      void bootstrap().catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [task?.status]);

  const canUpload = (!task && Boolean(currentUser)) || task?.status === "waiting_upload";
  const canAnalyze = task?.status === "ready_analyze";
  const canPreview = Boolean(task && ["waiting_user", "preview_failed"].includes(task.status) && scriptDraft.length > 0);
  const hasPreviewArtifacts = Boolean(
    latestEdit?.audio_b_url && latestEdit?.edited_delay_cuts_tos_key && latestEdit?.pause_cuts_on_original_tos_key,
  );
  const canFinalize = Boolean(task && ["waiting_user", "finalize_failed"].includes(task.status) && hasPreviewArtifacts);

  useEffect(() => {
    if (!canUpload || busyAction !== null || uploadState !== "idle" || !videoFile || !referenceFile) return;
    void handleUpload().catch(() => undefined);
  }, [busyAction, canUpload, currentUser?.username, referenceFile, task?.id, uploadState, videoFile]);

  async function ensureDraftTask() {
    if (task) return task;
    if (!currentUser?.username) {
      throw new Error("当前登录态未就绪，请刷新后重试");
    }

    const ensured = await ensureCurrentSmartCutDraft(currentUser.username, currentUser.company_id);
    if (ensured.task) {
      setTask(ensured.task);
      writeCachedDraftTaskId(currentUser.username, ensured.task.id);
      return ensured.task;
    }

    const createdTask = await createSmartCutTask(currentUser.username, currentUser.company_id);
    setTask(createdTask);
    writeCachedDraftTaskId(currentUser.username, createdTask.id);
    return createdTask;
  }

  async function handleUpload() {
    if (!videoFile || !referenceFile) return;
    setBusyAction("upload");
    setUploadProgress(0);
    setUploadState("uploading");
    setError(null);
    setNotice(null);
    setLastSubmittedTaskTitle(null);

    try {
      const ensuredTask = await ensureDraftTask();
      const nextTask = await uploadDirectInputs(ensuredTask.id, videoFile, referenceFile, {
        onProgress: (progress) => {
          setUploadProgress(progress.percent);
        },
      });
      setTask(nextTask);
      if (currentUser?.username) {
        writeCachedDraftTaskId(currentUser.username, nextTask.id);
      }
      setUploadProgress(100);
      setUploadState("success");
      setNotice("输入文件已上传，可以开始分析。");
    } catch (err) {
      setUploadState("error");
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
    setLastSubmittedTaskTitle(null);
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
    setLastSubmittedTaskTitle(null);
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
    setLastSubmittedTaskTitle(null);
    try {
      const result = await startFinalize(task.id, { outputMode, feedToAi });
      if (!result.visibleInTaskCenter) {
        throw new Error("Finalize 已提交，但任务还没有进入任务列表");
      }
      if (currentUser?.username) {
        clearCachedDraftTaskId(currentUser.username);
      }
      resetWorkspaceForNextDraft(result.taskTitle);
    } catch (err) {
      setError(err instanceof Error ? err.message : "提交生成视频失败");
    } finally {
      setBusyAction(null);
    }
  }

  const taskStatusLabel = task ? labelStatus(task.status) : "待同步";
  const taskStageLabel = task ? labelStage(task.current_stage) : "会话草稿待创建";
  const uploadSummary = videoFile?.name ?? summarizeUploadName(task?.original_video_tos_key ?? task?.original_video_url);
  const referenceSummary = referenceFile?.name ?? summarizeUploadName(task?.reference_text_tos_key ?? task?.reference_text_url);
  const audioAReady = Boolean(latestEdit?.audio_a_url);
  const previewReady = Boolean(latestEdit?.audio_b_url);
  const audioPreviewUrl = latestEdit?.audio_b_url ?? latestEdit?.audio_a_url ?? null;
  const audioPreviewLabel = latestEdit?.audio_b_url ? "试听音频 audio_b" : latestEdit?.audio_a_url ? "分析音频 audio_a" : null;
  const downloadReady = Boolean(task?.final_video_url);
  const stageOneLabel = canPreview ? "可生成试听" : canAnalyze ? "待开始分析" : "待上传素材";
  const stageTwoLabel = canFinalize ? "可生成视频" : previewReady ? "待确认规格" : "请先生成试听";
  const banner = buildWorkspaceBanner({
    busyAction,
    task,
    uploadState,
    canAnalyze,
    hasAudioA: audioAReady,
    hasAudioB: previewReady,
    submittedTaskTitle: lastSubmittedTaskTitle,
  });
  const uploadProgressText = formatPercent(uploadProgress);
  const uploadInFlight = uploadState === "uploading";
  const scriptActionsVisible = editorTab === "script";
  const scriptActionsDisabled = !scriptActionsVisible || busyAction === "preview" || task?.status === "previewing" || task?.status === "finalizing";
  const videoUploaded = Boolean(task?.original_video_tos_key);
  const referenceUploaded = Boolean(task?.reference_text_tos_key);
  const videoStatus = videoUploaded
    ? "已上传"
    : uploadInFlight && videoFile && referenceFile
      ? `正在上传中 ${uploadProgressText}`
      : uploadState === "error" && videoFile
        ? "上传失败，请重试"
        : videoFile
          ? "已选择，等待上传"
          : "待上传";
  const referenceStatus = referenceUploaded
    ? "已上传"
    : uploadInFlight && videoFile && referenceFile
      ? `正在上传中 ${uploadProgressText}`
      : uploadState === "error" && referenceFile
        ? "上传失败，请重试"
        : referenceFile
          ? "已选择，等待上传"
          : "待上传";
  const videoProgressValue = videoUploaded ? 100 : uploadInFlight && videoFile && referenceFile ? uploadProgress : 0;
  const referenceProgressValue = referenceUploaded ? 100 : uploadInFlight && videoFile && referenceFile ? uploadProgress : 0;
  const videoProgressHint = videoUploaded
    ? "视频素材已进入任务输入区。"
    : uploadInFlight && videoFile && referenceFile
      ? `上传进度 ${uploadProgressText}`
      : videoFile
        ? "视频已选中，等待标准文案后自动上传。"
        : "请先选择你要处理的视频。";
  const referenceProgressHint = referenceUploaded
    ? "标准文案已进入任务输入区。"
    : uploadInFlight && videoFile && referenceFile
      ? `上传进度 ${uploadProgressText}`
      : referenceFile
        ? "标准文案已选中，等待视频后自动上传。"
        : "请再上传一份标准文案。";

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
        {loading ? (
          <Card className="mb-6 flex min-h-[160px] items-center justify-center rounded-[28px] border-[#dbe4f4] bg-white p-6 shadow-sm">
            <p className="text-base font-medium text-stone-500">正在恢复当前会话草稿工作台…</p>
          </Card>
        ) : null}
        {!loading ? (
          <Card className="mb-6 rounded-[28px] border-[#dbe4f4] bg-[linear-gradient(135deg,#ffffff_0%,#eef5ff_100%)] p-5 shadow-sm">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-xs tracking-[0.24em] text-[#6f7d92]">CURRENT DRAFT</p>
                <h2 className="mt-2 text-[24px] font-semibold text-[#243444]">{banner.title}</h2>
                <p className="mt-2 max-w-3xl text-sm leading-7 text-[#5f6f84]">{banner.detail}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[20px] border border-[#dbe4f4] bg-white px-4 py-3">
                  <p className="text-xs tracking-[0.2em] text-[#7a8494]">当前状态</p>
                  <p className="mt-2 text-base font-semibold text-[#243444]">{taskStatusLabel}</p>
                </div>
                <div className="rounded-[20px] border border-[#dbe4f4] bg-white px-4 py-3">
                  <p className="text-xs tracking-[0.2em] text-[#7a8494]">生命周期阶段</p>
                  <p className="mt-2 text-base font-semibold text-[#243444]">{taskStageLabel}</p>
                </div>
                <div className="rounded-[20px] border border-[#dbe4f4] bg-white px-4 py-3">
                  <p className="text-xs tracking-[0.2em] text-[#7a8494]">当前入口语义</p>
                  <p className="mt-2 text-base font-semibold text-[#243444]">{task ? `已恢复草稿 ${task.id.slice(0, 8)}` : "空工作台，不自动建任务"}</p>
                </div>
                <div className="rounded-[20px] border border-[#dbe4f4] bg-white px-4 py-3">
                  <p className="text-xs tracking-[0.2em] text-[#7a8494]">下一步</p>
                  <p className="mt-2 text-base font-semibold text-[#243444]">{stageOneLabel} / {stageTwoLabel}</p>
                </div>
              </div>
            </div>
          </Card>
        ) : null}
        {!loading && lastSubmittedTaskTitle ? (
          <Card className="mb-6 rounded-[24px] border-emerald-200 bg-emerald-50/80 p-4 shadow-sm">
            <p className="text-sm font-semibold text-emerald-800">任务已进入任务列表</p>
            <p className="mt-2 text-sm leading-7 text-emerald-700">
              {lastSubmittedTaskTitle} 已升格为正式任务，当前工作台已经清空，可继续上传下一条。
            </p>
          </Card>
        ) : null}
        {!loading && notice ? <p className="mb-6 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</p> : null}
        {!loading && error ? <p className="mb-6 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
        {!loading && task?.error_message ? <p className="mb-6 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">后端错误：{task.error_message}</p> : null}
        <div className="grid gap-6 xl:grid-cols-[1.7fr_0.62fr]">
          <div className="space-y-5">
            <Card className="rounded-[30px] border-[#dbe4f4] bg-white p-5 shadow-sm">
              <p className="text-sm font-semibold text-[#243444]">请上传你要处理的视频和标准文案</p>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <label className="flex min-h-[84px] cursor-pointer items-center justify-center rounded-full border border-[#ddcfbe] bg-[#fffdf8] px-4 py-3 text-center text-[17px] font-semibold tracking-[0.02em] text-[#302520] transition hover:border-[#c8b49b] hover:bg-[#fff8ec]">
                  上传视频
                  <Input
                    className="hidden"
                    disabled={busyAction === "upload"}
                    key={`video-input-${inputResetToken}`}
                    onChange={(event) => {
                      setLastSubmittedTaskTitle(null);
                      setNotice(null);
                      setError(null);
                      setVideoFile(event.target.files?.[0] ?? null);
                      setUploadProgress(0);
                      setUploadState("idle");
                    }}
                    type="file"
                  />
                </label>
                <label className="flex min-h-[84px] cursor-pointer items-center justify-center rounded-full border border-[#ddcfbe] bg-[#fffdf8] px-4 py-3 text-center text-[17px] font-semibold tracking-[0.02em] text-[#302520] transition hover:border-[#c8b49b] hover:bg-[#fff8ec]">
                  上传标准文案
                  <Input
                    className="hidden"
                    disabled={busyAction === "upload"}
                    key={`reference-input-${inputResetToken}`}
                    onChange={(event) => {
                      setLastSubmittedTaskTitle(null);
                      setNotice(null);
                      setError(null);
                      setReferenceFile(event.target.files?.[0] ?? null);
                      setUploadProgress(0);
                      setUploadState("idle");
                    }}
                    type="file"
                  />
                </label>
                <button
                  className="min-h-[84px] rounded-full border border-[#2f2520] bg-[#2f2520] px-4 py-3 text-center text-[17px] font-semibold tracking-[0.02em] text-white transition hover:bg-[#3a2d27] disabled:cursor-not-allowed disabled:border-[#c9beb0] disabled:bg-[#ded5ca] disabled:text-[#fffaf3]"
                  disabled={!canAnalyze || busyAction !== null}
                  onClick={handleAnalyze}
                  type="button"
                >
                  开始分析
                </button>
              </div>

              <div className="mt-5 space-y-3">
                <div className="rounded-[20px] border border-[#d9dee8] bg-white px-5 py-4">
                  <div className="flex flex-wrap items-center gap-3 text-[15px]">
                    <span className="font-semibold text-[#394150]">视频文件</span>
                    <span className="min-w-0 flex-1 truncate text-[#4d5a6a]">{uploadSummary}</span>
                    <span className={`rounded-full px-3 py-1 text-[13px] font-semibold ${videoUploaded ? "bg-[#eef9f3] text-[#29a768]" : uploadInFlight ? "bg-[#fff5e6] text-[#d98a1d]" : "bg-[#f4f6f9] text-[#6c7788]"}`}>
                      {videoStatus}
                    </span>
                  </div>
                  <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[#edf1f6]">
                    <div
                      className="h-full rounded-full bg-[linear-gradient(90deg,#f6b24f_0%,#ffcf7e_100%)] transition-[width] duration-300"
                      style={{ width: `${videoProgressValue}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-[#7a8494]">{videoProgressHint}</p>
                </div>
                <div className="rounded-[20px] border border-[#d9dee8] bg-white px-5 py-4">
                  <div className="flex flex-wrap items-center gap-3 text-[15px]">
                    <span className="font-semibold text-[#394150]">标准文案</span>
                    <span className="min-w-0 flex-1 truncate text-[#4d5a6a]">{referenceSummary}</span>
                    <span className={`rounded-full px-3 py-1 text-[13px] font-semibold ${referenceUploaded ? "bg-[#eef9f3] text-[#29a768]" : uploadInFlight ? "bg-[#fff5e6] text-[#d98a1d]" : "bg-[#f4f6f9] text-[#6c7788]"}`}>
                      {referenceStatus}
                    </span>
                  </div>
                  <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[#edf1f6]">
                    <div
                      className="h-full rounded-full bg-[linear-gradient(90deg,#f6b24f_0%,#ffcf7e_100%)] transition-[width] duration-300"
                      style={{ width: `${referenceProgressValue}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-[#7a8494]">{referenceProgressHint}</p>
                </div>
              </div>
            </Card>

            <Card className="rounded-[30px] border-[#c9dcff] bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="text-[18px] font-semibold text-[#2f3848]">你可以手动修改识别结果，选择删除线即可</h2>
                </div>
                <label className="flex items-center gap-3 text-sm text-[#465067]">
                  <input checked={feedToAi} className="h-4 w-4 accent-[#4b86ff]" onChange={(event) => setFeedToAi(event.target.checked)} type="checkbox" />
                  投喂本文案给 AI
                </label>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  className={`rounded-full px-4 py-2 text-sm font-medium ${editorTab === "script" ? "bg-[#eaf3ff] text-[#4a85f6]" : "border border-[#dde4ef] bg-white text-stone-500"}`}
                  onClick={() => setEditorTab("script")}
                  type="button"
                >
                  识别结果
                </button>
                <button
                  className={`rounded-full px-4 py-2 text-sm font-medium ${editorTab === "groundtruth" ? "bg-[#eef2f7] text-[#667085]" : "border border-[#dde4ef] bg-white text-stone-500"}`}
                  onClick={() => setEditorTab("groundtruth")}
                  type="button"
                >
                  标准文案
                </button>
                <div className="flex flex-wrap items-center gap-2 md:ml-3">
                  <Button
                    className="h-10 px-4"
                    disabled={scriptActionsDisabled || !editorControls.canMarkDelete}
                    onClick={() => scriptEditorRef.current?.markDelete()}
                    type="button"
                  >
                    标记删除
                  </Button>
                  <Button
                    className="h-10 px-4"
                    disabled={scriptActionsDisabled || !editorControls.canRestore}
                    onClick={() => scriptEditorRef.current?.restoreSelection()}
                    type="button"
                    variant="secondary"
                  >
                    恢复保留
                  </Button>
                  <Button
                    className="h-10 px-4"
                    disabled={scriptActionsDisabled || !editorControls.canClear}
                    onClick={() => scriptEditorRef.current?.clearMarks()}
                    type="button"
                    variant="ghost"
                  >
                    清空删除标记
                  </Button>
                </div>
                <span className="text-xs text-[#7a8494]">
                  {scriptActionsVisible
                    ? editorControls.selectedCount > 0
                      ? `当前选中 ${editorControls.selectedCount} 个字`
                      : "请先在识别结果中拖选文字"
                    : "标准文案模式下仅展示，不可编辑"}
                </span>
              </div>

              <div className="mt-4 rounded-[22px] border border-[#dbe4f4] bg-[#fcfdff] p-4">
                {editorTab === "script" ? (
                  task?.analyze_script ? (
                    <SmartCutScriptEditor
                      disabled={busyAction === "preview" || task.status === "previewing" || task.status === "finalizing"}
                      onStateChange={setEditorControls}
                      onScriptChange={setScriptDraft}
                      ref={scriptEditorRef}
                      script={scriptDraft || task.analyze_script}
                    />
                  ) : (
                    <div className="min-h-[420px] rounded-[18px] border border-[#dfe6f2] bg-white px-5 py-5 text-[16px] leading-9 text-[#313b4a]">
                      <p className="text-stone-400">示例：</p>
                      <p className="mt-3">今天我来讲一下这个功能，</p>
                      <p className="line-through decoration-2">这个地方先删了要删掉，</p>
                      <p>后面这一句保留继续生成试听。</p>
                    </div>
                  )
                ) : (
                  <div className="min-h-[420px] rounded-[18px] border border-[#dfe6f2] bg-white px-5 py-5 text-[16px] leading-8 text-stone-500">
                    {task?.groundtruth_url ? (
                      <a className="text-[#4a85f6] underline" href={task.groundtruth_url} rel="noreferrer" target="_blank">
                        查看标准文案
                      </a>
                    ) : (
                      <p>这里将显示标准</p>
                    )}
                  </div>
                )}
              </div>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="rounded-[26px] border-[#e6ddd2] bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <p className="text-[20px] font-semibold text-[#241714]">输出音频预览</p>
                <Button
                  className="h-10 rounded-full bg-[#2f3945] px-5 text-white hover:bg-[#39444f]"
                  disabled={!canPreview || busyAction !== null}
                  onClick={handlePreview}
                  type="button"
                >
                  开始生成试听
                </Button>
              </div>
              <div className="mt-5 rounded-[24px] border border-dashed border-[#ddd2c4] bg-[#fffdfa] p-6">
                {audioPreviewUrl ? (
                  <div className="space-y-4">
                    <div className="rounded-[18px] border border-[#ece2d4] bg-white px-4 py-3">
                      <p className="text-xs tracking-[0.2em] text-[#7a7267]">CURRENT AUDIO</p>
                      <p className="mt-2 text-base font-semibold text-[#241714]">{audioPreviewLabel}</p>
                      <p className="mt-1 text-sm text-[#7b7267]">
                        {previewReady ? "当前播放器展示的是用户修改删除线之后的 audio_b。" : "Analyze 完成后，这里会先回显首版 audio_a。"}
                      </p>
                    </div>
                    <audio className="w-full" controls src={audioPreviewUrl} />
                  </div>
                ) : (
                  <div className="flex min-h-[240px] flex-col items-center justify-center text-center">
                    <p className="text-[24px] font-semibold text-[#241714]">还没有生成音频</p>
                    <p className="mt-6 max-w-[280px] text-[16px] leading-9 text-[#7b7267]">
                      Analyze 完成后这里先显示 audio_a，点击上方生成试听后再切到 audio_b。
                    </p>
                  </div>
                )}
              </div>
            </Card>

            <Card className="rounded-[24px] border-[#e6ddd2] bg-white p-5 shadow-sm">
              <p className="text-[20px] font-semibold text-[#2f3848]">输出视频规格</p>
              <div className="mt-5 space-y-5 text-[18px] leading-10 text-[#465067]">
                <label className="flex items-center gap-4">
                  <input checked={outputMode === "vertical_1080p"} className="h-5 w-5 accent-[#2d6cff]" onChange={() => setOutputMode("vertical_1080p")} type="radio" />
                  <span>1080P竖屏高清</span>
                </label>
                <label className="flex items-center gap-4">
                  <input checked={outputMode === "original"} className="h-5 w-5 accent-[#2d6cff]" onChange={() => setOutputMode("original")} type="radio" />
                  <span>持输入视频尺寸</span>
                </label>
              </div>
            </Card>

            <div className="space-y-3">
              <Button
                className="h-[88px] w-full rounded-full bg-[#2f3945] text-[26px] font-semibold text-white hover:bg-[#39444f]"
                disabled={!canFinalize || busyAction !== null}
                onClick={handleFinalize}
                type="button"
              >
                开始生成视频
              </Button>
              {downloadReady ? (
                <a
                  className="block text-center text-sm font-medium text-[#23835f] underline underline-offset-4"
                  href={task?.final_video_url ?? "#"}
                  target="_blank"
                >
                  下载已生成视频
                </a>
              ) : null}
            </div>

          </div>
        </div>
      </section>
    </UserWorkspaceShell>
  );
}
