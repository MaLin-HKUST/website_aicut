"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { AuthResponse } from "@/lib/auth";
import {
  abandonTask,
  getSmartCutContinueLabel,
  getSmartCutTask,
  isSmartCutDeletable,
  listSmartCutTasks,
  SmartCutTask,
  SmartCutTaskSummary,
  updateSmartCutTaskTitle,
} from "@/lib/smart-cut";
import { listTaskCenterItems, TaskCenterItem } from "@/lib/task-center";

const FILTERS = [
  { key: "all", label: "全部" },
  { key: "running", label: "执行中" },
  { key: "waiting", label: "等待中" },
  { key: "finished", label: "已完成" },
  { key: "failed", label: "失败" },
] as const;

type FilterKey = (typeof FILTERS)[number]["key"];
type QueueStatus = TaskCenterItem["status"];

type UserTaskListItem = {
  id: string;
  title: string;
  taskType: "smart_cut";
  status: QueueStatus;
  rawStatus: string | null;
  progress: number;
  currentStage: string;
  updatedAt: string;
  createdAt: string;
  downloadUrl?: string | null;
  errorMessage?: string | null;
  inputSummary: string[];
  outputSummary?: string[];
};

function statusLabel(status: QueueStatus) {
  if (status === "queued") return "排队中";
  if (status === "running") return "执行中";
  if (status === "waiting") return "等待中";
  if (status === "finished") return "已完成";
  return "失败";
}

function statusTone(status: QueueStatus) {
  if (status === "finished") return "bg-emerald-100 text-emerald-700";
  if (status === "queued") return "bg-blue-100 text-blue-700";
  if (status === "failed") return "bg-rose-100 text-rose-700";
  return "bg-amber-100 text-amber-700";
}

function smartCutStatusLabel(status?: string | null) {
  const mapping: Record<string, string> = {
    waiting_upload: "待上传素材",
    ready_analyze: "待启动分析",
    analyzing: "分析中",
    analyze_failed: "分析失败",
    waiting_user: "待人工确认",
    previewing: "试听生成中",
    preview_failed: "试听失败",
    finalizing: "生成视频中",
    finalize_failed: "生成失败",
    success: "已完成",
    abandoned: "已放弃",
  };
  if (!status) return "待同步";
  return mapping[status] ?? status;
}

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

function summarizeName(value: string | null | undefined) {
  if (!value) return null;
  return value.split("?")[0]?.split("/").filter(Boolean).pop() ?? value;
}

function formatSmartCutStage(value: string | null | undefined) {
  const mapping: Record<string, string> = {
    upload: "上传",
    analyze: "分析",
    user_select: "人工确认 / 试听",
    preview: "试听",
    finalize: "视频生成",
    complete: "完成",
  };
  if (!value) return "等待推进";
  return mapping[value] ?? smartCutStatusLabel(value);
}

function rawStatusToQueueStatus(status: string): QueueStatus {
  if (status === "success") return "finished";
  if (["analyze_failed", "preview_failed", "finalize_failed", "abandoned"].includes(status)) return "failed";
  if (["waiting_upload", "ready_analyze"].includes(status)) return "queued";
  if (status === "waiting_user") return "waiting";
  return "running";
}

function rawStatusToProgress(status: string) {
  const mapping: Record<string, number> = {
    waiting_upload: 5,
    ready_analyze: 15,
    analyzing: 35,
    analyze_failed: 35,
    waiting_user: 65,
    previewing: 75,
    preview_failed: 75,
    finalizing: 90,
    finalize_failed: 90,
    success: 100,
    abandoned: 0,
  };
  return mapping[status] ?? 0;
}

function buildSharedQueueItem(item: TaskCenterItem): UserTaskListItem {
  return {
    id: item.id,
    title: item.title,
    taskType: "smart_cut",
    status: item.status,
    rawStatus: null,
    progress: item.progress,
    currentStage: item.currentStage,
    updatedAt: item.updatedAt,
    createdAt: item.createdAt,
    downloadUrl: item.downloadUrl ?? null,
    errorMessage: item.errorMessage ?? null,
    inputSummary: item.inputSummary,
    outputSummary: item.outputSummary,
  };
}

function buildSelfQueueItem(summary: SmartCutTaskSummary, existing?: UserTaskListItem): UserTaskListItem {
  return {
    id: summary.id,
    title: existing?.title ?? `智能剪气口-${summary.id.slice(0, 8)}`,
    taskType: "smart_cut",
    status: rawStatusToQueueStatus(summary.status),
    rawStatus: summary.status,
    progress: rawStatusToProgress(summary.status),
    currentStage: formatSmartCutStage(summary.current_stage ?? summary.status),
    updatedAt: summary.updated_at,
    createdAt: summary.created_at,
    downloadUrl: existing?.downloadUrl ?? null,
    errorMessage: existing?.errorMessage ?? null,
    inputSummary: existing?.inputSummary ?? [],
    outputSummary: existing?.outputSummary ?? [],
  };
}

function buildDetailInputSummary(task: SmartCutTask, fallback: string[]) {
  const entries = [summarizeName(task.original_video_url), summarizeName(task.reference_text_url)].filter(Boolean) as string[];
  return entries.length > 0 ? entries : fallback;
}

function buildDetailOutputSummary(task: SmartCutTask, fallback: string[]) {
  const entries = [
    summarizeName(task.asr_result_tos_key),
    summarizeName(task.audio_b_url),
    summarizeName(task.final_video_url),
    summarizeName(task.groundtruth_url),
  ].filter(Boolean) as string[];
  return entries.length > 0 ? entries : fallback;
}

function filteredOutSelected(items: UserTaskListItem[], filter: FilterKey, selectedId: string) {
  if (!selectedId) return false;
  return !items.some((item) => item.id === selectedId && (filter === "all" || item.status === filter));
}

export function UserTasksShell() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const [items, setItems] = useState<UserTaskListItem[]>([]);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selectedTaskDetail, setSelectedTaskDetail] = useState<SmartCutTask | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailNotice, setDetailNotice] = useState<string | null>(null);
  const [deletingTaskId, setDeletingTaskId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [renamingTaskId, setRenamingTaskId] = useState<string | null>(null);
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
        router.replace("/admin/tasks");
        return;
      }

      setUser(payload.user);

      try {
        const [sharedItems, ownTasks] = await Promise.all([
          listTaskCenterItems({
            mode: "user",
            userId: payload.user.username,
            companyId: payload.user.company_id,
          }),
          listSmartCutTasks({
            userId: payload.user.username,
            limit: 50,
          }),
        ]);

        const merged = new Map<string, UserTaskListItem>();
        for (const item of sharedItems) {
          merged.set(item.id, buildSharedQueueItem(item));
        }
        for (const item of ownTasks.filter((task) => task.status !== "abandoned")) {
          merged.set(item.id, buildSelfQueueItem(item, merged.get(item.id)));
        }

        const nextItems = Array.from(merged.values()).sort(
          (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
        );
        setItems(nextItems);

        const requestedId = searchParams.get("taskId");
        setSelectedId(requestedId || nextItems[0]?.id || "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "读取任务失败");
      }
    }

    void bootstrap();
  }, [router, searchParams]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedTaskDetail(null);
      setDetailError(null);
      setDetailNotice(null);
      setEditingTitle(false);
      setTitleDraft("");
      return;
    }

    let cancelled = false;

    async function loadDetail() {
      try {
        setDetailError(null);
        setDetailNotice(null);
        setSelectedTaskDetail(null);
        const task = await getSmartCutTask(selectedId);
        if (cancelled) return;
        setSelectedTaskDetail(task);
      } catch (err) {
        if (cancelled) return;
        setSelectedTaskDetail(null);
        setDetailError(err instanceof Error ? err.message : "读取任务详情失败");
      }
    }

    void loadDetail();

    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  useEffect(() => {
    if (filteredOutSelected(items, filter, selectedId)) {
      const nextSelectedId = items.find((item) => filter === "all" || item.status === filter)?.id ?? "";
      setSelectedId(nextSelectedId);
    }
  }, [filter, items, selectedId]);

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  const filteredItems = useMemo(
    () => items.filter((item) => filter === "all" || item.status === filter),
    [filter, items],
  );

  const selectedTask = filteredItems.find((item) => item.id === selectedId) ?? filteredItems[0] ?? null;
  const activeTaskDetail = selectedTaskDetail && selectedTaskDetail.id === selectedTask?.id ? selectedTaskDetail : null;
  const continueLabel = getSmartCutContinueLabel(activeTaskDetail?.status ?? selectedTask?.rawStatus);
  const detailTitle =
    activeTaskDetail?.task_title || selectedTask?.title || (activeTaskDetail ? `智能剪气口-${activeTaskDetail.id.slice(0, 8)}` : "");
  const inputSummary = activeTaskDetail
    ? buildDetailInputSummary(activeTaskDetail, selectedTask?.inputSummary ?? [])
    : selectedTask?.inputSummary ?? [];
  const outputSummary = activeTaskDetail
    ? buildDetailOutputSummary(activeTaskDetail, selectedTask?.outputSummary ?? [])
    : selectedTask?.outputSummary ?? [];
  const detailStatusText = smartCutStatusLabel(activeTaskDetail?.status ?? selectedTask?.rawStatus);
  const detailStageText = activeTaskDetail
    ? formatSmartCutStage(activeTaskDetail.current_stage)
    : selectedTask?.currentStage ?? "等待推进";
  const sharedTaskNotice =
    activeTaskDetail &&
    user &&
    activeTaskDetail.user_id !== user.username &&
    activeTaskDetail.company_id !== null &&
    activeTaskDetail.company_id === user.company_id
      ? `当前打开的是 ${activeTaskDetail.user_id} 的同公司共享任务。`
      : null;
  const canDeleteTask = Boolean(
    activeTaskDetail &&
      user &&
      activeTaskDetail.user_id === user.username &&
      isSmartCutDeletable(activeTaskDetail.status) &&
      deletingTaskId === null,
  );
  const canRenameTask = Boolean(activeTaskDetail && user && activeTaskDetail.user_id === user.username);

  async function handleDeleteTask() {
    if (!activeTaskDetail) return;
    let nextSelectedId = "";
    setDeletingTaskId(activeTaskDetail.id);
    setDetailError(null);
    setDetailNotice(null);
    try {
      await abandonTask(activeTaskDetail.id);
      setItems((current) => {
        const remaining = current.filter((item) => item.id !== activeTaskDetail.id);
        nextSelectedId = remaining[0]?.id ?? "";
        return remaining;
      });
      setSelectedTaskDetail(null);
      setSelectedId((current) => (current === activeTaskDetail.id ? nextSelectedId : current));
      setDetailNotice("当前失败任务已删除。");
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "删除任务失败");
    } finally {
      setDeletingTaskId(null);
    }
  }

  function beginRenameTask() {
    setTitleDraft(detailTitle);
    setEditingTitle(true);
    setDetailError(null);
    setDetailNotice(null);
  }

  async function handleRenameTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeTaskDetail) return;

    const nextTitle = titleDraft.trim();
    if (!nextTitle) {
      setDetailError("任务名称不能为空。");
      return;
    }
    if (nextTitle.length > 120) {
      setDetailError("任务名称不能超过 120 个字符。");
      return;
    }

    setRenamingTaskId(activeTaskDetail.id);
    setDetailError(null);
    setDetailNotice(null);
    try {
      const updatedTask = await updateSmartCutTaskTitle(activeTaskDetail.id, nextTitle);
      const updatedTitle = updatedTask.task_title || nextTitle;
      setSelectedTaskDetail(updatedTask);
      setItems((current) =>
        current.map((item) =>
          item.id === updatedTask.id
            ? {
                ...item,
                title: updatedTitle,
                updatedAt: updatedTask.updated_at,
              }
            : item,
        ),
      );
      setEditingTitle(false);
      setTitleDraft(updatedTitle);
      setDetailNotice("任务名称已更新。");
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "修改任务名称失败");
    } finally {
      setRenamingTaskId(null);
    }
  }

  return (
    <UserWorkspaceShell
      activeItem="tasks"
      currentUser={user?.username ?? "..."}
      headline={user?.company_name ? `你好，${user.company_name}，小马AI准备就绪~` : undefined}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <section className="grid gap-5 xl:grid-cols-[0.92fr_1.08fr]">
        <Card className="rounded-[32px] border-[#e5dacd] bg-white p-6 shadow-panel">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-stone-500">任务中心</p>
              <h2 className="mt-3 text-4xl font-semibold text-[#241714]">任务列表</h2>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            {FILTERS.map((item) => (
              <button
                key={item.key}
                className={[
                  "rounded-full border px-4 py-2 text-sm font-semibold transition",
                  filter === item.key
                    ? "border-[#2b201d] bg-[#2b201d] text-white"
                    : "border-[#dfd5c5] bg-[#faf7f2] text-[#241714]",
                ].join(" ")}
                onClick={() => setFilter(item.key)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>

          {error ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

          <div className="mt-5 space-y-3">
            {filteredItems.length === 0 ? (
              <div className="rounded-[24px] border border-dashed border-[#dccab6] bg-[#fffaf5] p-8 text-center text-sm text-stone-500">
                当前筛选下没有任务
              </div>
            ) : (
              filteredItems.map((item) => (
                <button
                  key={item.id}
                  className={[
                    "block w-full rounded-[24px] border p-4 text-left transition",
                    selectedTask?.id === item.id
                      ? "border-[#2b201d] bg-[#fff8ef]"
                      : "border-[#ebe1d3] bg-[#fffdf9] hover:bg-[#faf4eb]",
                  ].join(" ")}
                  onClick={() => setSelectedId(item.id)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold text-[#241714]">{item.title}</p>
                      <p className="mt-1 text-sm text-stone-500">{item.id}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusTone(item.status)}`}>
                      {statusLabel(item.status)}
                    </span>
                  </div>
                  <div className="mt-4 flex items-center justify-between text-sm text-stone-500">
                    <span>{item.currentStage}</span>
                    <span>{formatTime(item.updatedAt)}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </Card>

        <Card className="rounded-[32px] border-[#e5dacd] bg-[#f8f5ef] p-6 shadow-panel">
          {!selectedTask ? (
            <div className="flex min-h-[480px] items-center justify-center text-sm text-stone-500">请选择一个任务</div>
          ) : (
            <div className="space-y-5">
              <div className="rounded-[28px] border border-[#e4dacb] bg-white p-5">
                <p className="text-xs uppercase tracking-[0.28em] text-stone-500">任务详情</p>
                <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  {editingTitle ? (
                    <form className="flex flex-1 flex-col gap-3 sm:flex-row" onSubmit={handleRenameTask}>
                      <label className="sr-only" htmlFor="task-title-input">
                        任务名称
                      </label>
                      <input
                        id="task-title-input"
                        className="min-h-12 flex-1 rounded-2xl border border-[#d8cbbb] bg-[#fffdf9] px-4 text-base font-semibold text-[#241714] outline-none transition focus:border-[#2b201d] focus:ring-2 focus:ring-[#2b201d]/10"
                        maxLength={120}
                        onChange={(event) => setTitleDraft(event.target.value)}
                        value={titleDraft}
                      />
                      <div className="flex gap-2">
                        <Button disabled={renamingTaskId === activeTaskDetail?.id} type="submit">
                          保存
                        </Button>
                        <Button
                          disabled={renamingTaskId === activeTaskDetail?.id}
                          onClick={() => {
                            setEditingTitle(false);
                            setTitleDraft(detailTitle);
                          }}
                          type="button"
                          variant="secondary"
                        >
                          取消
                        </Button>
                      </div>
                    </form>
                  ) : (
                    <>
                      <h3 className="text-4xl font-semibold text-[#241714]">{detailTitle}</h3>
                      {canRenameTask ? (
                        <Button onClick={beginRenameTask} type="button" variant="secondary">
                          修改名称
                        </Button>
                      ) : null}
                    </>
                  )}
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  <span className={`rounded-full px-4 py-2 text-sm font-semibold ${statusTone(selectedTask.status)}`}>
                    {detailStatusText}
                  </span>
                  <span className="rounded-full border border-[#dfd5c5] bg-[#faf7f2] px-4 py-2 text-sm text-stone-600">
                    {detailStageText}
                  </span>
                </div>
                {sharedTaskNotice ? (
                  <p className="mt-4 rounded-2xl bg-sky-50 px-4 py-3 text-sm text-sky-800">{sharedTaskNotice}</p>
                ) : null}
                {detailNotice ? (
                  <p className="mt-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{detailNotice}</p>
                ) : null}
                {detailError ? (
                  <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{detailError}</p>
                ) : null}
                {activeTaskDetail?.error_message ? (
                  <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{activeTaskDetail.error_message}</p>
                ) : selectedTask.errorMessage ? (
                  <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{selectedTask.errorMessage}</p>
                ) : null}
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <div className="rounded-[24px] border border-[#e4dacb] bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-stone-500">任务类型</p>
                  <p className="mt-3 text-lg font-semibold text-[#241714]">{selectedTask.taskType}</p>
                </div>
                <div className="rounded-[24px] border border-[#e4dacb] bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-stone-500">进度</p>
                  <p className="mt-3 text-lg font-semibold text-[#241714]">{selectedTask.progress}%</p>
                </div>
                <div className="rounded-[24px] border border-[#e4dacb] bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-stone-500">最后更新</p>
                  <p className="mt-3 text-lg font-semibold text-[#241714]">{formatTime(selectedTask.updatedAt)}</p>
                </div>
              </div>

              <div className="rounded-[28px] border border-[#e4dacb] bg-white p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-stone-500">输入摘要</p>
                <div className="mt-4 space-y-3">
                  {inputSummary.length === 0 ? (
                    <p className="text-sm text-stone-500">暂无输入摘要</p>
                  ) : (
                    inputSummary.map((entry) => (
                      <div key={entry} className="rounded-[18px] bg-[#faf7f2] px-4 py-3 text-sm text-stone-600">
                        {entry}
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-[28px] border border-[#e4dacb] bg-white p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-stone-500">结果摘要</p>
                <div className="mt-4 space-y-3">
                  {outputSummary.length > 0 ? (
                    outputSummary.map((entry) => (
                      <div key={entry} className="rounded-[18px] bg-[#faf7f2] px-4 py-3 text-sm text-stone-600">
                        {entry}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-stone-500">任务推进后，这里会显示分析、试听或最终视频产物。</p>
                  )}
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  {continueLabel ? (
                    <Button onClick={() => router.push(`/smart-cut/${encodeURIComponent(selectedTask.id)}`)} type="button">
                      {continueLabel}
                    </Button>
                  ) : null}
                  {canDeleteTask ? (
                    <Button
                      className="text-red-600 ring-red-200 hover:bg-red-50"
                      disabled={deletingTaskId !== null}
                      onClick={handleDeleteTask}
                      type="button"
                      variant="secondary"
                    >
                      删除任务
                    </Button>
                  ) : null}
                  {activeTaskDetail?.final_video_url || selectedTask.downloadUrl ? (
                    <a className="inline-flex" href={activeTaskDetail?.final_video_url ?? selectedTask.downloadUrl ?? undefined} target="_blank">
                      <Button type="button" variant="secondary">
                        下载结果
                      </Button>
                    </a>
                  ) : null}
                </div>
              </div>
            </div>
          )}
        </Card>
      </section>
    </UserWorkspaceShell>
  );
}
