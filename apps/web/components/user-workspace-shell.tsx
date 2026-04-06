"use client";

import { ReactNode } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type NavItem = {
  label: string;
  href?: string;
  active?: boolean;
  badge?: string;
};

type TaskItem = {
  name: string;
  status: string;
};

type UserWorkspaceShellProps = {
  companyName: string | null;
  activeItem: string;
  children: ReactNode;
  onLogout: () => void | Promise<void>;
};

const primaryItems: NavItem[] = [
  { label: "文案生成语音", href: "/tts" },
  { label: "视频剪辑", badge: "即将开放" },
  { label: "素材管理", badge: "即将开放" },
  { label: "任务列表", badge: "即将开放" },
  { label: "账户中心", badge: "即将开放" },
];

const taskItems: TaskItem[] = [
  { name: "品牌口播任务", status: "执行中" },
  { name: "产品说明任务", status: "排队中" },
  { name: "示例音频任务", status: "已完成" },
];

export function UserWorkspaceShell({
  companyName,
  activeItem,
  children,
  onLogout,
}: UserWorkspaceShellProps) {
  const router = useRouter();
  
  const headline = `你好，${companyName ?? "..."}，小马AI准备就绪~`;

  return (
    <main className="min-h-screen bg-[#ecf1f6] p-4 text-[#16202a] lg:p-6">
      <div className="mx-auto max-w-[1500px] space-y-4">
        <section className="rounded-[30px] border border-[#cad4de] bg-white p-5 shadow-panel lg:p-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <h1
                className="text-2xl font-semibold text-[#15202a] lg:text-3xl"
                style={{ fontFamily: "\"Trebuchet MS\", \"Segoe UI\", sans-serif" }}
              >
                {headline}
              </h1>
            </div>

            <div className="flex gap-3">
              <MetricCard label="已剪辑条数" value="0" />
              <MetricCard label="剩余条数" value="--" />
              <MetricCard label="当前执行任务" value="0" />
              <MetricCard label="当前账号" value={companyName ?? "..."} />
            </div>
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[250px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <Card className="rounded-[28px] border-[#cad4de] bg-[#dfe8f0] p-4">
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">功能</p>
              <div className="mt-4 space-y-2">
                {primaryItems.map((item) => {
                  const isActive = item.label === activeItem;
                  const isClickable = Boolean(item.href);
                  return (
                    <button
                      key={item.label}
                      className={cn(
                        "flex w-full items-center justify-between rounded-[18px] px-4 py-3 text-left text-sm transition",
                        isActive ? "bg-[#18364e] text-white" : "bg-white text-[#16202a]",
                        isClickable ? "hover:bg-[#18364e] hover:text-white" : "cursor-default",
                      )}
                      onClick={() => {
                        if (item.href) {
                          router.push(item.href);
                        }
                      }}
                      type="button"
                    >
                      <span>{item.label}</span>
                      {item.badge ? (
                        <span className={cn("text-[11px]", isActive ? "text-slate-200" : "text-slate-400")}>{item.badge}</span>
                      ) : null}
                    </button>
                  );
                })}
              </div>
            </Card>

            <Card className="rounded-[28px] border-[#cad4de] bg-[#dfe8f0] p-4">
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">任务列表</p>
              <div className="mt-4 space-y-2">
                {taskItems.map((task) => (
                  <div key={task.name} className="rounded-[18px] bg-white px-4 py-3 text-sm">
                    <p className="font-medium text-[#17202a]">{task.name}</p>
                    <p className="mt-1 text-xs text-slate-500">{task.status}</p>
                  </div>
                ))}
              </div>
            </Card>

            <Button className="h-11 w-full bg-[#18364e] hover:bg-[#102739]" onClick={onLogout}>
              退出登录
            </Button>
          </aside>

          <section>
            <div className="grid gap-4">
              {children}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-[#cdd6de] bg-[#f3f6fa] px-3 py-2">
      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[#16202a]">{value}</p>
    </div>
  );
}
