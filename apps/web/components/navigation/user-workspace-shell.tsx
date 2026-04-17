"use client";

import { ReactNode } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export type UserWorkspaceNavKey = "tts" | "smart-cut" | "tasks";

export type UserWorkspaceMetric = {
  label: string;
  value: string;
};

export type UserWorkspacePreviewTask = {
  id: string;
  title: string;
  status: string;
};

const PRIMARY_ITEMS: Array<{
  key: UserWorkspaceNavKey;
  label: string;
  href: string;
  icon: string;
}> = [
  { key: "tts", label: "文案生成语音", href: "/tts", icon: "M" },
  { key: "smart-cut", label: "智能气口剪辑", href: "/smart-cut", icon: "V" },
  { key: "tasks", label: "任务列表", href: "/tasks", icon: "T" },
];

const PLACEHOLDER_ITEMS = ["素材管理", "账户中心"];

function statusLabel(status: string) {
  if (status === "finished" || status === "success") return "已完成";
  if (status === "queued") return "排队中";
  if (status === "running" || status === "waiting" || status === "previewing" || status === "finalizing") return "执行中";
  if (status === "failed") return "失败";
  return status;
}

function statusDot(status: string) {
  if (status === "finished" || status === "success") return "bg-emerald-400";
  if (status === "queued") return "bg-blue-400";
  if (status === "failed") return "bg-rose-400";
  return "bg-amber-400";
}

export function UserWorkspaceShell({
  activeItem,
  currentUser,
  metrics,
  previewTasks,
  onLogout,
  headline,
  children,
}: {
  activeItem: UserWorkspaceNavKey;
  currentUser: string;
  metrics: UserWorkspaceMetric[];
  previewTasks: UserWorkspacePreviewTask[];
  onLogout?: () => void | Promise<void>;
  headline?: string;
  children: ReactNode;
}) {
  const router = useRouter();
  const headerText = headline ?? `你好，${currentUser}，小马AI准备就绪~`;

  return (
    <main className="min-h-screen bg-[#f4f1ea] p-4 lg:p-6">
      <div className="mx-auto flex max-w-[1500px] gap-4">
        <aside className="flex w-[260px] shrink-0 flex-col gap-4">
          <div className="px-2 pt-2">
            <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-stone-400">小马 AI 剪辑</p>
            <h2 className="mt-2 text-[22px] font-semibold text-[#241714]">你好，{currentUser}</h2>
          </div>

          <Card className="flex flex-col gap-1 rounded-[24px] border-[#e5dacd] bg-white p-3 shadow-sm">
            <p className="px-3 pb-1 text-[10px] font-medium uppercase tracking-[0.25em] text-stone-400">功能</p>
            {PRIMARY_ITEMS.map((item) => {
              const active = item.key === activeItem;
              return (
                <button
                  key={item.key}
                  className={[
                    "flex items-center gap-3 rounded-[16px] px-3 py-2.5 text-left text-sm font-medium transition",
                    active ? "bg-[#2b201d] text-white shadow-md" : "text-[#241714] hover:bg-[#f7efe2]",
                  ].join(" ")}
                  onClick={() => router.push(item.href)}
                  type="button"
                >
                  <span
                    className={[
                      "flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold",
                      active ? "bg-white/20 text-white" : "bg-[#f4f1ea] text-stone-600",
                    ].join(" ")}
                  >
                    {item.icon}
                  </span>
                  {item.label}
                </button>
              );
            })}

            {PLACEHOLDER_ITEMS.map((label) => (
              <div
                key={label}
                className="flex items-center justify-between rounded-[16px] px-3 py-2.5 text-sm text-stone-400"
              >
                <span>{label}</span>
                <span className="text-[10px] text-stone-300">即将开放</span>
              </div>
            ))}
          </Card>

          <Card className="flex-1 overflow-hidden rounded-[24px] border-[#e5dacd] bg-white p-3 shadow-sm">
            <p className="px-3 pb-2 text-[10px] font-medium uppercase tracking-[0.25em] text-stone-400">任务列表</p>
            <div className="space-y-2 overflow-y-auto">
              {previewTasks.length === 0 ? (
                <div className="rounded-[16px] border border-dashed border-[#eee2d1] bg-[#fffaf5] px-4 py-5 text-sm text-stone-400">
                  暂无任务
                </div>
              ) : (
                previewTasks.slice(0, 3).map((task) => (
                  <div
                    key={task.id}
                    className="cursor-pointer rounded-[16px] border border-[#f0e8dc] bg-[#fffaf5] p-3 transition hover:border-[#e5d7c5]"
                    onClick={() => router.push(`/tasks?taskId=${encodeURIComponent(task.id)}`)}
                    role="button"
                    tabIndex={0}
                  >
                    <p className="text-sm font-semibold text-[#241714]">{task.title}</p>
                    <div className="mt-1 flex items-center gap-2 text-xs text-stone-500">
                      <span className={`h-2 w-2 rounded-full ${statusDot(task.status)}`} />
                      {statusLabel(task.status)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Button
            className="h-11 w-full rounded-[16px] bg-[#2b201d] text-white hover:bg-[#3d2f29]"
            onClick={() => void onLogout?.()}
            type="button"
          >
            退出登录
          </Button>
        </aside>

        <div className="flex-1 space-y-4">
          <section className="rounded-[32px] border border-[#e5dacd] bg-white p-6 shadow-panel">
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_repeat(4,108px)] xl:items-center">
              <div>
                <h1 className="text-4xl font-semibold leading-tight text-[#241714]">{headerText}</h1>
              </div>
              {metrics.map((metric) => (
                <div
                  key={metric.label}
                  className="rounded-[18px] border border-[#d9d0c1] bg-[#f8f5ef] px-4 py-3 text-center"
                >
                  <p className="text-[10px] uppercase tracking-[0.18em] text-stone-500">{metric.label}</p>
                  <p className="mt-2 text-2xl font-semibold text-[#241714]">{metric.value}</p>
                </div>
              ))}
            </div>
          </section>

          {children}
        </div>
      </div>
    </main>
  );
}
