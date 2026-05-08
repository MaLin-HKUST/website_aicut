export type MarketingVideoWorkflowStatus =
  | "queued"
  | "running"
  | "waiting_user"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "manual_required";

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

export type MarketingVideoWorkflow = {
  workflow_id: string;
  customer_id: string;
  company_id: string;
  task_type: "std_marketing_video";
  task_type_label: string;
  workflow_name: "TONGAN";
  title: string;
  status: MarketingVideoWorkflowStatus;
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

export type CreateMarketingVideoWorkflowRequest = {
  customer_id: string;
  company_id: string;
  task_type: "std_marketing_video";
  workflow_name: "TONGAN";
  mode: "standard";
  title: string;
  input_bundle: {
    script_txt: {
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
const MOCK_NODE_NAMES = [
  ["tongan_input_prepare", "文案校验", "general"],
  ["tongan_tts", "语音生成", "general"],
  ["tongan_asr", "字幕识别", "general"],
  ["tongan_timeline", "时间线整理", "general"],
  ["tongan_pipeline_exec", "视频合成", "special"],
  ["tongan_finalize", "结果归档", "general"],
] as const;

const TONGAN_STAGE5C_NODE_ORDER = ["tongan_pre_pipeline", "tongan_pipeline_exec", "tongan_post_pipeline"] as const;

const TONGAN_STAGE5C_NODE_LABELS: Record<(typeof TONGAN_STAGE5C_NODE_ORDER)[number], string> = {
  tongan_pre_pipeline: "准备素材与基础视频",
  tongan_pipeline_exec: "智能匹配素材",
  tongan_post_pipeline: "渲染成片",
};

function getApiMode(): "mock" | "real" {
  const mode = process.env.NEXT_PUBLIC_MARKETING_VIDEO_API_MODE;
  return mode === "real" ? "real" : "mock";
}

export function isMarketingVideoMockMode(): boolean {
  return getApiMode() === "mock";
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function getMarketingVideoNodeLabel(nodeCode: string, nodeName?: string | null): string {
  return TONGAN_STAGE5C_NODE_LABELS[nodeCode as keyof typeof TONGAN_STAGE5C_NODE_LABELS] ?? nodeName ?? nodeCode;
}

function getCanonicalNodeIndex(nodeCode: string): number {
  const index = TONGAN_STAGE5C_NODE_ORDER.indexOf(nodeCode as (typeof TONGAN_STAGE5C_NODE_ORDER)[number]);
  return index === -1 ? Number.MAX_SAFE_INTEGER : index;
}

function getFailedSubtask(subtasks: MarketingVideoSubtask[]): MarketingVideoSubtask | undefined {
  return subtasks.find((subtask) => subtask.status === "failed" || subtask.status === "manual_required");
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

function buildSubtasks(stageIndex: number, status: MarketingVideoWorkflowStatus): MarketingVideoSubtask[] {
  return MOCK_NODE_NAMES.map(([node_code, node_name, worker_kind], index) => {
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
      attempt: 1,
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
      current_node: "tongan_timeline",
      current_node_label: "时间线整理",
      progress_percent: 52,
      updated_at: now,
      error_message: "样例 07 文案解析失败，请检查 TXT 内容后重试。",
      download: { available: false, final_video_url: null, task_manifest_key: null },
      subtasks: buildSubtasks(3, "failed"),
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
        final_video_url: "https://example.com/stage6a/tongan-07-final.mp4",
        task_manifest_key: "video-workflows/staging/tongan/final/task_manifest.json",
      },
      subtasks: buildSubtasks(MOCK_NODE_NAMES.length, "succeeded"),
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
      subtasks: buildSubtasks(0, "queued"),
    };
  }

  const stageIndex = elapsedSeconds < 4 ? 1 : elapsedSeconds < 6 ? 2 : elapsedSeconds < 8 ? 4 : 5;
  const [current_node, current_node_label] = MOCK_NODE_NAMES[stageIndex];
  return {
    ...workflow,
    status: "running",
    current_node,
    current_node_label,
    progress_percent: Math.min(96, Math.round(18 + elapsedSeconds * 8)),
    updated_at: now,
    subtasks: buildSubtasks(stageIndex, "running"),
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
  options?: { onProgress?: (percent: number) => void },
): Promise<MarketingVideoUploadResult> {
  if (!file.name.toLowerCase().endsWith(".txt")) {
    throw new Error("请上传 TXT 文案文件。");
  }

  if (file.size === 0) {
    throw new Error("TXT 文件为空，请重新选择。");
  }

  if (getApiMode() === "mock") {
    options?.onProgress?.(25);
    await sleep(120);
    options?.onProgress?.(70);
    await sleep(120);
    options?.onProgress?.(100);
    return {
      upload_session_id: `upl_mock_${Date.now()}`,
      filename: file.name,
      tos_key: `video-workflows/staging/tongan/uploads/mock/${encodeURIComponent(file.name)}`,
    };
  }

  const presign = await fetchJson<MarketingVideoPresignResponse>("/api/proxy/api/marketing-video/uploads/presign", {
    method: "POST",
    body: JSON.stringify({
      customer_id: "tongan",
      company_id: "tongan",
      filename: file.name,
      content_type: file.type || "text/plain",
      task_type: "std_marketing_video",
      workflow_name: "TONGAN",
      mode: "standard",
    }),
  });

  const scriptObject = presign.objects?.find((object) => object.input_name === "script_txt") ?? presign.objects?.[0];
  const uploadUrl = scriptObject?.upload_url ?? presign.upload_url ?? presign.url;
  const uploadMethod = scriptObject?.method ?? "PUT";
  const uploadKey = scriptObject?.upload_key ?? presign.tos_key ?? presign.object_key;
  if (!uploadUrl) {
    throw new Error("上传地址缺失，请稍后重试。");
  }
  if (!presign.upload_session_id) {
    throw new Error("上传会话缺失，请稍后重试。");
  }
  if (uploadMethod.toUpperCase() !== "PUT") {
    throw new Error(`不支持的上传方法：${uploadMethod}`);
  }
  if (!uploadKey) {
    throw new Error("上传对象路径缺失，请稍后重试。");
  }

  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(uploadMethod, uploadUrl);
    xhr.setRequestHeader("Content-Type", scriptObject?.content_type || file.type || "text/plain");
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      options?.onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => reject(new Error("上传到 TOS 失败，请检查网络后重试。"));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
        return;
      }
      reject(new Error(`TOS upload failed: ${xhr.status}`));
    };
    xhr.send(file);
  });

  options?.onProgress?.(100);
  return {
    upload_session_id: presign.upload_session_id,
    filename: file.name,
    tos_key: uploadKey,
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
      task_type: "std_marketing_video",
      task_type_label: "标准营销视频剪辑",
      workflow_name: "TONGAN",
      title: request.title || "TONGAN 07 staging sample",
      status: "queued",
      current_node: null,
      current_node_label: "等待调度",
      progress_percent: 8,
      created_at: now,
      updated_at: now,
      error_message: null,
      download: { available: false, final_video_url: null, task_manifest_key: null },
      subtasks: buildSubtasks(0, "queued"),
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
