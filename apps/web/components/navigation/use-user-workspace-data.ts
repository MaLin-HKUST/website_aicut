"use client";

import { useEffect, useMemo, useState } from "react";

import { listTaskCenterItems, TaskCenterItem } from "@/lib/task-center";
import { UserWorkspaceMetric, UserWorkspacePreviewTask } from "@/components/navigation/user-workspace-shell";

function prettifyTitle(item: TaskCenterItem): string {
  if (/\.[a-z0-9]{2,5}$/i.test(item.title)) {
    if (item.taskType === "tts") return "品牌口播任务";
    if (item.taskType === "smart_cut") return "视频剪辑任务";
    if (item.taskType === "std_marketing_video") return "营销视频任务";
    return "待处理任务";
  }
  return item.title;
}

function toPreviewTasks(items: TaskCenterItem[]): UserWorkspacePreviewTask[] {
  return items.slice(0, 3).map((item) => ({
    id: item.id,
    title: prettifyTitle(item),
    status: item.status,
  }));
}

export function useUserWorkspaceData(userId?: string, companyId?: number | null) {
  const [items, setItems] = useState<TaskCenterItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    if (!userId) {
      setItems([]);
      return;
    }

    async function bootstrap() {
      try {
        const nextItems = await listTaskCenterItems({ mode: "user", userId, companyId });
        if (!cancelled) {
          setItems(nextItems.filter((item) => item.companyId !== null && item.companyId === companyId));
        }
      } catch {
        if (!cancelled) {
          setItems([]);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [companyId, userId]);

  const metrics = useMemo<UserWorkspaceMetric[]>(
    () => [
      { label: "已剪辑条数", value: String(items.filter((item) => item.status === "finished").length) },
      { label: "剩余条数", value: "--" },
      { label: "当前执行任务", value: String(items.filter((item) => item.status === "running" || item.status === "waiting" || item.status === "queued").length) },
      { label: "当前账号", value: userId ?? "--" },
    ],
    [items, userId],
  );

  return {
    items,
    metrics,
    previewTasks: toPreviewTasks(items),
  };
}
