"use client";

import { ReactNode } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export type UserWorkspaceNavKey = "tts" | "smart-cut" | "marketing-video" | "tasks";

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
  disabled?: boolean;
}> = [
  { key: "tts", label: "文案生成语音", href: "/tts", icon: "M" },
  { key: "smart-cut", label: "智能剪气口", href: "/smart-cut", icon: "V" },
  { key: "marketing-video", label: "生成营销视频", href: "/marketing-video", icon: "G" },
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
    <main className="min-h-screen bg-[#f1f2f0] p-4 lg:p-5">
      <div className="mx-auto flex max-w-[1480px] flex-col gap-4 lg:flex-row">
        <aside className="flex w-full shrink-0 flex-col gap-4 pt-1 lg:w-[276px]">
          <div className="px-3">
            <p className="text-[10px] font-medium tracking-[0.28em] text-stone-400">小马 AI 剪辑</p>
          </div>

          <Card className="flex flex-col gap-1 rounded-[26px] border-[#e1e2df] bg-[#eef1f5] p-4 shadow-[0_6px_18px_rgba(60,66,74,0.04)]">
            <p className="px-2 pb-2 text-[11px] tracking-[0.25em] text-stone-400">功能</p>
            {PRIMARY_ITEMS.map((item) => {
              const active = item.key === activeItem;
              return (
                <button
                  key={item.key}
                  className={[
                    "flex items-center gap-3 rounded-[18px] px-4 py-3 text-left text-[15px] font-medium transition",
                    item.disabled
                      ? "cursor-not-allowed bg-white text-stone-400"
                      : active
                        ? "bg-[#243444] text-white shadow-[0_8px_18px_rgba(36,52,68,0.12)]"
                        : "bg-white text-[#241714] hover:bg-[#faf7f2]",
                  ].join(" ")}
                  disabled={item.disabled}
                  onClick={() => {
                    if (item.disabled) return;
                    router.push(item.href);
                  }}
                  type="button"
                >
                  <span
                    className={[
                      "flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold",
                      item.disabled ? "bg-[#f2efe9] text-stone-300" : active ? "bg-white/18 text-white" : "bg-[#f2efe9] text-stone-500",
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
                className="flex items-center justify-between rounded-[18px] bg-white px-4 py-3 text-[15px] text-stone-400"
              >
                <span>{label}</span>
                <span className="text-[11px] text-stone-300">即将开放</span>
              </div>
            ))}
          </Card>

          <Card className="flex-1 overflow-hidden rounded-[26px] border-[#e1e2df] bg-[#eef1f5] p-4 shadow-[0_6px_18px_rgba(60,66,74,0.04)]">
            <p className="px-2 pb-2 text-[11px] tracking-[0.25em] text-stone-400">任务列表</p>
            <div className="space-y-2 overflow-y-auto">
              {previewTasks.length === 0 ? (
                <div className="rounded-[18px] border border-dashed border-[#e4ddd3] bg-white px-4 py-5 text-sm text-stone-400">
                  暂无任务
                </div>
              ) : (
                previewTasks.slice(0, 3).map((task) => (
                  <div
                    key={task.id}
                    className="cursor-pointer rounded-[18px] border border-[#e5ddd2] bg-white px-4 py-4 transition hover:border-[#d4cabd]"
                    onClick={() => router.push(`/tasks?taskId=${encodeURIComponent(task.id)}`)}
                    role="button"
                    tabIndex={0}
                  >
                    <p className="text-[15px] font-semibold text-[#241714]">{task.title}</p>
                    <div className="mt-2 flex items-center gap-2 text-[12px] text-stone-500">
                      <span className={`h-2 w-2 rounded-full ${statusDot(task.status)}`} />
                      {statusLabel(task.status)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Button
            className="h-11 w-full rounded-[18px] bg-[#2f3945] text-white hover:bg-[#39444f]"
            onClick={() => void onLogout?.()}
            type="button"
          >
            退出登录
          </Button>
        </aside>

        <div className="min-w-0 flex-1 space-y-4">
          <section className="rounded-[30px] border border-[#e3e3df] bg-[#fffefb] px-7 py-5 shadow-[0_8px_22px_rgba(60,66,74,0.04)]">
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_repeat(4,minmax(92px,112px))] xl:items-center">
              <div>
                <h1 className="text-[30px] font-semibold leading-tight text-[#241714]">{headerText}</h1>
              </div>
              {metrics.map((metric) => (
                <div
                  key={metric.label}
                  className="rounded-[18px] border border-[#ddddd7] bg-[#fafafa] px-2.5 py-2.5 text-center"
                >
                  <p className="text-[10px] tracking-[0.14em] text-stone-500">{metric.label}</p>
                  <p className="mt-1.5 break-all text-[15px] font-semibold text-[#241714]">{metric.value}</p>
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
