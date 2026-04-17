"use client";

import { useEffect, useMemo, useState } from "react";

import { listTaskCenterItems, TaskCenterItem } from "@/lib/task-center";
import { UserWorkspaceMetric, UserWorkspacePreviewTask } from "@/components/navigation/user-workspace-shell";

function toPreviewTasks(items: TaskCenterItem[]): UserWorkspacePreviewTask[] {
  return items.slice(0, 3).map((item) => ({
    id: item.id,
    title: item.title,
    status: item.status,
  }));
}

export function useUserWorkspaceData(userId?: string) {
  const [items, setItems] = useState<TaskCenterItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    if (!userId) {
      setItems([]);
      return;
    }

    async function bootstrap() {
      try {
        const nextItems = await listTaskCenterItems({ mode: "user", userId });
        if (!cancelled) {
          setItems(nextItems);
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
  }, [userId]);

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
