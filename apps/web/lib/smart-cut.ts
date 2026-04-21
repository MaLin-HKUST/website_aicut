export type SmartCutTask = {
  id: string;
  user_id: string;
  status: string;
  current_stage: string | null;
  task_title: string | null;
  visible_in_task_center: boolean;
  session_scope_id: string | null;
  error_stage: string | null;
  error_message: string | null;
  original_video_url: string | null;
  original_video_tos_key: string | null;
  reference_text_url: string | null;
  reference_text_tos_key: string | null;
  analyze_script: string | null;
  analyze_script_tos_key: string | null;
  asr_result_tos_key: string | null;
  active_edit_id: string | null;
  finalize_source_edit_id: string | null;
  final_video_url: string | null;
  final_video_tos_key: string | null;
  groundtruth_url: string | null;
  groundtruth_tos_key: string | null;
  feed_to_ai: boolean;
  output_mode: "original" | "vertical_1080p" | null;
  last_scheduler_task_id: string | null;
  created_at: string;
  updated_at: string;
};

export type SmartCutTaskSummary = {
  id: string;
  status: string;
  current_stage: string | null;
  active_edit_id: string | null;
  created_at: string;
  updated_at: string;
};

export type SmartCutEdit = {
  id: string;
  task_id: string;
  edited_script: string;
  status: string;
  audio_a_url: string | null;
  audio_b_url: string | null;
  audio_b_tos_key: string | null;
  edited_delay_cuts_tos_key: string | null;
  pause_cuts_on_original_tos_key: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

type SmartCutTaskApi = {
  id: string;
  user_id: string;
  status: string;
  current_stage: string | null;
  task_title?: string | null;
  visible_in_task_center?: boolean;
  session_scope_id?: string | null;
  original_video_url?: string | null;
  reference_text_url?: string | null;
  analyze_script?: unknown;
  asr_result_tos_key?: string | null;
  active_edit_id?: string | null;
  current_edited_script?: unknown;
  audio_b_url?: string | null;
  final_video_url?: string | null;
  groundtruth_url?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

type SmartCutEditApi = {
  id: string;
  task_id: string;
  edited_script: unknown;
  status: string;
  audio_a_url?: string | null;
  audio_b_url?: string | null;
  edited_delay_cuts_tos_key?: string | null;
  pause_cuts_on_original_tos_key?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

type TaskCreateApi = {
  id?: string;
  user_id?: string | number;
  status?: string;
  current_stage?: string | null;
  created_at?: string;
  updated_at?: string;
  data?: {
    task_id: string;
  };
};

type FinalizeResponseApi = {
  scheduler_task_id: string;
  status: string;
  visible_in_task_center: boolean;
  task_title: string;
};

type SmartCutDraftEnvelope =
  | SmartCutTaskApi
  | {
      task?: SmartCutTaskApi | null;
      data?: SmartCutTaskApi | null;
    }
  | null;

export type SmartCutDraftLookup = {
  supported: boolean;
  task: SmartCutTask | null;
};

export type SmartCutFinalizeResult = {
  schedulerTaskId: string;
  status: string;
  visibleInTaskCenter: boolean;
  taskTitle: string;
};

export type DeleteRange = { start: number; end: number };

const DEFAULT_TOS_PUBLIC_BASE_URL = "https://autocut-malin.tos-cn-shanghai.volces.com";

function resolveTosUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  if (/^https?:\/\//i.test(value)) return value;
  const baseUrl = process.env.NEXT_PUBLIC_TOS_PUBLIC_BASE_URL || DEFAULT_TOS_PUBLIC_BASE_URL;
  return `${baseUrl.replace(/\/+$/, "")}/${value.replace(/^\/+/, "")}`;
}

function toScriptText(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    const parts = value.map((segment) => {
      if (typeof segment === "string") return segment;
      if (segment && typeof segment === "object" && "text" in segment) {
        return String((segment as { text?: unknown }).text ?? "");
      }
      return "";
    });
    return parts.join("");
  }
  if (typeof value === "object" && value && Array.isArray((value as { segments?: unknown[] }).segments)) {
    const parts = (value as { segments: unknown[] }).segments.map((segment) => {
      if (typeof segment === "string") return segment;
      if (segment && typeof segment === "object" && "text" in segment) {
        return String((segment as { text?: unknown }).text ?? "");
      }
      return "";
    });
    return parts.join("");
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function normalizeTask(payload: SmartCutTaskApi): SmartCutTask {
  return {
    id: payload.id,
    user_id: payload.user_id,
    status: payload.status,
    current_stage: payload.current_stage ?? null,
    task_title: payload.task_title ?? null,
    visible_in_task_center: payload.visible_in_task_center ?? false,
    session_scope_id: payload.session_scope_id ?? null,
    error_stage: null,
    error_message: payload.error_message ?? null,
    original_video_url: resolveTosUrl(payload.original_video_url ?? null),
    original_video_tos_key: payload.original_video_url ?? null,
    reference_text_url: resolveTosUrl(payload.reference_text_url ?? null),
    reference_text_tos_key: payload.reference_text_url ?? null,
    analyze_script: toScriptText(payload.current_edited_script ?? payload.analyze_script),
    analyze_script_tos_key: null,
    asr_result_tos_key: payload.asr_result_tos_key ?? null,
    active_edit_id: payload.active_edit_id ?? null,
    finalize_source_edit_id: payload.active_edit_id ?? null,
    final_video_url: resolveTosUrl(payload.final_video_url ?? null),
    final_video_tos_key: payload.final_video_url ?? null,
    groundtruth_url: resolveTosUrl(payload.groundtruth_url ?? null),
    groundtruth_tos_key: payload.groundtruth_url ?? null,
    feed_to_ai: true,
    output_mode: "original",
    last_scheduler_task_id: null,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
  };
}

function normalizeEdit(payload: SmartCutEditApi): SmartCutEdit {
  return {
    id: payload.id,
    task_id: payload.task_id,
    edited_script: toScriptText(payload.edited_script) ?? "",
    status: payload.status,
    audio_a_url: resolveTosUrl(payload.audio_a_url ?? null),
    audio_b_url: resolveTosUrl(payload.audio_b_url ?? null),
    audio_b_tos_key: payload.audio_b_url ?? null,
    edited_delay_cuts_tos_key: payload.edited_delay_cuts_tos_key ?? null,
    pause_cuts_on_original_tos_key: payload.pause_cuts_on_original_tos_key ?? null,
    error_message: payload.error_message ?? null,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
  };
}

export function mergeRanges(ranges: DeleteRange[]): DeleteRange[] {
  const sorted = [...ranges]
    .filter((range) => range.end > range.start)
    .sort((left, right) => left.start - right.start || left.end - right.end);

  const merged: DeleteRange[] = [];
  for (const range of sorted) {
    const last = merged[merged.length - 1];
    if (!last || range.start > last.end) {
      merged.push({ ...range });
      continue;
    }
    last.end = Math.max(last.end, range.end);
  }
  return merged;
}

export function parseBraceScript(script: string): { visibleText: string; ranges: DeleteRange[] } {
  const visible: string[] = [];
  const ranges: DeleteRange[] = [];
  let depth = 0;
  let currentStart: number | null = null;

  for (const char of script) {
    if (char === "{") {
      if (depth === 0) currentStart = visible.length;
      depth += 1;
      continue;
    }
    if (char === "}") {
      if (depth > 0) {
        depth -= 1;
        if (depth === 0 && currentStart !== null) {
          ranges.push({ start: currentStart, end: visible.length });
          currentStart = null;
        }
      }
      continue;
    }
    visible.push(char);
  }

  return { visibleText: visible.join(""), ranges: mergeRanges(ranges) };
}

export function applyRangesToScript(visibleText: string, ranges: DeleteRange[]): string {
  const chars = visibleText.split("");
  const merged = mergeRanges(ranges);
  for (let index = merged.length - 1; index >= 0; index -= 1) {
    const range = merged[index];
    chars.splice(range.end, 0, "}");
    chars.splice(range.start, 0, "{");
  }
  return chars.join("");
}

export function rangeContainsIndex(ranges: DeleteRange[], index: number): boolean {
  return ranges.some((range) => index >= range.start && index < range.end);
}

export function formatTaskStatus(task: Pick<SmartCutTask, "status" | "current_stage">): string {
  const parts = [task.status];
  if (task.current_stage) parts.push(task.current_stage);
  return parts.join(" / ");
}

export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function fetchOptionalJson<T>(
  url: string,
  init?: RequestInit,
): Promise<{ supported: boolean; data: T | null }> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers ?? {}),
    },
  });

  if ([404, 405, 501].includes(response.status)) {
    return { supported: false, data: null };
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return { supported: true, data: null };
  }

  const text = await response.text();
  if (!text.trim()) {
    return { supported: true, data: null };
  }

  return { supported: true, data: JSON.parse(text) as T };
}

function unwrapDraftTask(payload: SmartCutDraftEnvelope): SmartCutTaskApi | null {
  if (!payload) return null;
  if ("id" in payload && typeof payload.id === "string") {
    return payload;
  }
  if ("task" in payload && payload.task && typeof payload.task.id === "string") {
    return payload.task;
  }
  if ("data" in payload && payload.data && typeof payload.data.id === "string") {
    return payload.data;
  }
  return null;
}

export async function listSmartCutTasks(userId?: string): Promise<SmartCutTaskSummary[]> {
  const query = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  return fetchJson<SmartCutTaskSummary[]>(`/api/proxy/api/smart-cut/tasks${query}`);
}

export async function getSmartCutTask(taskId: string): Promise<SmartCutTask> {
  const payload = await fetchJson<SmartCutTaskApi>(`/api/proxy/api/smart-cut/tasks/${taskId}`);
  return normalizeTask(payload);
}

export async function getSmartCutEdits(taskId: string): Promise<SmartCutEdit[]> {
  const payload = await fetchJson<SmartCutEditApi[]>(`/api/proxy/api/smart-cut/tasks/${taskId}/edits`);
  return payload.map(normalizeEdit);
}

export async function createSmartCutTask(userId: string): Promise<SmartCutTask> {
  const payload = await fetchJson<TaskCreateApi>("/api/proxy/api/smart-cut/tasks", {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
  const taskId = payload.data?.task_id ?? payload.id;
  if (!taskId) {
    throw new Error("Task creation did not return task_id");
  }

  if (payload.id && payload.status && payload.created_at && payload.updated_at) {
    return normalizeTask(payload as SmartCutTaskApi);
  }

  return getSmartCutTask(taskId);
}

export async function getCurrentSmartCutDraft(userId: string): Promise<SmartCutDraftLookup> {
  const query = `?user_id=${encodeURIComponent(userId)}`;
  const result = await fetchOptionalJson<SmartCutDraftEnvelope>(`/api/proxy/api/smart-cut/tasks/draft/current${query}`);
  const payload = unwrapDraftTask(result.data);
  return {
    supported: result.supported,
    task: payload ? normalizeTask(payload) : null,
  };
}

export async function ensureCurrentSmartCutDraft(userId: string): Promise<SmartCutDraftLookup> {
  const result = await fetchOptionalJson<SmartCutDraftEnvelope>("/api/proxy/api/smart-cut/tasks/draft/current/ensure", {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
  const payload = unwrapDraftTask(result.data);
  return {
    supported: result.supported,
    task: payload ? normalizeTask(payload) : null,
  };
}

type UploadDirectProgress = {
  loaded: number;
  total: number;
  percent: number;
};

type UploadPrepareApi = {
  video_upload_url: string;
  video_key: string;
  text_upload_url: string;
  text_key: string;
  expires_at: string;
};

function parseXhrPayload<T>(xhr: XMLHttpRequest): T | null {
  if (xhr.response && typeof xhr.response === "object") {
    return xhr.response as T;
  }

  if (!xhr.responseText) {
    return null;
  }

  try {
    return JSON.parse(xhr.responseText) as T;
  } catch {
    return null;
  }
}

async function uploadFileToPresignedUrl(
  url: string,
  file: File,
  options?: {
    onProgress?: (progress: UploadDirectProgress) => void;
    offset?: number;
    totalBytes?: number;
  },
): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || !options?.onProgress || !options.totalBytes) return;
      const loaded = (options.offset ?? 0) + event.loaded;
      options.onProgress({
        loaded,
        total: options.totalBytes,
        percent: Math.max(0, Math.min(100, Math.round((loaded / options.totalBytes) * 100))),
      });
    };

    xhr.onerror = () => reject(new Error("上传到 TOS 失败，请检查网络后重试"));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
        return;
      }
      reject(new Error(`TOS upload failed: ${xhr.status}`));
    };

    xhr.send(file);
  });
}

export async function uploadDirectInputs(
  taskId: string,
  videoFile: File,
  referenceFile: File,
  options?: {
    onProgress?: (progress: UploadDirectProgress) => void;
  },
): Promise<SmartCutTask> {
  const videoExt = videoFile.name.split(".").pop()?.toLowerCase() ?? "mp4";
  const prepare = await fetchJson<UploadPrepareApi>(`/api/proxy/api/smart-cut/tasks/${taskId}/upload-prepare?video_ext=${encodeURIComponent(videoExt)}`, {
    method: "POST",
  });

  const totalBytes = videoFile.size + referenceFile.size;
  await uploadFileToPresignedUrl(prepare.video_upload_url, videoFile, {
    onProgress: options?.onProgress,
    offset: 0,
    totalBytes,
  });
  await uploadFileToPresignedUrl(prepare.text_upload_url, referenceFile, {
    onProgress: options?.onProgress,
    offset: videoFile.size,
    totalBytes,
  });

  await fetchJson(`/api/proxy/api/smart-cut/tasks/${taskId}/upload-complete`, {
    method: "POST",
    body: JSON.stringify({
      uploaded_keys: [prepare.video_key, prepare.text_key],
    }),
  });

  options?.onProgress?.({
    loaded: totalBytes,
    total: totalBytes,
    percent: 100,
  });

  return getSmartCutTask(taskId);
}

export async function startAnalyze(taskId: string): Promise<SmartCutTask> {
  await fetchJson(`/api/proxy/api/smart-cut/tasks/${taskId}/analyze`, { method: "POST" });
  return getSmartCutTask(taskId);
}

export async function startPreview(taskId: string, editedScript: string): Promise<SmartCutTask> {
  await fetchJson(`/api/proxy/api/smart-cut/tasks/${taskId}/preview`, {
    method: "POST",
    body: JSON.stringify({ edited_script: editedScript }),
  });
  return getSmartCutTask(taskId);
}

export async function startFinalize(
  taskId: string,
  params: { outputMode: "original" | "vertical_1080p"; feedToAi: boolean },
): Promise<SmartCutFinalizeResult> {
  const payload = await fetchJson<FinalizeResponseApi>(`/api/proxy/api/smart-cut/tasks/${taskId}/finalize`, {
    method: "POST",
    body: JSON.stringify({ output_mode: params.outputMode, feed_to_ai: params.feedToAi }),
  });
  return {
    schedulerTaskId: payload.scheduler_task_id,
    status: payload.status,
    visibleInTaskCenter: payload.visible_in_task_center,
    taskTitle: payload.task_title,
  };
}
