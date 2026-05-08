"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthResponse } from "@/lib/auth";
import {
  buildMarketingVideoMockWorkflow,
  cancelMarketingVideoWorkflow,
  createMarketingVideoWorkflow,
  getMarketingVideoDownload,
  getMarketingVideoWorkflow,
  isMarketingVideoMockMode,
  MarketingVideoWorkflow,
  MarketingVideoWorkflowStatus,
  uploadMarketingVideoScript,
} from "@/lib/marketing-video";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type BusyState = "upload" | "create" | "cancel" | null;

const STATUS_LABELS: Record<MarketingVideoWorkflowStatus, string> = {
  queued: "排队中",
  running: "生成中",
  waiting_user: "等待处理",
  succeeded: "已完成",
  failed: "失败",
  cancelled: "已取消",
  manual_required: "需人工处理",
};

const SUBTASK_STATUS_LABELS: Record<string, string> = {
  queued: "排队中",
  ready: "待执行",
  dispatching: "调度中",
  accepted: "已接收",
  running: "执行中",
  succeeded: "已完成",
  failed: "失败",
  cancelled: "已取消",
  manual_required: "需人工处理",
};

function statusTone(status: MarketingVideoWorkflowStatus) {
  if (status === "succeeded") return "bg-emerald-100 text-emerald-700";
  if (status === "failed" || status === "manual_required") return "bg-rose-100 text-rose-700";
  if (status === "cancelled") return "bg-stone-100 text-stone-600";
  if (status === "queued") return "bg-blue-100 text-blue-700";
  return "bg-amber-100 text-amber-700";
}

function subtaskTone(status: string) {
  if (status === "succeeded") return "bg-emerald-100 text-emerald-700";
  if (status === "failed" || status === "manual_required") return "bg-rose-100 text-rose-700";
  if (status === "queued") return "bg-stone-100 text-stone-500";
  return "bg-amber-100 text-amber-700";
}

function formatTime(value?: string | null) {
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

function buildDefaultTitle(file: File | null) {
  if (!file) return "TONGAN 07 staging sample";
  return file.name.replace(/\.txt$/i, "") || "TONGAN 07 staging sample";
}

export function MarketingVideoWorkspace() {
  const router = useRouter();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const workspace = useUserWorkspaceData(user?.username, user?.company_id);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<BusyState>(null);
  const [scriptFile, setScriptFile] = useState<File | null>(null);
  const [title, setTitle] = useState("TONGAN 07 staging sample");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [workflow, setWorkflow] = useState<MarketingVideoWorkflow | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mockMode = isMarketingVideoMockMode();

  const canCreate = Boolean(user && scriptFile && busy === null);
  const workflowDone = workflow && ["succeeded", "failed", "cancelled", "manual_required"].includes(workflow.status);

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

  useEffect(() => {
    if (!workflow || workflowDone) return;
    const timer = window.setInterval(() => {
      void getMarketingVideoWorkflow(workflow.workflow_id)
        .then((nextWorkflow) => {
          setWorkflow(nextWorkflow);
          if (nextWorkflow.download.available) {
            setDownloadUrl(nextWorkflow.download.final_video_url);
          }
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : "刷新任务状态失败");
        });
    }, 2500);
    return () => window.clearInterval(timer);
  }, [workflow, workflowDone]);

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

  async function handleCreateTask() {
    if (!user || !scriptFile) return;
    setBusy("create");
    setError(null);
    setNotice(null);
    setDownloadUrl(null);
    try {
      setBusy("upload");
      const upload = await uploadMarketingVideoScript(scriptFile, { onProgress: setUploadProgress });
      setBusy("create");
      const nextWorkflow = await createMarketingVideoWorkflow({
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
      setWorkflow(nextWorkflow);
      setNotice(mockMode ? "Mock 任务已创建，页面会自动推进状态。" : "任务已创建，页面会自动刷新状态。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleCancel() {
    if (!workflow) return;
    setBusy("cancel");
    setError(null);
    setNotice(null);
    try {
      const nextWorkflow = await cancelMarketingVideoWorkflow(workflow.workflow_id);
      setWorkflow(nextWorkflow);
      setNotice("当前任务已取消。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "取消任务失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleDownload() {
    if (!workflow) return;
    setError(null);
    try {
      const url = await getMarketingVideoDownload(workflow.workflow_id);
      setDownloadUrl(url);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "下载链接暂不可用");
    }
  }

  function showMockExample(outcome: "succeeded" | "failed") {
    const nextWorkflow = buildMarketingVideoMockWorkflow(outcome);
    setWorkflow(nextWorkflow);
    setDownloadUrl(nextWorkflow.download.final_video_url);
    setNotice(outcome === "succeeded" ? "已切换到成功示例。" : "已切换到失败示例。");
    setError(null);
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
      <section className="rounded-[32px] border border-[#e5dacd] bg-[#f8f5ef] p-4 shadow-panel sm:p-6">
        <Card className="rounded-[28px] border-[#e4dacb] bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <p className="text-xs tracking-[0.24em] text-stone-500">MARKETING VIDEO</p>
              <h2 className="mt-2 text-[26px] font-semibold text-[#241714]">生成营销视频</h2>
              <p className="mt-2 max-w-3xl text-sm leading-7 text-stone-600">
                当前开放 TONGAN 标准营销视频。上传一个 TXT 文案后创建任务，页面展示主任务状态、节点进度和最终下载入口。
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

        <div className="mt-5 grid gap-5 xl:grid-cols-[1.03fr_0.97fr]">
          <div className="space-y-5">
            <Card className="rounded-[28px] border-[#e4dacb] bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-[#241714]">任务输入</h3>
                  <p className="mt-2 text-sm leading-7 text-stone-500">只支持一个 TXT 文案文件。RBZJ/KDT IP 模式暂未开放。</p>
                </div>
                <span className="self-start rounded-full border border-[#dfd5c5] bg-[#faf7f2] px-4 py-2 text-sm text-stone-600">
                  std_marketing_video
                </span>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-[1fr_1fr]">
                <label className="flex min-h-[92px] cursor-pointer flex-col items-center justify-center rounded-[24px] border border-dashed border-[#dccab6] bg-[#fffaf5] px-4 py-4 text-center transition hover:bg-[#fff5e9]">
                  <span className="text-[17px] font-semibold text-[#302520]">选择 TXT 文案</span>
                  <span className="mt-2 max-w-full break-all text-sm text-stone-500">{selectedFileMeta}</span>
                  <Input accept=".txt,text/plain" className="hidden" disabled={busy !== null} onChange={handleFileChange} type="file" />
                </label>

                <div className="rounded-[24px] border border-[#e4dacb] bg-[#fffdf9] p-4">
                  <label className="text-xs tracking-[0.2em] text-stone-500" htmlFor="marketing-video-title">
                    任务标题
                  </label>
                  <Input
                    className="mt-3"
                    disabled={busy !== null}
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
                <span className="text-sm text-stone-500">创建后自动刷新任务进度</span>
              </div>
            </Card>

            <Card className="rounded-[28px] border-[#e4dacb] bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-[#241714]">任务状态</h3>
                  <p className="mt-2 text-sm text-stone-500">{workflow ? workflow.workflow_id : "创建任务后这里会显示状态。"}</p>
                </div>
                {workflow ? (
                  <span className={`w-fit rounded-full px-4 py-2 text-sm font-semibold ${statusTone(workflow.status)}`}>
                    {STATUS_LABELS[workflow.status]}
                  </span>
                ) : null}
              </div>

              {workflow ? (
                <div className="mt-5 space-y-4">
                  <div>
                    <div className="flex items-center justify-between text-sm text-stone-500">
                      <span>{workflow.current_node_label ?? "等待创建"}</span>
                      <span>{workflow.progress_percent}%</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#ebe1d3]">
                      <div
                        className="h-full rounded-full bg-[#c4633d] transition-all"
                        style={{ width: `${Math.max(0, Math.min(100, workflow.progress_percent))}%` }}
                      />
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-[20px] border border-[#e4dacb] bg-[#fffaf5] px-4 py-3">
                      <p className="text-xs tracking-[0.18em] text-stone-500">任务类型</p>
                      <p className="mt-2 text-sm font-semibold text-[#241714]">{workflow.task_type_label}</p>
                    </div>
                    <div className="rounded-[20px] border border-[#e4dacb] bg-[#fffaf5] px-4 py-3">
                      <p className="text-xs tracking-[0.18em] text-stone-500">更新时间</p>
                      <p className="mt-2 text-sm font-semibold text-[#241714]">{formatTime(workflow.updated_at)}</p>
                    </div>
                    <div className="rounded-[20px] border border-[#e4dacb] bg-[#fffaf5] px-4 py-3">
                      <p className="text-xs tracking-[0.18em] text-stone-500">当前节点</p>
                      <p className="mt-2 text-sm font-semibold text-[#241714]">{workflow.current_node_label ?? "--"}</p>
                    </div>
                  </div>

                  {workflow.error_message ? (
                    <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{workflow.error_message}</p>
                  ) : null}

                  {workflow.download.available ? (
                    <div className="rounded-[24px] border border-emerald-200 bg-emerald-50 p-4">
                      <p className="text-sm font-semibold text-emerald-800">成片已生成</p>
                      <p className="mt-2 break-all text-sm text-emerald-700">{downloadUrl ?? workflow.download.final_video_url}</p>
                      <div className="mt-4">
                        <Button onClick={handleDownload} type="button" variant="secondary">
                          下载成片
                        </Button>
                      </div>
                    </div>
                  ) : null}

                  <div className="flex flex-wrap gap-3">
                    {!workflowDone ? (
                      <Button disabled={busy !== null} onClick={handleCancel} type="button" variant="secondary">
                        {busy === "cancel" ? "取消中..." : "取消任务"}
                      </Button>
                    ) : null}
                    {mockMode ? (
                      <>
                        <Button onClick={() => showMockExample("succeeded")} type="button" variant="secondary">
                          查看成功示例
                        </Button>
                        <Button onClick={() => showMockExample("failed")} type="button" variant="secondary">
                          查看失败示例
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>
              ) : loading ? (
                <p className="mt-5 text-sm text-stone-500">正在读取账号...</p>
              ) : (
                <p className="mt-5 text-sm text-stone-500">请选择 TXT 文件并创建任务。</p>
              )}
            </Card>
          </div>

          <Card className="rounded-[28px] border-[#e4dacb] bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-lg font-semibold text-[#241714]">节点进度</h3>
                <p className="mt-2 text-sm text-stone-500">显示 TONGAN 三段进度，不在前端计算 DAG 权重。</p>
              </div>
              <span className="w-fit rounded-full border border-[#dfd5c5] bg-[#faf7f2] px-4 py-2 text-sm text-stone-600">
                TONGAN
              </span>
            </div>

            <div className="mt-5 space-y-3">
              {workflow ? (
                workflow.subtasks.map((subtask) => (
                  <div key={subtask.subtask_id} className="rounded-[22px] border border-[#e4dacb] bg-[#fffdf9] p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-[#241714]">{subtask.node_name}</p>
                        <p className="mt-1 text-xs text-stone-500">
                          {subtask.node_code} · attempt {subtask.attempt}
                        </p>
                      </div>
                      <span className={`w-fit rounded-full px-3 py-1 text-xs font-semibold ${subtaskTone(subtask.status)}`}>
                        {SUBTASK_STATUS_LABELS[subtask.status] ?? subtask.status}
                      </span>
                    </div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#ebe1d3]">
                      <div
                        className="h-full rounded-full bg-[#c4633d]"
                        style={{ width: `${Math.max(0, Math.min(100, subtask.progress_percent))}%` }}
                      />
                    </div>
                    {subtask.error_message ? <p className="mt-3 text-sm text-red-700">{subtask.error_message}</p> : null}
                  </div>
                ))
              ) : (
                <div className="rounded-[24px] border border-dashed border-[#dccab6] bg-[#fffaf5] p-8 text-center text-sm text-stone-500">
                  创建任务后会显示准备素材与基础视频、智能匹配素材和渲染成片。
                </div>
              )}
            </div>
          </Card>
        </div>
      </section>
    </UserWorkspaceShell>
  );
}
