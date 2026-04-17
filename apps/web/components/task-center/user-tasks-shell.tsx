"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Card } from "@/components/ui/card";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { listTaskCenterItems, TaskCenterItem } from "@/lib/task-center";

type AuthResponse = {
  user: {
    username: string;
    role: "admin" | "user";
  };
};

const FILTERS = [
  { key: "all", label: "全部" },
  { key: "running", label: "执行中" },
  { key: "waiting", label: "等待中" },
  { key: "finished", label: "已完成" },
  { key: "failed", label: "失败" },
] as const;

type FilterKey = (typeof FILTERS)[number]["key"];

function statusLabel(status: TaskCenterItem["status"]) {
  if (status === "queued") return "排队中";
  if (status === "running") return "执行中";
  if (status === "waiting") return "等待中";
  if (status === "finished") return "已完成";
  return "失败";
}

function statusTone(status: TaskCenterItem["status"]) {
  if (status === "finished") return "bg-emerald-100 text-emerald-700";
  if (status === "queued") return "bg-blue-100 text-blue-700";
  if (status === "failed") return "bg-rose-100 text-rose-700";
  return "bg-amber-100 text-amber-700";
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

export function UserTasksShell() {
  const searchParams = useSearchParams();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const [items, setItems] = useState<TaskCenterItem[]>([]);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const workspace = useUserWorkspaceData(user?.username);

  useEffect(() => {
    async function bootstrap() {
      const response = await fetch("/api/proxy/auth/me");
      if (!response.ok) {
        window.location.href = "/login";
        return;
      }

      const payload = (await response.json()) as AuthResponse;
      if (payload.user.role === "admin") {
        window.location.href = "/admin/tasks";
        return;
      }

      setUser(payload.user);

      try {
        const nextItems = await listTaskCenterItems({ mode: "user", userId: payload.user.username });
        setItems(nextItems);
        const requestedId = searchParams.get("taskId");
        setSelectedId(requestedId || nextItems[0]?.id || "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "读取任务失败");
      }
    }

    void bootstrap();
  }, [searchParams]);

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  const filteredItems = useMemo(
    () => items.filter((item) => filter === "all" || item.status === filter),
    [filter, items],
  );

  const selectedTask = filteredItems.find((item) => item.id === selectedId) ?? filteredItems[0] ?? null;

  return (
    <UserWorkspaceShell
      activeItem="tasks"
      currentUser={user?.username ?? "..."}
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
                <h3 className="mt-3 text-4xl font-semibold text-[#241714]">{selectedTask.title}</h3>
                <div className="mt-4 flex flex-wrap gap-3">
                  <span className={`rounded-full px-4 py-2 text-sm font-semibold ${statusTone(selectedTask.status)}`}>
                    {statusLabel(selectedTask.status)}
                  </span>
                  <span className="rounded-full border border-[#dfd5c5] bg-[#faf7f2] px-4 py-2 text-sm text-stone-600">
                    {selectedTask.currentStage}
                  </span>
                </div>
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
                  {selectedTask.inputSummary.length === 0 ? (
                    <p className="text-sm text-stone-500">暂无输入摘要</p>
                  ) : (
                    selectedTask.inputSummary.map((entry) => (
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
                  {selectedTask.outputSummary && selectedTask.outputSummary.length > 0 ? (
                    selectedTask.outputSummary.map((entry) => (
                      <div key={entry} className="rounded-[18px] bg-[#faf7f2] px-4 py-3 text-sm text-stone-600">
                        {entry}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-stone-500">任务完成后，这里会显示输出文件和下载信息。</p>
                  )}
                  {selectedTask.downloadUrl ? (
                    <a
                      className="inline-flex rounded-full bg-[#2b201d] px-5 py-3 text-sm font-semibold text-white"
                      href={selectedTask.downloadUrl}
                      target="_blank"
                    >
                      下载结果
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
