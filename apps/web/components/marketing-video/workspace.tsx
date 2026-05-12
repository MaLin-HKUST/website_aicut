"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthResponse } from "@/lib/auth";
import {
  createMarketingVideoWorkflow,
  isMarketingVideoMockMode,
  MarketingVideoWorkflowSummary,
  uploadMarketingVideoScript,
} from "@/lib/marketing-video";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type BusyState = "upload" | "create" | null;

const MARKETING_VIDEO_FULL_ACCESS_COMPANY_IDS = new Set([2, 10]);

function buildDefaultTitle(file: File | null) {
  if (!file) return "TONGAN 07 staging sample";
  return file.name.replace(/\.txt$/i, "") || "TONGAN 07 staging sample";
}

function hasMarketingVideoFullAccess(companyId: number | null | undefined) {
  return companyId !== null && companyId !== undefined && MARKETING_VIDEO_FULL_ACCESS_COMPANY_IDS.has(companyId);
}

export function MarketingVideoWorkspace() {
  const router = useRouter();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const workspace = useUserWorkspaceData(user?.username, user?.company_id);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<BusyState>(null);
  const [scriptFile, setScriptFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [title, setTitle] = useState("TONGAN 07 staging sample");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [createdWorkflow, setCreatedWorkflow] = useState<MarketingVideoWorkflowSummary | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mockMode = isMarketingVideoMockMode();
  const pageLocked = Boolean(user && !hasMarketingVideoFullAccess(user.company_id));

  const canCreate = Boolean(user && !pageLocked && scriptFile && busy === null);
  const selectedFileMeta = useMemo(() => {
    if (!scriptFile) return "尚未选择 TXT 文件";
    const sizeKb = Math.max(1, Math.round(scriptFile.size / 1024));
    return `${scriptFile.name} · ${sizeKb} KB`;
  }, [scriptFile]);

  useEffect(() => {
    async function bootstrap() {
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
      setLoading(false);
    }

    void bootstrap().catch((err) => {
      setError(err instanceof Error ? err.message : "初始化失败");
      setLoading(false);
    });
  }, [router]);

  async function logout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setError(null);
    setNotice(null);
    setScriptFile(file);
    setUploadProgress(0);
    if (file) setTitle(buildDefaultTitle(file));
  }

  function resetForm(options: { clearMessages?: boolean } = { clearMessages: true }) {
    setScriptFile(null);
    setTitle("TONGAN 07 staging sample");
    setUploadProgress(0);
    setFileInputKey((value) => value + 1);
    if (options.clearMessages !== false) {
      setNotice(null);
      setError(null);
    }
  }

  async function handleCreateTask() {
    if (!user || !scriptFile || pageLocked) return;
    setError(null);
    setNotice(null);
    try {
      setBusy("upload");
      const upload = await uploadMarketingVideoScript(scriptFile, { onProgress: setUploadProgress });
      setBusy("create");
      const workflow = await createMarketingVideoWorkflow({
        customer_id: "tongan",
        company_id: "tongan",
        task_type: "std_marketing_video",
        workflow_name: "TONGAN",
        mode: "standard",
        title: title.trim() || buildDefaultTitle(scriptFile),
        input_bundle: {
          script_txt: {
            upload_session_id: upload.upload_session_id,
            filename: upload.filename,
            tos_key: upload.tos_key,
          },
        },
      });
      const { subtasks: _subtasks, ...summary } = workflow;
      setCreatedWorkflow(summary);
      setNotice("任务已进入任务中心");
      resetForm({ clearMessages: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setBusy(null);
    }
  }

  return (
    <UserWorkspaceShell
      activeItem="marketing-video"
      currentUser={user?.username ?? "..."}
      headline={user?.company_name ? `你好，${user.company_name}，小马AI准备就绪~` : undefined}
      metrics={workspace.metrics}
      onLogout={logout}
      previewTasks={workspace.previewTasks}
    >
      <section className="relative rounded-[32px] border border-[#e5dacd] bg-[#f8f5ef] p-4 shadow-panel sm:p-6">
        {pageLocked ? (
          <div
            className="mb-5 rounded-[28px] border border-[#d7c6b0] bg-[#f0ece5] px-5 py-6 text-center shadow-sm"
            data-testid="marketing-video-development-lock"
          >
            <p className="text-[30px] font-semibold text-[#241714]">页面正在开发中</p>
            <p className="mt-2 text-sm text-stone-600">当前账号可以查看入口，完整操作暂未开放。</p>
          </div>
        ) : null}

        <div className={pageLocked ? "pointer-events-none select-none opacity-45 grayscale" : undefined} aria-disabled={pageLocked}>
          <Card className="rounded-[28px] border-[#e4dacb] bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <p className="text-xs tracking-[0.24em] text-stone-500">MARKETING VIDEO</p>
                <h2 className="mt-2 text-[26px] font-semibold text-[#241714]">生成营销视频</h2>
                <p className="mt-2 max-w-3xl text-sm leading-7 text-stone-600">
                  上传短视频的文案并创建 标准营销视频任务。创建后可以离开本页，后续进度、停止、改名和下载都在任务中心处理。
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[20px] border border-[#e4dacb] bg-[#fffaf5] px-4 py-3">
                  <p className="text-xs tracking-[0.2em] text-stone-500">当前模式</p>
                  <p className="mt-2 text-base font-semibold text-[#241714]">TONGAN 标准</p>
                </div>
                <div className="rounded-[20px] border border-[#e4dacb] bg-[#fffaf5] px-4 py-3">
                  <p className="text-xs tracking-[0.2em] text-stone-500">API</p>
                  <p className="mt-2 text-base font-semibold text-[#241714]">{mockMode ? "Mock" : "Real"}</p>
                </div>
              </div>
            </div>
          </Card>

          {notice ? <p className="mt-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</p> : null}
          {error ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

          <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_0.82fr]">
            <Card className="rounded-[28px] border-[#e4dacb] bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-[#241714]">任务输入</h3>
                  <p className="mt-2 text-sm leading-7 text-stone-500">输入短视频的文案(txt文件格式)</p>
                </div>
                <span className="self-start rounded-full border border-[#dfd5c5] bg-[#faf7f2] px-4 py-2 text-sm text-stone-600">
                  标准视频模式
                </span>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-[1fr_1fr]">
                <label className="flex min-h-[92px] cursor-pointer flex-col items-center justify-center rounded-[24px] border border-dashed border-[#dccab6] bg-[#fffaf5] px-4 py-4 text-center transition hover:bg-[#fff5e9]">
                  <span className="text-[17px] font-semibold text-[#302520]">选择 TXT 文案</span>
                  <span className="mt-2 max-w-full break-all text-sm text-stone-500">{selectedFileMeta}</span>
                  <Input
                    key={fileInputKey}
                    accept=".txt,text/plain"
                    className="hidden"
                    disabled={busy !== null || pageLocked}
                    onChange={handleFileChange}
                    type="file"
                  />
                </label>

                <div className="rounded-[24px] border border-[#e4dacb] bg-[#fffdf9] p-4">
                  <label className="text-xs tracking-[0.2em] text-stone-500" htmlFor="marketing-video-title">
                    任务标题
                  </label>
                  <Input
                    className="mt-3"
                    disabled={busy !== null || pageLocked}
                    id="marketing-video-title"
                    onChange={(event) => setTitle(event.target.value)}
                    value={title}
                  />
                </div>
              </div>

              <div className="mt-5 flex flex-wrap items-center gap-3">
                <Button disabled={!canCreate} onClick={handleCreateTask} type="button">
                  {busy === "upload"
                    ? `上传中 ${uploadProgress}%`
                    : busy === "create"
                      ? "创建中..."
                      : "创建营销视频任务"}
                </Button>
                <span className="text-sm text-stone-500">创建后任务会持久显示在任务中心</span>
              </div>
            </Card>

            <Card className="rounded-[28px] border-[#e4dacb] bg-white p-5 shadow-sm">
              <h3 className="text-lg font-semibold text-[#241714]">任务中心</h3>
              {createdWorkflow ? (
                <div className="mt-5 space-y-4">
                  <div className="rounded-[22px] border border-[#e4dacb] bg-[#fffaf5] p-4">
                    <p className="text-sm font-semibold text-[#241714]">{createdWorkflow.title}</p>
                    <p className="mt-2 break-all text-xs text-stone-500">{createdWorkflow.workflow_id}</p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button onClick={() => router.push(`/tasks?taskId=${encodeURIComponent(createdWorkflow.workflow_id)}`)} type="button">
                      查看任务详情
                    </Button>
                    <Button disabled={loading || busy !== null} onClick={() => resetForm()} type="button" variant="secondary">
                      继续创建
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="mt-4 text-sm leading-7 text-stone-500">
                  创建成功后会出现任务详情入口。刷新或离开页面不会影响后端工作流，任务状态会从任务中心重新读取。
                </p>
              )}
            </Card>
          </div>
        </div>
      </section>
    </UserWorkspaceShell>
  );
}
