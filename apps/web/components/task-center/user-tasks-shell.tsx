"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { AuthResponse } from "@/lib/auth";
import {
  archiveMarketingVideoWorkflow,
  cancelMarketingVideoWorkflow,
  getMarketingVideoDownload,
  getMarketingVideoNodeLabel,
  getMarketingVideoWorkflow,
  listMarketingVideoWorkflows,
  MarketingVideoWorkflow,
  MarketingVideoWorkflowStatus,
  MarketingVideoWorkflowSummary,
  updateMarketingVideoWorkflowTitle,
} from "@/lib/marketing-video";
import {
  abandonTask,
  getSmartCutContinueLabel,
  getSmartCutTask,
  isSmartCutDeletable,
  listSmartCutTasks,
  SmartCutTask,
  SmartCutTaskSummary,
} from "@/lib/smart-cut";
import { getTaskTypeLabel, listTaskCenterItems, TaskCenterItem } from "@/lib/task-center";

const FILTERS = [
  { key: "all", label: "全部" },
  { key: "running", label: "执行中" },
  { key: "waiting", label: "等待中" },
  { key: "finished", label: "已完成" },
  { key: "failed", label: "失败" },
  { key: "cancelled", label: "已停止" },
] as const;

type FilterKey = (typeof FILTERS)[number]["key"];
type QueueStatus = TaskCenterItem["status"];

type UserTaskListItem = {
  id: string;
  title: string;
  taskType: TaskCenterItem["taskType"];
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
  if (status === "cancelled") return "已停止";
  return "失败";
}

function statusTone(status: QueueStatus) {
  if (status === "finished") return "bg-emerald-100 text-emerald-700";
  if (status === "queued") return "bg-blue-100 text-blue-700";
  if (status === "failed") return "bg-rose-100 text-rose-700";
  if (status === "cancelled") return "bg-stone-100 text-stone-600";
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
    taskType: item.taskType,
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

function marketingStatusToQueueStatus(status: MarketingVideoWorkflowStatus): QueueStatus {
  if (status === "succeeded") return "finished";
  if (status === "failed") return "failed";
  if (status === "cancelled") return "cancelled";
  if (status === "waiting_user" || status === "manual_required") return "waiting";
  if (status === "queued") return "queued";
  return "running";
}

function buildMarketingVideoQueueItem(workflow: MarketingVideoWorkflowSummary | MarketingVideoWorkflow): UserTaskListItem {
  const downloadUrl = workflow.download.available ? workflow.download.final_video_url : null;
  return {
    id: workflow.workflow_id,
    title: workflow.title || `TONGAN ${workflow.workflow_id.slice(3, 11)}`,
    taskType: "std_marketing_video",
    status: marketingStatusToQueueStatus(workflow.status),
    rawStatus: workflow.status,
    progress: workflow.progress_percent,
    currentStage: workflow.current_node_label || statusLabel(marketingStatusToQueueStatus(workflow.status)),
    updatedAt: workflow.updated_at,
    createdAt: workflow.created_at,
    downloadUrl,
    errorMessage: workflow.error_message,
    inputSummary: ["TXT 文案", workflow.workflow_id],
    outputSummary: downloadUrl ? ["final video ready"] : [],
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
  const [selectedMarketingVideoDetail, setSelectedMarketingVideoDetail] = useState<MarketingVideoWorkflow | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailNotice, setDetailNotice] = useState<string | null>(null);
  const [deletingTaskId, setDeletingTaskId] = useState<string | null>(null);
  const [marketingAction, setMarketingAction] = useState<"rename" | "cancel" | "archive" | "download" | null>(null);
  const [marketingTitleDraft, setMarketingTitleDraft] = useState("");
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
        const [sharedItems, ownTasks, marketingWorkflows] = await Promise.all([
          listTaskCenterItems({
            mode: "user",
            userId: payload.user.username,
            companyId: payload.user.company_id,
          }),
          listSmartCutTasks({
            userId: payload.user.username,
            limit: 50,
          }),
          listMarketingVideoWorkflows(),
        ]);

        const merged = new Map<string, UserTaskListItem>();
        for (const item of sharedItems) {
          merged.set(item.id, buildSharedQueueItem(item));
        }
        for (const item of ownTasks.filter((task) => task.status !== "abandoned")) {
          merged.set(item.id, buildSelfQueueItem(item, merged.get(item.id)));
        }
        for (const workflow of marketingWorkflows) {
          merged.set(workflow.workflow_id, buildMarketingVideoQueueItem(workflow));
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
      setSelectedMarketingVideoDetail(null);
      setDetailError(null);
      setDetailNotice(null);
      return;
    }

    const selectedSummary = items.find((item) => item.id === selectedId);
    if (selectedSummary?.taskType === "std_marketing_video") {
      setSelectedTaskDetail(null);
      let cancelled = false;

      async function loadMarketingVideoDetail() {
        try {
          setDetailError(null);
          setDetailNotice(null);
          const workflow = await getMarketingVideoWorkflow(selectedId);
          if (cancelled) return;
          setSelectedMarketingVideoDetail(workflow);
          setMarketingTitleDraft(workflow.title);
          setItems((current) => {
            const nextItem = buildMarketingVideoQueueItem(workflow);
            const rest = current.filter((item) => item.id !== workflow.workflow_id);
            return [nextItem, ...rest].sort(
              (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
            );
          });
        } catch (err) {
          if (cancelled) return;
          setSelectedMarketingVideoDetail(null);
          setDetailError(err instanceof Error ? err.message : "读取营销视频任务详情失败");
        }
      }

      void loadMarketingVideoDetail();

      return () => {
        cancelled = true;
      };
    }

    if (selectedSummary && selectedSummary.taskType !== "smart_cut") {
      setSelectedTaskDetail(null);
      setSelectedMarketingVideoDetail(null);
      setDetailError(null);
      setDetailNotice(null);
      return;
    }

    let cancelled = false;

    async function loadDetail() {
      try {
        setDetailError(null);
        setDetailNotice(null);
        setSelectedTaskDetail(null);
        setSelectedMarketingVideoDetail(null);
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

  useEffect(() => {
    if (!selectedMarketingVideoDetail) return;
    if (!["queued", "running", "waiting_user", "manual_required"].includes(selectedMarketingVideoDetail.status)) return;

    const timer = window.setInterval(() => {
      void getMarketingVideoWorkflow(selectedMarketingVideoDetail.workflow_id)
        .then((workflow) => {
          setSelectedMarketingVideoDetail(workflow);
          setItems((current) => {
            const nextItem = buildMarketingVideoQueueItem(workflow);
            const rest = current.filter((item) => item.id !== workflow.workflow_id);
            return [nextItem, ...rest].sort(
              (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
            );
          });
        })
        .catch((err) => setDetailError(err instanceof Error ? err.message : "刷新营销视频任务失败"));
    }, 3000);

    return () => window.clearInterval(timer);
  }, [selectedMarketingVideoDetail]);

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
  const activeMarketingVideoDetail =
    selectedMarketingVideoDetail && selectedMarketingVideoDetail.workflow_id === selectedTask?.id ? selectedMarketingVideoDetail : null;
  const continueLabel =
    selectedTask?.taskType === "smart_cut"
      ? getSmartCutContinueLabel(activeTaskDetail?.status ?? selectedTask?.rawStatus)
      : null;
  const detailTitle =
    activeMarketingVideoDetail?.title ||
    activeTaskDetail?.task_title ||
    selectedTask?.title ||
    (activeTaskDetail ? `智能剪气口-${activeTaskDetail.id.slice(0, 8)}` : "");
  const inputSummary = activeMarketingVideoDetail
    ? ["TXT 文案", activeMarketingVideoDetail.workflow_id]
    : activeTaskDetail
    ? buildDetailInputSummary(activeTaskDetail, selectedTask?.inputSummary ?? [])
    : selectedTask?.inputSummary ?? [];
  const outputSummary = activeMarketingVideoDetail
    ? activeMarketingVideoDetail.download.available
      ? ["成片已生成"]
      : []
    : activeTaskDetail
    ? buildDetailOutputSummary(activeTaskDetail, selectedTask?.outputSummary ?? [])
    : selectedTask?.outputSummary ?? [];
  const detailStatusText =
    activeMarketingVideoDetail
      ? statusLabel(marketingStatusToQueueStatus(activeMarketingVideoDetail.status))
      : selectedTask?.taskType === "smart_cut"
      ? smartCutStatusLabel(activeTaskDetail?.status ?? selectedTask?.rawStatus)
      : selectedTask
        ? statusLabel(selectedTask.status)
        : "待同步";
  const detailStageText = activeMarketingVideoDetail
    ? activeMarketingVideoDetail.current_node_label || "等待推进"
    : activeTaskDetail
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
  const canCancelMarketingVideo = Boolean(
    activeMarketingVideoDetail && ["queued", "running"].includes(activeMarketingVideoDetail.status) && marketingAction === null,
  );
  const canArchiveMarketingVideo = Boolean(
    activeMarketingVideoDetail && ["cancelled", "failed"].includes(activeMarketingVideoDetail.status) && marketingAction === null,
  );

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

  function handleSelectTask(taskId: string) {
    setSelectedId(taskId);
    router.replace(`/tasks?taskId=${encodeURIComponent(taskId)}`, { scroll: false });
  }

  async function refreshMarketingVideoDetail(workflowId: string) {
    const workflow = await getMarketingVideoWorkflow(workflowId);
    setSelectedMarketingVideoDetail(workflow);
    setMarketingTitleDraft(workflow.title);
    setItems((current) => {
      const nextItem = buildMarketingVideoQueueItem(workflow);
      const rest = current.filter((item) => item.id !== workflow.workflow_id);
      return [nextItem, ...rest].sort(
        (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
      );
    });
    return workflow;
  }

  async function handleRenameMarketingVideo() {
    if (!activeMarketingVideoDetail) return;
    setMarketingAction("rename");
    setDetailError(null);
    setDetailNotice(null);
    try {
      const workflow = await updateMarketingVideoWorkflowTitle(activeMarketingVideoDetail.workflow_id, marketingTitleDraft);
      setSelectedMarketingVideoDetail(workflow);
      setItems((current) => {
        const nextItem = buildMarketingVideoQueueItem(workflow);
        const rest = current.filter((item) => item.id !== workflow.workflow_id);
        return [nextItem, ...rest].sort(
          (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
        );
      });
      setDetailNotice("任务名称已更新。");
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "修改任务名称失败");
    } finally {
      setMarketingAction(null);
    }
  }

  async function handleCancelMarketingVideo() {
    if (!activeMarketingVideoDetail) return;
    setMarketingAction("cancel");
    setDetailError(null);
    setDetailNotice(null);
    try {
      const workflow = await cancelMarketingVideoWorkflow(activeMarketingVideoDetail.workflow_id);
      setSelectedMarketingVideoDetail(workflow);
      setItems((current) => {
        const nextItem = buildMarketingVideoQueueItem(workflow);
        const rest = current.filter((item) => item.id !== workflow.workflow_id);
        return [nextItem, ...rest].sort(
          (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
        );
      });
      setDetailNotice("任务已停止。");
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "停止任务失败");
    } finally {
      setMarketingAction(null);
    }
  }

  async function handleArchiveMarketingVideo() {
    if (!activeMarketingVideoDetail) return;
    const archivedId = activeMarketingVideoDetail.workflow_id;
    setMarketingAction("archive");
    setDetailError(null);
    setDetailNotice(null);
    try {
      await archiveMarketingVideoWorkflow(archivedId);
      let nextSelectedId = "";
      setItems((current) => {
        const remaining = current.filter((item) => item.id !== archivedId);
        nextSelectedId = remaining[0]?.id ?? "";
        return remaining;
      });
      setSelectedMarketingVideoDetail(null);
      setSelectedId(nextSelectedId);
      if (nextSelectedId) router.replace(`/tasks?taskId=${encodeURIComponent(nextSelectedId)}`, { scroll: false });
      setDetailNotice("任务已从列表归档。");
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "归档任务失败");
    } finally {
      setMarketingAction(null);
    }
  }

  async function handleMarketingVideoDownload() {
    if (!activeMarketingVideoDetail) return;
    setMarketingAction("download");
    setDetailError(null);
    try {
      const url = await getMarketingVideoDownload(activeMarketingVideoDetail.workflow_id);
      await refreshMarketingVideoDetail(activeMarketingVideoDetail.workflow_id);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "下载链接暂不可用");
    } finally {
      setMarketingAction(null);
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
                  onClick={() => handleSelectTask(item.id)}
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
                <h3 className="mt-3 text-4xl font-semibold text-[#241714]">{detailTitle}</h3>
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
                ) : activeMarketingVideoDetail?.error_message ? (
                  <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{activeMarketingVideoDetail.error_message}</p>
                ) : selectedTask.errorMessage ? (
                  <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{selectedTask.errorMessage}</p>
                ) : null}
                {activeMarketingVideoDetail ? (
                  <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                    <Input
                      aria-label="营销视频任务名称"
                      disabled={marketingAction !== null}
                      onChange={(event) => setMarketingTitleDraft(event.target.value)}
                      value={marketingTitleDraft}
                    />
                    <Button
                      disabled={marketingAction !== null || marketingTitleDraft.trim().length === 0}
                      onClick={handleRenameMarketingVideo}
                      type="button"
                      variant="secondary"
                    >
                      {marketingAction === "rename" ? "保存中..." : "保存名称"}
                    </Button>
                  </div>
                ) : null}
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <div className="rounded-[24px] border border-[#e4dacb] bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-stone-500">任务类型</p>
                  <p className="mt-3 text-lg font-semibold text-[#241714]">{getTaskTypeLabel(selectedTask.taskType)}</p>
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

              {activeMarketingVideoDetail ? (
                <div className="rounded-[28px] border border-[#e4dacb] bg-white p-5">
                    <p className="text-xs uppercase tracking-[0.24em] text-stone-500">节点状态</p>
                    <div className="mt-4 space-y-3">
                      {activeMarketingVideoDetail.subtasks.map((subtask) => (
                        <div key={subtask.subtask_id} className="rounded-[18px] bg-[#faf7f2] px-4 py-3 text-sm text-stone-600">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                            <span className="font-semibold text-[#241714]">
                              {getMarketingVideoNodeLabel(subtask.node_code, subtask.node_name)}
                            </span>
                            <span>
                              {subtask.status} · attempt {subtask.attempt}
                            </span>
                          </div>
                          {subtask.error_message ? <p className="mt-2 text-red-700">{subtask.error_message}</p> : null}
                        </div>
                      ))}
                    </div>
                </div>
              ) : null}

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
                  {activeMarketingVideoDetail && canCancelMarketingVideo ? (
                    <Button onClick={handleCancelMarketingVideo} type="button" variant="secondary">
                      {marketingAction === "cancel" ? "停止中..." : "停止任务"}
                    </Button>
                  ) : null}
                  {activeMarketingVideoDetail && canArchiveMarketingVideo ? (
                    <Button
                      className="text-red-600 ring-red-200 hover:bg-red-50"
                      onClick={handleArchiveMarketingVideo}
                      type="button"
                      variant="secondary"
                    >
                      {marketingAction === "archive" ? "归档中..." : "删除任务"}
                    </Button>
                  ) : null}
                  {activeMarketingVideoDetail?.download.available ? (
                    <Button onClick={handleMarketingVideoDownload} type="button" variant="secondary">
                      {marketingAction === "download" ? "打开中..." : "下载成片"}
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
