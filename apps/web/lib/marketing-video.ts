import type { KdtTtsVoiceName } from "./tts-voices";

export type MarketingVideoWorkflowStatus =
  | "queued"
  | "running"
  | "waiting_user"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "manual_required";

export type MarketingVideoDisplayStatus = "queued" | "running" | "finished" | "failed" | "cancelled" | "waiting";

export type MarketingVideoSubtask = {
  subtask_id: string;
  node_code: string;
  node_name: string;
  worker_kind: "general" | "special";
  status: string;
  attempt: number;
  progress_percent: number;
  error_message: string | null;
};

export type MarketingVideoTaskType = "std_marketing_video" | "ip_marketing_video";
export type MarketingVideoWorkflowName = "TONGAN" | "RBZJ_KDT";
export type MarketingVideoInputName = "script_txt" | "opener_video" | "ending_video";

export { KDT_TTS_VOICES } from "./tts-voices";
export type { KdtTtsVoiceName } from "./tts-voices";

export type MarketingVideoWorkflow = {
  workflow_id: string;
  customer_id: string;
  company_id: string;
  task_type: MarketingVideoTaskType;
  task_type_label: string;
  workflow_name: MarketingVideoWorkflowName;
  title: string;
  status: MarketingVideoWorkflowStatus;
  display_status?: MarketingVideoDisplayStatus;
  active_subtask_status?: string | null;
  active_node_code?: string | null;
  current_node: string | null;
  current_node_label: string | null;
  progress_percent: number;
  created_at: string;
  updated_at: string;
  error_message: string | null;
  download: {
    available: boolean;
    final_video_url: string | null;
    task_manifest_key: string | null;
  };
  subtasks: MarketingVideoSubtask[];
};

export type MarketingVideoWorkflowSummary = Omit<MarketingVideoWorkflow, "subtasks">;

export type CreateMarketingVideoWorkflowRequest = {
  customer_id: string;
  company_id: string;
  task_type: MarketingVideoTaskType;
  workflow_name: MarketingVideoWorkflowName;
  tts_voice?: KdtTtsVoiceName;
  mode: "standard";
  title: string;
  input_bundle: {
    script_txt: {
      upload_session_id: string;
      filename: string;
      tos_key?: string;
    };
    opener_video?: {
      upload_session_id: string;
      filename: string;
      tos_key?: string;
    };
    ending_video?: {
      upload_session_id: string;
      filename: string;
      tos_key?: string;
    };
  };
};

export type MarketingVideoUploadResult = {
  upload_session_id: string;
  filename: string;
  tos_key?: string;
};

export type MarketingVideoInputUploadResult = Record<MarketingVideoInputName, MarketingVideoUploadResult | undefined> & {
  script_txt: MarketingVideoUploadResult;
};

export type MarketingVideoWorkflowProfile = {
  kind: "tongan" | "kdt";
  customerId: "tongan" | "kdt";
  taskType: MarketingVideoTaskType;
  workflowName: MarketingVideoWorkflowName;
  mode: "standard";
  defaultTitle: string;
  modeLabel: string;
  taskBadge: string;
  description: string;
  inputHint: string;
  supportsOpenerEnding: boolean;
};

type MarketingVideoPresignResponse = {
  upload_session_id?: string;
  upload_url?: string;
  url?: string;
  tos_key?: string;
  object_key?: string;
  objects?: Array<{
    input_name?: string;
    upload_key?: string;
    upload_url?: string;
    content_type?: string;
    method?: string;
  }>;
};

type MockOutcome = "auto" | "succeeded" | "failed";

const MOCK_STORAGE_KEY = "marketing-video-stage6a-workflows";
const TONGAN_MOCK_NODE_NAMES = [
  ["tongan_pre_pipeline", "准备素材与基础视频", "general"],
  ["tongan_pipeline_exec", "智能匹配素材", "special"],
  ["tongan_post_pipeline", "渲染成片", "general"],
] as const;
const KDT_MOCK_NODE_NAMES = [
  ["kdt_validate_inputs", "校验输入", "general"],
  ["kdt_pre_pipeline", "准备素材", "general"],
  ["kdt_pipeline_exec", "智能匹配", "special"],
  ["kdt_post_pipeline", "渲染成片", "general"],
] as const;

const TONGAN_STAGE5C_NODE_ORDER = ["tongan_pre_pipeline", "tongan_pipeline_exec", "tongan_post_pipeline"] as const;
const KDT_NODE_ORDER = ["kdt_validate_inputs", "kdt_pre_pipeline", "kdt_pipeline_exec", "kdt_post_pipeline"] as const;

const MARKETING_VIDEO_NODE_LABELS: Record<string, string> = {
  tongan_pre_pipeline: "准备素材与基础视频",
  tongan_pipeline_exec: "智能匹配素材",
  tongan_post_pipeline: "渲染成片",
  kdt_validate_inputs: "校验输入",
  kdt_pre_pipeline: "准备素材",
  kdt_pipeline_exec: "智能匹配",
  kdt_post_pipeline: "渲染成片",
};

const TONGAN_PROFILE: MarketingVideoWorkflowProfile = {
  kind: "tongan",
  customerId: "tongan",
  taskType: "std_marketing_video",
  workflowName: "TONGAN",
  mode: "standard",
  defaultTitle: "TONGAN 07 staging sample",
  modeLabel: "TONGAN 标准",
  taskBadge: "标准视频模式",
  description: "上传短视频的文案并创建 TONGAN 标准营销视频任务。创建后可以离开本页，后续进度、停止、改名和下载都在任务中心处理。",
  inputHint: "输入短视频的文案(txt文件格式)",
  supportsOpenerEnding: false,
};

const KDT_PROFILE: MarketingVideoWorkflowProfile = {
  kind: "kdt",
  customerId: "kdt",
  taskType: "ip_marketing_video",
  workflowName: "RBZJ_KDT",
  mode: "standard",
  defaultTitle: "KDT IP 视频样片",
  modeLabel: "KDT IP营销视频",
  taskBadge: "IP 视频模式",
  description: "上传 KDT 文案并创建 IP 出镜营销视频任务。可选上传开头和结尾视频；不勾选时使用后端默认素材策略。",
  inputHint: "输入 KDT 文案(txt文件格式)",
  supportsOpenerEnding: true,
};

function getApiMode(): "mock" | "real" {
  const mode = process.env.NEXT_PUBLIC_MARKETING_VIDEO_API_MODE;
  return mode === "real" ? "real" : "mock";
}

export function isMarketingVideoMockMode(): boolean {
  return getApiMode() === "mock";
}

export function getMarketingVideoWorkflowProfile(companyId: number | null | undefined): MarketingVideoWorkflowProfile | null {
  if (companyId === 1) return KDT_PROFILE;
  if (companyId === 2 || companyId === 10) return TONGAN_PROFILE;
  return null;
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function getMarketingVideoNodeLabel(nodeCode: string, nodeName?: string | null): string {
  return MARKETING_VIDEO_NODE_LABELS[nodeCode] ?? nodeName ?? nodeCode;
}

function getCanonicalNodeIndex(nodeCode: string): number {
  const order = [...TONGAN_STAGE5C_NODE_ORDER, ...KDT_NODE_ORDER] as readonly string[];
  const index = order.indexOf(nodeCode);
  return index === -1 ? Number.MAX_SAFE_INTEGER : index;
}

function getFailedSubtask(subtasks: MarketingVideoSubtask[]): MarketingVideoSubtask | undefined {
  return subtasks.find((subtask) => subtask.status === "failed" || subtask.status === "manual_required");
}

function isActiveMarketingVideoSubtaskStatus(status: string | null | undefined): boolean {
  return status === "running" || status === "accepted" || status === "dispatching";
}

function isMarketingVideoDisplayStatus(status: unknown): status is MarketingVideoDisplayStatus {
  return (
    status === "queued" ||
    status === "running" ||
    status === "finished" ||
    status === "failed" ||
    status === "cancelled" ||
    status === "waiting"
  );
}

export function formatMarketingVideoSubtaskStatus(status: string | null | undefined, attempt?: number | null): string {
  const statusText =
    status === "succeeded"
      ? "已完成"
      : status === "running" || status === "accepted" || status === "dispatching"
        ? "执行中"
        : status === "ready" || status === "pending" || status === "queued"
          ? "排队中"
          : status === "failed"
            ? "失败"
            : status === "cancelled"
              ? "已停止"
              : status === "skipped"
                ? "已跳过"
                : status === "timeout"
                  ? "已超时"
                  : status === "lost"
                    ? "连接丢失"
                    : status === "manual_required"
                      ? "需人工处理"
                      : "未知状态";
  const attemptText = typeof attempt === "number" && Number.isFinite(attempt) && attempt > 0 ? `第 ${attempt} 次执行` : "尚未执行";
  return `${statusText} · ${attemptText}`;
}

export function deriveMarketingVideoDisplayQueueStatus(
  workflow: Pick<MarketingVideoWorkflow, "status"> &
    Partial<Pick<MarketingVideoWorkflow, "display_status" | "active_subtask_status" | "subtasks">>,
): MarketingVideoDisplayStatus {
  if (isMarketingVideoDisplayStatus(workflow.display_status)) return workflow.display_status;

  if (workflow.status === "succeeded") return "finished";
  if (workflow.status === "failed") return "failed";
  if (workflow.status === "cancelled") return "cancelled";
  if (workflow.status === "waiting_user" || workflow.status === "manual_required") return "waiting";
  if (isActiveMarketingVideoSubtaskStatus(workflow.active_subtask_status)) return "running";
  if (workflow.subtasks?.some((subtask) => isActiveMarketingVideoSubtaskStatus(subtask.status))) return "running";
  if (workflow.status === "queued") return "queued";
  if (workflow.subtasks && workflow.subtasks.length > 0) return "queued";
  return "running";
}

function buildNodeFailureMessage(subtask: MarketingVideoSubtask | undefined, workflowMessage: string | null): string | null {
  if (!subtask) return workflowMessage;
  const label = getMarketingVideoNodeLabel(subtask.node_code, subtask.node_name);
  const message = subtask.error_message ?? workflowMessage ?? "节点执行失败，请查看任务日志。";
  return message.includes(label) ? message : `${label}：${message}`;
}

export function normalizeMarketingVideoWorkflow(workflow: MarketingVideoWorkflow): MarketingVideoWorkflow {
  const subtasks = workflow.subtasks
    .map((subtask) => ({
      ...subtask,
      node_name: getMarketingVideoNodeLabel(subtask.node_code, subtask.node_name),
    }))
    .sort((left, right) => {
      const leftIndex = getCanonicalNodeIndex(left.node_code);
      const rightIndex = getCanonicalNodeIndex(right.node_code);
      if (leftIndex !== rightIndex) return leftIndex - rightIndex;
      return 0;
    });
  const failedSubtask = getFailedSubtask(subtasks);
  const currentNodeLabel = workflow.current_node
    ? getMarketingVideoNodeLabel(workflow.current_node, workflow.current_node_label)
    : failedSubtask
      ? getMarketingVideoNodeLabel(failedSubtask.node_code, failedSubtask.node_name)
      : workflow.current_node_label;

  return {
    ...workflow,
    current_node_label: currentNodeLabel,
    error_message:
      workflow.status === "failed" || workflow.status === "manual_required"
        ? buildNodeFailureMessage(failedSubtask, workflow.error_message)
        : workflow.error_message,
    download: {
      ...workflow.download,
      available: workflow.download.available || Boolean(workflow.download.final_video_url),
    },
    subtasks,
  };
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { error?: { message?: string }; detail?: string; message?: string }
      | null;
    throw new Error(payload?.error?.message ?? payload?.detail ?? payload?.message ?? `Request failed: ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function readMockWorkflows(): Record<string, MarketingVideoWorkflow & { mock_outcome?: MockOutcome }> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(window.localStorage.getItem(MOCK_STORAGE_KEY) ?? "{}") as Record<
      string,
      MarketingVideoWorkflow & { mock_outcome?: MockOutcome }
    >;
  } catch {
    return {};
  }
}

function writeMockWorkflow(workflow: MarketingVideoWorkflow & { mock_outcome?: MockOutcome }) {
  if (typeof window === "undefined") return;
  const workflows = readMockWorkflows();
  workflows[workflow.workflow_id] = workflow;
  window.localStorage.setItem(MOCK_STORAGE_KEY, JSON.stringify(workflows));
}

function getMockNodeNames(workflowName: MarketingVideoWorkflowName) {
  return workflowName === "RBZJ_KDT" ? KDT_MOCK_NODE_NAMES : TONGAN_MOCK_NODE_NAMES;
}

function buildSubtasks(stageIndex: number, status: MarketingVideoWorkflowStatus, workflowName: MarketingVideoWorkflowName = "TONGAN"): MarketingVideoSubtask[] {
  return getMockNodeNames(workflowName).map(([node_code, node_name, worker_kind], index) => {
    if (status === "failed" && index === stageIndex) {
      return {
        subtask_id: `st_mock_${node_code}`,
        node_code,
        node_name,
        worker_kind,
        status: "failed",
        attempt: 1,
        progress_percent: 62,
        error_message: "样例 07 文案解析失败，请检查 TXT 内容后重试。",
      };
    }

    if (status === "succeeded" || index < stageIndex) {
      return {
        subtask_id: `st_mock_${node_code}`,
        node_code,
        node_name,
        worker_kind,
        status: "succeeded",
        attempt: 1,
        progress_percent: 100,
        error_message: null,
      };
    }

    if (index === stageIndex && status === "running") {
      return {
        subtask_id: `st_mock_${node_code}`,
        node_code,
        node_name,
        worker_kind,
        status: "running",
        attempt: 1,
        progress_percent: 56,
        error_message: null,
      };
    }

    return {
      subtask_id: `st_mock_${node_code}`,
      node_code,
      node_name,
      worker_kind,
      status: "queued",
      attempt: 0,
      progress_percent: 0,
      error_message: null,
    };
  });
}

function withMockProgress(workflow: MarketingVideoWorkflow & { mock_outcome?: MockOutcome }): MarketingVideoWorkflow {
  const elapsedSeconds = Math.max(0, (Date.now() - new Date(workflow.created_at).getTime()) / 1000);
  const outcome = workflow.mock_outcome ?? "auto";
  const now = new Date().toISOString();

  if (outcome === "failed") {
    return {
      ...workflow,
      status: "failed",
      current_node: "tongan_pipeline_exec",
      current_node_label: "智能匹配素材",
      progress_percent: 52,
      updated_at: now,
      error_message: "样例 07 文案解析失败，请检查 TXT 内容后重试。",
      download: { available: false, final_video_url: null, task_manifest_key: null },
      subtasks: buildSubtasks(1, "failed", workflow.workflow_name),
    };
  }

  if (outcome === "succeeded" || elapsedSeconds >= 9) {
    return {
      ...workflow,
      status: "succeeded",
      current_node: null,
      current_node_label: "已完成",
      progress_percent: 100,
      updated_at: now,
      error_message: null,
      download: {
        available: true,
        final_video_url: "https://autocut-malin.tos-cn-shanghai.volces.com/video-workflows/staging/tongan/mock/tongan-07-final.mp4",
        task_manifest_key: "video-workflows/staging/tongan/final/task_manifest.json",
      },
      subtasks: buildSubtasks(getMockNodeNames(workflow.workflow_name).length, "succeeded", workflow.workflow_name),
    };
  }

  if (elapsedSeconds < 2) {
    return {
      ...workflow,
      status: "queued",
      current_node: null,
      current_node_label: "等待调度",
      progress_percent: 8,
      updated_at: now,
      subtasks: buildSubtasks(0, "queued", workflow.workflow_name),
    };
  }

  const stageIndex = elapsedSeconds < 4 ? 0 : elapsedSeconds < 7 ? 1 : 2;
  const [current_node, current_node_label] = getMockNodeNames(workflow.workflow_name)[stageIndex];
  return {
    ...workflow,
    status: "running",
    current_node,
    current_node_label,
    progress_percent: Math.min(96, Math.round(18 + elapsedSeconds * 8)),
    updated_at: now,
    subtasks: buildSubtasks(stageIndex, "running", workflow.workflow_name),
  };
}

export function buildMarketingVideoMockWorkflow(outcome: Exclude<MockOutcome, "auto">): MarketingVideoWorkflow {
  const now = new Date().toISOString();
  const workflow: MarketingVideoWorkflow & { mock_outcome?: MockOutcome } = {
    workflow_id: `wf_mock_${outcome}_${Date.now()}`,
    customer_id: "tongan",
    company_id: "tongan",
    task_type: "std_marketing_video",
    task_type_label: "标准营销视频剪辑",
    workflow_name: "TONGAN",
    title: outcome === "failed" ? "TONGAN 07 失败样例" : "TONGAN 07 成功样例",
    status: "queued",
    current_node: null,
    current_node_label: "等待调度",
    progress_percent: 0,
    created_at: now,
    updated_at: now,
    error_message: null,
    download: { available: false, final_video_url: null, task_manifest_key: null },
    subtasks: buildSubtasks(0, "queued"),
    mock_outcome: outcome,
  };
  return withMockProgress(workflow);
}

export async function uploadMarketingVideoScript(
  file: File,
  options?: { companyId?: number | string; onProgress?: (percent: number) => void },
): Promise<MarketingVideoUploadResult> {
  const bundle = await uploadMarketingVideoInputs({ scriptFile: file, companyId: options?.companyId, onProgress: options?.onProgress });
  return bundle.script_txt;
}

function assertScriptFile(file: File) {
  if (!file.name.toLowerCase().endsWith(".txt")) {
    throw new Error("请上传 TXT 文案文件。");
  }

  if (file.size === 0) {
    throw new Error("TXT 文件为空，请重新选择。");
  }
}

function assertVideoFile(file: File, label: string) {
  if (!file.name.toLowerCase().endsWith(".mp4")) {
    throw new Error(`${label} 请上传 MP4 文件。`);
  }
  if (file.size === 0) {
    throw new Error(`${label} 文件为空，请重新选择。`);
  }
}

async function putPresignedObject(args: {
  file: File;
  object: NonNullable<MarketingVideoPresignResponse["objects"]>[number] | undefined;
  fallbackContentType: string;
  onProgress?: (loaded: number, total: number) => void;
}) {
  const uploadUrl = args.object?.upload_url;
  const uploadMethod = args.object?.method ?? "PUT";
  if (!uploadUrl) {
    throw new Error("上传地址缺失，请稍后重试。");
  }
  if (uploadMethod.toUpperCase() !== "PUT") {
    throw new Error(`不支持的上传方法：${uploadMethod}`);
  }

  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(uploadMethod, uploadUrl);
    xhr.setRequestHeader("Content-Type", args.object?.content_type || args.file.type || args.fallbackContentType);
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      args.onProgress?.(event.loaded, event.total);
    };
    xhr.onerror = () => reject(new Error("上传到 TOS 失败，请检查网络后重试。"));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
        return;
      }
      reject(new Error(`TOS upload failed: ${xhr.status}`));
    };
    xhr.send(args.file);
  });
}

export async function uploadMarketingVideoInputs(options: {
  scriptFile: File;
  companyId?: number | string;
  profile?: MarketingVideoWorkflowProfile;
  openerFile?: File | null;
  endingFile?: File | null;
  onProgress?: (percent: number) => void;
}): Promise<MarketingVideoInputUploadResult> {
  const profile = options.profile ?? TONGAN_PROFILE;
  assertScriptFile(options.scriptFile);
  if (options.openerFile) assertVideoFile(options.openerFile, "开头视频");
  if (options.endingFile) assertVideoFile(options.endingFile, "结尾视频");

  if (getApiMode() === "mock") {
    options.onProgress?.(25);
    await sleep(120);
    options.onProgress?.(70);
    await sleep(120);
    options.onProgress?.(100);
    return {
      script_txt: {
        upload_session_id: `upl_mock_${Date.now()}`,
        filename: options.scriptFile.name,
        tos_key: `video-workflows/staging/${profile.customerId}/uploads/mock/${encodeURIComponent(options.scriptFile.name)}`,
      },
      opener_video: options.openerFile
        ? {
            upload_session_id: `upl_mock_${Date.now()}`,
            filename: options.openerFile.name,
            tos_key: `video-workflows/staging/${profile.customerId}/uploads/mock/${encodeURIComponent(options.openerFile.name)}`,
          }
        : undefined,
      ending_video: options.endingFile
        ? {
            upload_session_id: `upl_mock_${Date.now()}`,
            filename: options.endingFile.name,
            tos_key: `video-workflows/staging/${profile.customerId}/uploads/mock/${encodeURIComponent(options.endingFile.name)}`,
          }
        : undefined,
    };
  }

  const presign = await fetchJson<MarketingVideoPresignResponse>("/api/proxy/api/marketing-video/uploads/presign", {
    method: "POST",
    body: JSON.stringify({
      customer_id: profile.customerId,
      company_id: options.companyId !== undefined ? String(options.companyId) : profile.customerId,
      filename: options.scriptFile.name,
      content_type: options.scriptFile.type || "text/plain",
      task_type: profile.taskType,
      workflow_name: profile.workflowName,
      mode: profile.mode,
      opener_video_filename: options.openerFile?.name,
      ending_video_filename: options.endingFile?.name,
    }),
  });

  if (!presign.upload_session_id) {
    throw new Error("上传会话缺失，请稍后重试。");
  }
  const objectByName = new Map((presign.objects ?? []).map((object) => [object.input_name, object]));
  const scriptObject =
    objectByName.get("script_txt") ??
    (presign.upload_url || presign.url
      ? { input_name: "script_txt", upload_url: presign.upload_url ?? presign.url, upload_key: presign.tos_key ?? presign.object_key, method: "PUT" }
      : undefined);
  const scriptUploadKey = scriptObject?.upload_key;
  if (!scriptUploadKey) {
    throw new Error("上传对象路径缺失，请稍后重试。");
  }

  const uploadJobs: Array<{ name: MarketingVideoInputName; file: File; object: NonNullable<MarketingVideoPresignResponse["objects"]>[number] | undefined; contentType: string }> = [
    { name: "script_txt", file: options.scriptFile, object: scriptObject, contentType: "text/plain" },
  ];
  if (options.openerFile) uploadJobs.push({ name: "opener_video", file: options.openerFile, object: objectByName.get("opener_video"), contentType: "video/mp4" });
  if (options.endingFile) uploadJobs.push({ name: "ending_video", file: options.endingFile, object: objectByName.get("ending_video"), contentType: "video/mp4" });

  const finished = new Map<MarketingVideoInputName, number>();
  for (const job of uploadJobs) {
    const objectKey = job.object?.upload_key;
    if (!objectKey) throw new Error(`${job.name} 上传对象路径缺失，请稍后重试。`);
    await putPresignedObject({
      file: job.file,
      object: job.object,
      fallbackContentType: job.contentType,
      onProgress: (loaded, total) => {
        finished.set(job.name, total > 0 ? loaded / total : 0);
        const sum = uploadJobs.reduce((value, item) => value + (finished.get(item.name) ?? 0), 0);
        options.onProgress?.(Math.round((sum / uploadJobs.length) * 100));
      },
    });
    finished.set(job.name, 1);
    const sum = uploadJobs.reduce((value, item) => value + (finished.get(item.name) ?? 0), 0);
    options.onProgress?.(Math.round((sum / uploadJobs.length) * 100));
  }

  options.onProgress?.(100);
  return {
    script_txt: {
      upload_session_id: presign.upload_session_id,
      filename: options.scriptFile.name,
      tos_key: scriptUploadKey,
    },
    opener_video:
      options.openerFile && objectByName.get("opener_video")?.upload_key
        ? {
            upload_session_id: presign.upload_session_id,
            filename: options.openerFile.name,
            tos_key: objectByName.get("opener_video")?.upload_key,
          }
        : undefined,
    ending_video:
      options.endingFile && objectByName.get("ending_video")?.upload_key
        ? {
            upload_session_id: presign.upload_session_id,
            filename: options.endingFile.name,
            tos_key: objectByName.get("ending_video")?.upload_key,
          }
        : undefined,
  };
}

export async function createMarketingVideoWorkflow(
  request: CreateMarketingVideoWorkflowRequest,
): Promise<MarketingVideoWorkflow> {
  if (getApiMode() === "mock") {
    const now = new Date().toISOString();
    const workflow: MarketingVideoWorkflow & { mock_outcome?: MockOutcome } = {
      workflow_id: `wf_mock_${Date.now()}`,
      customer_id: request.customer_id,
      company_id: request.company_id,
      task_type: request.task_type,
      task_type_label: request.task_type === "ip_marketing_video" ? "有 IP 出镜营销视频剪辑" : "标准营销视频剪辑",
      workflow_name: request.workflow_name,
      title: request.title || (request.workflow_name === "RBZJ_KDT" ? KDT_PROFILE.defaultTitle : TONGAN_PROFILE.defaultTitle),
      status: "queued",
      current_node: null,
      current_node_label: "等待调度",
      progress_percent: 8,
      created_at: now,
      updated_at: now,
      error_message: null,
      download: { available: false, final_video_url: null, task_manifest_key: null },
      subtasks: buildSubtasks(0, "queued", request.workflow_name),
      mock_outcome: "auto",
    };
    writeMockWorkflow(workflow);
    return workflow;
  }

  const workflow = await fetchJson<MarketingVideoWorkflow>("/api/proxy/api/marketing-video/workflows", {
    method: "POST",
    body: JSON.stringify(request),
  });
  return normalizeMarketingVideoWorkflow(workflow);
}

export async function listMarketingVideoWorkflows(): Promise<MarketingVideoWorkflowSummary[]> {
  if (getApiMode() === "mock") {
    const workflows = Object.values(readMockWorkflows())
      .map((workflow) => {
        const nextWorkflow = withMockProgress(workflow);
        writeMockWorkflow({ ...nextWorkflow, mock_outcome: workflow.mock_outcome });
        const { subtasks: _subtasks, ...summary } = normalizeMarketingVideoWorkflow(nextWorkflow);
        return summary;
      })
      .filter((workflow) => !(workflow as MarketingVideoWorkflowSummary & { archived_at?: string | null }).archived_at)
      .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime());
    return workflows;
  }

  const payload = await fetchJson<{ workflows: MarketingVideoWorkflowSummary[] }>("/api/proxy/api/marketing-video/workflows");
  return payload.workflows.map((workflow) => normalizeMarketingVideoWorkflow({ ...workflow, subtasks: [] }));
}

export async function getMarketingVideoWorkflow(workflowId: string): Promise<MarketingVideoWorkflow> {
  if (getApiMode() === "mock") {
    const workflow = readMockWorkflows()[workflowId];
    if (!workflow) throw new Error("未找到营销视频任务。");
    const nextWorkflow = withMockProgress(workflow);
    writeMockWorkflow({ ...nextWorkflow, mock_outcome: workflow.mock_outcome });
    return nextWorkflow;
  }

  const workflow = await fetchJson<MarketingVideoWorkflow>(
    `/api/proxy/api/marketing-video/workflows/${encodeURIComponent(workflowId)}`,
  );
  return normalizeMarketingVideoWorkflow(workflow);
}

export async function getMarketingVideoDownload(workflowId: string): Promise<string> {
  if (getApiMode() === "mock") {
    const workflow = await getMarketingVideoWorkflow(workflowId);
    if (!workflow.download.available || !workflow.download.final_video_url) {
      throw new Error("任务完成后才能下载成片。");
    }
    return workflow.download.final_video_url;
  }

  const payload = await fetchJson<{ download_url?: string; final_video_url?: string }>(
    `/api/proxy/api/marketing-video/workflows/${encodeURIComponent(workflowId)}/download`,
  );
  const url = payload.download_url ?? payload.final_video_url;
  if (!url) throw new Error("下载链接暂不可用。");
  return url;
}

export async function cancelMarketingVideoWorkflow(workflowId: string): Promise<MarketingVideoWorkflow> {
  if (getApiMode() === "mock") {
    const workflow = readMockWorkflows()[workflowId];
    if (!workflow) throw new Error("未找到营销视频任务。");
    const cancelled: MarketingVideoWorkflow & { mock_outcome?: MockOutcome } = {
      ...workflow,
      status: "cancelled",
      current_node: null,
      current_node_label: "已取消",
      progress_percent: workflow.progress_percent,
      updated_at: new Date().toISOString(),
      error_message: null,
      mock_outcome: "auto",
    };
    writeMockWorkflow(cancelled);
    return cancelled;
  }

  await fetchJson(`/api/proxy/api/marketing-video/workflows/${encodeURIComponent(workflowId)}/cancel`, {
    method: "POST",
  });
  return getMarketingVideoWorkflow(workflowId);
}

export async function updateMarketingVideoWorkflowTitle(workflowId: string, title: string): Promise<MarketingVideoWorkflow> {
  if (getApiMode() === "mock") {
    const workflow = readMockWorkflows()[workflowId];
    if (!workflow) throw new Error("未找到营销视频任务。");
    const updated: MarketingVideoWorkflow & { mock_outcome?: MockOutcome } = {
      ...workflow,
      title: title.trim(),
      updated_at: new Date().toISOString(),
    };
    writeMockWorkflow(updated);
    return normalizeMarketingVideoWorkflow(updated);
  }

  const workflow = await fetchJson<MarketingVideoWorkflow>(
    `/api/proxy/api/marketing-video/workflows/${encodeURIComponent(workflowId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ title }),
    },
  );
  return normalizeMarketingVideoWorkflow(workflow);
}

export async function archiveMarketingVideoWorkflow(workflowId: string): Promise<void> {
  if (getApiMode() === "mock") {
    const workflows = readMockWorkflows();
    delete workflows[workflowId];
    window.localStorage.setItem(MOCK_STORAGE_KEY, JSON.stringify(workflows));
    return;
  }

  await fetchJson(`/api/proxy/api/marketing-video/workflows/${encodeURIComponent(workflowId)}`, {
    method: "DELETE",
  });
}
