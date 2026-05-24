"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthResponse } from "@/lib/auth";
import {
  createMarketingVideoWorkflow,
  getMarketingVideoWorkflowProfile,
  isMarketingVideoMockMode,
  KDT_TTS_VOICES,
  KdtTtsVoiceName,
  MarketingVideoWorkflowSummary,
  uploadMarketingVideoInputs,
} from "@/lib/marketing-video";
import { UserWorkspaceShell } from "@/components/navigation/user-workspace-shell";
import { useUserWorkspaceData } from "@/components/navigation/use-user-workspace-data";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type BusyState = "upload" | "create" | null;

function buildDefaultTitle(file: File | null, fallback: string) {
  if (!file) return fallback;
  return file.name.replace(/\.txt$/i, "") || fallback;
}

function hasMarketingVideoFullAccess(companyId: number | null | undefined) {
  return Boolean(getMarketingVideoWorkflowProfile(companyId));
}

export function MarketingVideoWorkspace() {
  const router = useRouter();
  const [user, setUser] = useState<AuthResponse["user"] | null>(null);
  const workspace = useUserWorkspaceData(user?.username, user?.company_id);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<BusyState>(null);
  const [scriptFile, setScriptFile] = useState<File | null>(null);
  const [useCustomOpenEnd, setUseCustomOpenEnd] = useState(false);
  const [openerFile, setOpenerFile] = useState<File | null>(null);
  const [endingFile, setEndingFile] = useState<File | null>(null);
  const [kdtTtsVoice, setKdtTtsVoice] = useState<KdtTtsVoiceName>("康迪");
  const [fileInputKey, setFileInputKey] = useState(0);
  const [openerInputKey, setOpenerInputKey] = useState(0);
  const [endingInputKey, setEndingInputKey] = useState(0);
  const activeProfile = getMarketingVideoWorkflowProfile(user?.company_id);
  const [title, setTitle] = useState("TONGAN 07 staging sample");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [createdWorkflow, setCreatedWorkflow] = useState<MarketingVideoWorkflowSummary | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mockMode = isMarketingVideoMockMode();
  const pageLocked = Boolean(user && !hasMarketingVideoFullAccess(user.company_id));

  const canCreate = Boolean(
    user &&
      activeProfile &&
      !pageLocked &&
      scriptFile &&
      busy === null &&
      (!activeProfile.supportsOpenerEnding || !useCustomOpenEnd || (openerFile && endingFile)),
  );
  const selectedFileMeta = useMemo(() => {
    if (!scriptFile) return "尚未选择 TXT 文件";
    const sizeKb = Math.max(1, Math.round(scriptFile.size / 1024));
    return `${scriptFile.name} · ${sizeKb} KB`;
  }, [scriptFile]);
  const openerFileMeta = useMemo(() => {
    if (!openerFile) return "尚未选择开头 MP4";
    const sizeMb = Math.max(1, Math.round(openerFile.size / 1024 / 1024));
    return `${openerFile.name} · ${sizeMb} MB`;
  }, [openerFile]);
  const endingFileMeta = useMemo(() => {
    if (!endingFile) return "尚未选择结尾 MP4";
    const sizeMb = Math.max(1, Math.round(endingFile.size / 1024 / 1024));
    return `${endingFile.name} · ${sizeMb} MB`;
  }, [endingFile]);

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
      const profile = getMarketingVideoWorkflowProfile(payload.user.company_id);
      if (profile) setTitle(profile.defaultTitle);
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
    if (file) setTitle(buildDefaultTitle(file, activeProfile?.defaultTitle ?? "TONGAN 07 staging sample"));
  }

  function handleOpenerFileChange(event: ChangeEvent<HTMLInputElement>) {
    setError(null);
    setNotice(null);
    setOpenerFile(event.target.files?.[0] ?? null);
  }

  function handleEndingFileChange(event: ChangeEvent<HTMLInputElement>) {
    setError(null);
    setNotice(null);
    setEndingFile(event.target.files?.[0] ?? null);
  }

  function resetForm(options: { clearMessages?: boolean } = { clearMessages: true }) {
    setScriptFile(null);
    setOpenerFile(null);
    setEndingFile(null);
    setUseCustomOpenEnd(false);
    setKdtTtsVoice("康迪");
    setTitle(activeProfile?.defaultTitle ?? "TONGAN 07 staging sample");
    setUploadProgress(0);
    setFileInputKey((value) => value + 1);
    setOpenerInputKey((value) => value + 1);
    setEndingInputKey((value) => value + 1);
    if (options.clearMessages !== false) {
      setNotice(null);
      setError(null);
    }
  }

  async function handleCreateTask() {
    if (!user || user.company_id === null || user.company_id === undefined || !scriptFile || pageLocked || !activeProfile) return;
    setError(null);
    setNotice(null);
    try {
      setBusy("upload");
      const uploads = await uploadMarketingVideoInputs({
        scriptFile,
        companyId: user.company_id,
        profile: activeProfile,
        openerFile: activeProfile.supportsOpenerEnding && useCustomOpenEnd ? openerFile : null,
        endingFile: activeProfile.supportsOpenerEnding && useCustomOpenEnd ? endingFile : null,
        onProgress: setUploadProgress,
      });
      setBusy("create");
      const inputBundle = {
        script_txt: {
          upload_session_id: uploads.script_txt.upload_session_id,
          filename: uploads.script_txt.filename,
          tos_key: uploads.script_txt.tos_key,
        },
        ...(uploads.opener_video
          ? {
              opener_video: {
                upload_session_id: uploads.opener_video.upload_session_id,
                filename: uploads.opener_video.filename,
                tos_key: uploads.opener_video.tos_key,
              },
            }
          : {}),
        ...(uploads.ending_video
          ? {
              ending_video: {
                upload_session_id: uploads.ending_video.upload_session_id,
                filename: uploads.ending_video.filename,
                tos_key: uploads.ending_video.tos_key,
              },
            }
          : {}),
      };
      const workflow = await createMarketingVideoWorkflow({
        customer_id: activeProfile.customerId,
        company_id: String(user.company_id),
        task_type: activeProfile.taskType,
        workflow_name: activeProfile.workflowName,
        ...(activeProfile.kind === "kdt" ? { tts_voice: kdtTtsVoice } : {}),
        mode: activeProfile.mode,
        title: title.trim() || buildDefaultTitle(scriptFile, activeProfile.defaultTitle),
        input_bundle: inputBundle,
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
                  {activeProfile?.description ?? "上传短视频的文案并创建营销视频任务。创建后可以离开本页，后续进度、停止、改名和下载都在任务中心处理。"}
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[20px] border border-[#e4dacb] bg-[#fffaf5] px-4 py-3">
                  <p className="text-xs tracking-[0.2em] text-stone-500">当前模式</p>
                  <p className="mt-2 text-base font-semibold text-[#241714]">{activeProfile?.modeLabel ?? "暂未开放"}</p>
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
                  <p className="mt-2 text-sm leading-7 text-stone-500">{activeProfile?.inputHint ?? "输入短视频的文案(txt文件格式)"}</p>
                </div>
                <span className="self-start rounded-full border border-[#dfd5c5] bg-[#faf7f2] px-4 py-2 text-sm text-stone-600">
                  {activeProfile?.taskBadge ?? "未开放"}
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

              {activeProfile?.kind === "kdt" ? (
                <div className="mt-5 rounded-[24px] border border-[#e4dacb] bg-[#fffdf9] p-4" data-testid="kdt-tts-voice-control">
                  <label className="text-xs tracking-[0.2em] text-stone-500" htmlFor="kdt-tts-voice">
                    TTS 音色
                  </label>
                  <select
                    className="mt-3 h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-[#241714] shadow-sm outline-none transition focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={busy !== null || pageLocked}
                    id="kdt-tts-voice"
                    onChange={(event) => setKdtTtsVoice(event.target.value as KdtTtsVoiceName)}
                    value={kdtTtsVoice}
                  >
                    {KDT_TTS_VOICES.map((voice) => (
                      <option key={voice.value} value={voice.value}>
                        {voice.label}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}

              {activeProfile?.supportsOpenerEnding ? (
                <div className="mt-5 rounded-[24px] border border-[#e4dacb] bg-[#fffdf9] p-4" data-testid="kdt-open-end-controls">
                  <label className="flex items-start gap-3 text-sm font-semibold text-[#241714]">
                    <input
                      checked={useCustomOpenEnd}
                      className="mt-1 h-4 w-4 accent-[#8f5d38]"
                      disabled={busy !== null || pageLocked}
                      onChange={(event) => {
                        setUseCustomOpenEnd(event.target.checked);
                        if (!event.target.checked) {
                          setOpenerFile(null);
                          setEndingFile(null);
                          setOpenerInputKey((value) => value + 1);
                          setEndingInputKey((value) => value + 1);
                        }
                      }}
                      type="checkbox"
                    />
                    <span>
                      使用自定义开头和结尾视频
                      <span className="mt-1 block text-sm font-normal leading-6 text-stone-500">
                        勾选后需要上传开头 MP4 和结尾 MP4；不勾选时后端使用默认素材策略。
                      </span>
                    </span>
                  </label>

                  {useCustomOpenEnd ? (
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <label className="flex min-h-[88px] cursor-pointer flex-col items-center justify-center rounded-[22px] border border-dashed border-[#dccab6] bg-[#fffaf5] px-4 py-4 text-center transition hover:bg-[#fff5e9]">
                        <span className="text-[16px] font-semibold text-[#302520]">选择开头 MP4</span>
                        <span className="mt-2 max-w-full break-all text-sm text-stone-500">{openerFileMeta}</span>
                        <Input
                          key={openerInputKey}
                          accept=".mp4,video/mp4"
                          className="hidden"
                          disabled={busy !== null || pageLocked}
                          onChange={handleOpenerFileChange}
                          type="file"
                        />
                      </label>
                      <label className="flex min-h-[88px] cursor-pointer flex-col items-center justify-center rounded-[22px] border border-dashed border-[#dccab6] bg-[#fffaf5] px-4 py-4 text-center transition hover:bg-[#fff5e9]">
                        <span className="text-[16px] font-semibold text-[#302520]">选择结尾 MP4</span>
                        <span className="mt-2 max-w-full break-all text-sm text-stone-500">{endingFileMeta}</span>
                        <Input
                          key={endingInputKey}
                          accept=".mp4,video/mp4"
                          className="hidden"
                          disabled={busy !== null || pageLocked}
                          onChange={handleEndingFileChange}
                          type="file"
                        />
                      </label>
                    </div>
                  ) : null}
                </div>
              ) : null}

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
