"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthResponse } from "@/lib/auth";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  abandonTask,
  getSmartCutEdits,
  getSmartCutRuns,
  getSmartCutTask,
  SmartCutEdit,
  SmartCutTask,
  SmartCutTaskRun,
  startFinalize,
  startPreview,
  startSmartCutTask,
  uploadDirectInputs,
} from "@/lib/smart-cut";
import { SmartCutScriptEditor, SmartCutScriptEditorHandle } from "@/components/smart-cut/script-editor";

function labelStatus(status?: string | null) {
  if (!status) return "待同步";
  const mapping: Record<string, string> = {
    waiting_upload: "待上传素材",
    analyzing: "分析中",
    waiting_user: "待人工确认",
    previewing: "试听生成中",
    finalizing: "生成视频中",
    success: "已完成",
    abandoned: "已放弃",
    analyze_failed: "分析失败",
  };
  return mapping[status] ?? status;
}

function labelStage(stage?: string | null) {
  if (!stage) return "等待推进";
  const mapping: Record<string, string> = {
    upload: "上传",
    analyze: "分析",
    user_select: "人工确认 / 试听",
    preview: "试听",
    finalize: "视频生成",
    complete: "完成",
  };
  return mapping[stage] ?? stage;
}

function formatTs(value?: string | null) {
  if (!value) return "--";
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

function summarizeName(value: string | null | undefined) {
  if (!value) return "尚未上传";
  return value.split("?")[0]?.split("/").filter(Boolean).pop() ?? value;
}

function latestSuccessfulEdit(edits: SmartCutEdit[]) {
  return edits.find((edit) => edit.status === "success") ?? null;
}

export function SmartCutWorkspace({ taskId }: { taskId?: string }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const workspace = useUserWorkspaceData(user?.username, user?.company_id);
  const [task, setTask] = useState<SmartCutTask | null>(null);
  const [edits, setEdits] = useState<SmartCutEdit[]>([]);
  const [runs, setRuns] = useState<SmartCutTaskRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"start" | "upload" | "preview" | "finalize" | "abandon" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [scriptDraft, setScriptDraft] = useState("");
  const [outputMode, setOutputMode] = useState<"original" | "vertical_1080p">("original");
  const [feedToAi, setFeedToAi] = useState(true);
  const [uploadProgress, setUploadProgress] = useState(0);
  const editorRef = useRef<SmartCutScriptEditorHandle>(null);
  const [editorState, setEditorState] = useState({
    canMarkDelete: false,
    canRestore: false,
    canClear: false,
    selectedCount: 0,
  });

  const currentEdit = useMemo(() => latestSuccessfulEdit(edits), [edits]);
  const canUpload = Boolean(task && task.status === "waiting_upload" && videoFile && referenceFile && busy === null);
  const canPreview = Boolean(task && ["waiting_user", "success"].includes(task.status) && scriptDraft.trim().length > 0 && busy === null);
  const canFinalize = Boolean(task && ["waiting_user", "success"].includes(task.status) && currentEdit?.edited_delay_cuts_tos_key && busy === null);
  const audioUrl = currentEdit?.audio_b_url ?? currentEdit?.audio_a_url ?? null;
  const audioLabel = currentEdit?.audio_b_url ? "试听音频 audio_b" : currentEdit?.audio_a_url ? "分析音频 audio_a" : null;

  async function loadTask(nextTaskId: string) {
    const [taskPayload, editsPayload, runsPayload] = await Promise.all([
      getSmartCutTask(nextTaskId),
      getSmartCutEdits(nextTaskId).catch(() => []),
      getSmartCutRuns(nextTaskId).catch(() => []),
    ]);
    setTask(taskPayload);
    setEdits(editsPayload);
    setRuns(runsPayload);
    setScriptDraft(latestSuccessfulEdit(editsPayload)?.edited_script ?? editsPayload[0]?.edited_script ?? taskPayload.analyze_script ?? "");
    return taskPayload;
  }

  async function bootstrap() {
    setLoading(true);
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
    if (taskId) {
      await loadTask(taskId);
    } else {
      setTask(null);
      setEdits([]);
      setRuns([]);
      setScriptDraft("");
    }
    setLoading(false);
  }

  useEffect(() => {
    void bootstrap().catch((err) => {
      setError(err instanceof Error ? err.message : "初始化失败");
      setLoading(false);
    });
  }, [taskId]);

  useEffect(() => {
    if (!task) return;
    if (!["analyzing", "previewing", "finalizing"].includes(task.status)) return;
    const timer = window.setInterval(() => {
      void loadTask(task.id).catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [task]);

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  async function handleStartTask() {
    if (!user) return;
    setBusy("start");
    setError(null);
    setNotice(null);
    try {
      const nextTask = await startSmartCutTask(user.username, user.company_id);
      setNotice("任务卡已创建，请上传素材。");
      router.push(`/smart-cut/${nextTask.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "开启任务失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleUploadAndAnalyze() {
    if (!task || !videoFile || !referenceFile) return;
    setBusy("upload");
    setError(null);
    setNotice(null);
    try {
      const nextTask = await uploadDirectInputs(task.id, videoFile, referenceFile, {
        onProgress: setUploadProgress,
      });
      await loadTask(nextTask.id);
      setNotice("素材上传完成，系统已自动开始分析。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setBusy(null);
    }
  }

  async function handlePreview() {
    if (!task) return;
    setBusy("preview");
    setError(null);
    setNotice(null);
    try {
      await startPreview(task.id, scriptDraft);
      await loadTask(task.id);
      setNotice("试听任务已提交，页面会自动刷新最新音频。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成试听失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleFinalize() {
    if (!task) return;
    setBusy("finalize");
    setError(null);
    setNotice(null);
    try {
      const result = await startFinalize(task.id, { outputMode, feedToAi });
      setNotice(`${result.taskTitle} 已进入任务列表继续处理。`);
      router.push("/tasks");
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成视频失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleAbandon() {
    if (!task) return;
    setBusy("abandon");
    setError(null);
    try {
      await abandonTask(task.id);
      setNotice("当前任务已放弃。");
      router.push("/smart-cut");
    } catch (err) {
      setError(err instanceof Error ? err.message : "放弃任务失败");
    } finally {
      setBusy(null);
    }
  }

  return (
    <UserWorkspaceShell
      activeItem="smart-cut"
      currentUser={user?.username ?? "..."}
      headline={user?.company_name ? `你好，${user.company_name}，小马AI准备就绪~` : undefined}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <section className="rounded-[32px] border border-[#dde1ea] bg-[#f7f9fc] p-6 shadow-[0_8px_24px_rgba(78,91,117,0.06)]">
        <Card className="mb-6 rounded-[28px] border-[#dbe4f4] bg-[linear-gradient(135deg,#ffffff_0%,#eef5ff_100%)] p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs tracking-[0.24em] text-[#6f7d92]">SMART CUT TASK</p>
              <h2 className="mt-2 text-[24px] font-semibold text-[#243444]">
                {task ? (task.task_title || `任务 ${task.id.slice(0, 8)}`) : "空工作台，等待开启任务"}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-7 text-[#5f6f84]">
                {task
                  ? "当前页只围绕一个显式主任务工作。上传完成后系统会自动分析；试听是可选循环，生成视频可以直接基于 analyze 结果。"
                  : "进入页面不会自动建隐藏草稿。点击“开启任务”后，所有上传、分析、试听和生成视频都会绑定到同一张主任务卡。"}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[20px] border border-[#dbe4f4] bg-white px-4 py-3">
                <p className="text-xs tracking-[0.2em] text-[#7a8494]">当前状态</p>
                <p className="mt-2 text-base font-semibold text-[#243444]">{task ? labelStatus(task.status) : "未创建任务"}</p>
              </div>
              <div className="rounded-[20px] border border-[#dbe4f4] bg-white px-4 py-3">
                <p className="text-xs tracking-[0.2em] text-[#7a8494]">阶段</p>
                <p className="mt-2 text-base font-semibold text-[#243444]">{task ? labelStage(task.current_stage) : "等待开启"}</p>
              </div>
            </div>
          </div>
        </Card>

        {notice ? <p className="mb-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</p> : null}
        {error ? <p className="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

        {!task ? (
          <Card className="rounded-[30px] border-[#dbe4f4] bg-white p-8 shadow-sm">
            <div className="space-y-4 text-center">
              <p className="text-lg font-semibold text-[#243444]">当前没有活动任务</p>
              <p className="text-sm leading-7 text-stone-500">开启任务后，你会得到一张主任务卡。之后所有上传、analyze、preview、finalize 都只围绕这张任务卡推进。</p>
              <div className="pt-2">
                <Button disabled={busy !== null || !user} onClick={handleStartTask} type="button">
                  {busy === "start" ? "创建中..." : "开启任务"}
                </Button>
              </div>
            </div>
          </Card>
        ) : (
          <div className="grid gap-6 xl:grid-cols-[1.7fr_0.62fr]">
            <div className="space-y-5">
              <Card className="rounded-[30px] border-[#dbe4f4] bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[#243444]">请上传你要处理的视频和标准文案</p>
                  <div className="flex gap-2">
                    <Button disabled={busy !== null} onClick={handleAbandon} type="button" variant="secondary">
                      放弃任务
                    </Button>
                  </div>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="flex min-h-[84px] cursor-pointer items-center justify-center rounded-full border border-[#ddcfbe] bg-[#fffdf8] px-4 py-3 text-center text-[17px] font-semibold text-[#302520]">
                    上传视频
                    <Input className="hidden" disabled={busy !== null} onChange={(event) => setVideoFile(event.target.files?.[0] ?? null)} type="file" />
                  </label>
                  <label className="flex min-h-[84px] cursor-pointer items-center justify-center rounded-full border border-[#ddcfbe] bg-[#fffdf8] px-4 py-3 text-center text-[17px] font-semibold text-[#302520]">
                    上传标准文案
                    <Input className="hidden" disabled={busy !== null} onChange={(event) => setReferenceFile(event.target.files?.[0] ?? null)} type="file" />
                  </label>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <Button disabled={!canUpload} onClick={handleUploadAndAnalyze} type="button">
                    {busy === "upload" ? `上传中 ${uploadProgress}%` : "上传并自动开始分析"}
                  </Button>
                  <span className="text-sm text-stone-500">视频：{videoFile?.name ?? summarizeName(task.original_video_url)}</span>
                  <span className="text-sm text-stone-500">文案：{referenceFile?.name ?? summarizeName(task.reference_text_url)}</span>
                </div>
              </Card>

              <Card className="rounded-[30px] border-[#c9dcff] bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <h2 className="text-[18px] font-semibold text-[#2f3848]">删除线调整与试听</h2>
                    <p className="mt-2 text-sm leading-7 text-stone-500">Analyze 完成后可直接改删除线并试听，也可以跳过试听直接生成视频。</p>
                  </div>
                  <label className="flex items-center gap-3 text-sm text-[#465067]">
                    <input checked={feedToAi} className="h-4 w-4 accent-[#4b86ff]" onChange={(event) => setFeedToAi(event.target.checked)} type="checkbox" />
                    投喂本文案给 AI
                  </label>
                </div>

                <div className="mt-4 flex flex-wrap gap-3">
                  <Button disabled={busy !== null || !editorState.canMarkDelete} onClick={() => editorRef.current?.markDelete()} type="button">
                    标记删除
                  </Button>
                  <Button disabled={busy !== null || !editorState.canRestore} onClick={() => editorRef.current?.restoreSelection()} type="button" variant="secondary">
                    恢复保留
                  </Button>
                  <Button disabled={busy !== null || !editorState.canClear} onClick={() => editorRef.current?.clearMarks()} type="button" variant="secondary">
                    清空删除标记
                  </Button>
                  <Button disabled={!canPreview} onClick={handlePreview} type="button">
                    {busy === "preview" ? "生成试听中..." : "开始生成试听"}
                  </Button>
                  <Button disabled={!canFinalize} onClick={handleFinalize} type="button">
                    {busy === "finalize" ? "开始生成视频..." : "开始生成视频"}
                  </Button>
                </div>

                <div className="mt-5">
                  <SmartCutScriptEditor
                    disabled={!task || task.status === "analyzing" || task.status === "finalizing"}
                    onScriptChange={setScriptDraft}
                    onStateChange={setEditorState}
                    ref={editorRef}
                    script={scriptDraft}
                  />
                </div>
              </Card>
            </div>

            <div className="space-y-5">
              <Card className="rounded-[28px] border-[#dbe4f4] bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-[#243444]">输出音频预览</p>
                <div className="mt-4 rounded-[24px] border border-dashed border-[#d9dee8] p-4">
                  {audioUrl ? (
                    <div className="space-y-4">
                      <p className="text-sm font-semibold text-[#243444]">{audioLabel}</p>
                      <audio className="w-full" controls src={audioUrl} />
                    </div>
                  ) : (
                    <p className="text-sm leading-7 text-stone-500">Analyze 完成后这里会先显示 `audio_a`，试听成功后切到 `audio_b`。</p>
                  )}
                </div>
              </Card>

              <Card className="rounded-[28px] border-[#dbe4f4] bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-[#243444]">输出视频规格</p>
                <div className="mt-4 space-y-3 text-sm text-stone-600">
                  <label className="flex items-center gap-3">
                    <input checked={outputMode === "vertical_1080p"} onChange={() => setOutputMode("vertical_1080p")} type="radio" />
                    1080P竖屏高清
                  </label>
                  <label className="flex items-center gap-3">
                    <input checked={outputMode === "original"} onChange={() => setOutputMode("original")} type="radio" />
                    保持输入视频尺寸
                  </label>
                </div>
              </Card>

              <Card className="rounded-[28px] border-[#dbe4f4] bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-[#243444]">任务时间线</p>
                <div className="mt-4 space-y-3">
                  {runs.length === 0 ? (
                    <p className="text-sm text-stone-500">当前还没有子执行记录。</p>
                  ) : (
                    runs.map((run) => (
                      <div key={run.id} className="rounded-[18px] border border-[#e2e8f0] bg-[#fafcff] p-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-[#243444]">{run.run_type} #{run.sequence_number}</p>
                          <span className="text-xs text-stone-500">{run.status}</span>
                        </div>
                        <p className="mt-2 text-xs text-stone-500">创建：{formatTs(run.created_at)}</p>
                        {run.error_message ? <p className="mt-2 text-xs text-rose-600">{run.error_message}</p> : null}
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>
          </div>
        )}
      </section>
    </UserWorkspaceShell>
  );
}
