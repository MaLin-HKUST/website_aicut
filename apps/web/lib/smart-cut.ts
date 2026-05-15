export type SmartCutTask = {
  id: string;
  user_id: string;
  company_id: number | null;
  status: string;
  current_stage: string | null;
  task_title: string | null;
  visible_in_task_center: boolean;
  session_scope_id: string | null;
  current_run_id: string | null;
  latest_successful_run_id: string | null;
  failed_stage: string | null;
  revision_count: number;
  original_video_url: string | null;
  reference_text_url: string | null;
  analyze_script: string | null;
  asr_result_tos_key: string | null;
  active_edit_id: string | null;
  audio_b_url: string | null;
  final_video_url: string | null;
  subtitle_srt_url: string | null;
  groundtruth_url: string | null;
  error_message: string | null;
  status_detail: string | null;
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
  edited_delay_cuts_tos_key: string | null;
  pause_cuts_on_original_tos_key: string | null;
  error_message: string | null;
  version_number: number;
  created_at: string;
  updated_at: string;
};

export type SmartCutTaskRun = {
  id: string;
  task_id: string;
  run_type: string;
  status: string;
  sequence_number: number;
  scheduler_task_id: string | null;
  source_edit_id: string | null;
  payload_snapshot: unknown;
  result_snapshot: unknown;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
};

export type SmartCutTaskSummary = {
  id: string;
  company_id: number | null;
  status: string;
  current_stage: string | null;
  status_detail: string | null;
  active_edit_id: string | null;
  created_at: string;
  updated_at: string;
};

export const SMART_CUT_AUTO_RESUME_STATUSES = new Set([
  "waiting_upload",
  "ready_analyze",
  "analyzing",
  "waiting_user",
  "previewing",
  "finalizing",
  "analyze_failed",
  "preview_failed",
  "finalize_failed",
]);

const SMART_CUT_PREVIEW_AVAILABLE_STATUSES = new Set([
  "waiting_user",
  "preview_failed",
  "success",
]);

const SMART_CUT_FINALIZE_AVAILABLE_STATUSES = new Set([
  "waiting_user",
  "success",
]);

const SMART_CUT_DELETABLE_STATUSES = new Set([
  "analyze_failed",
  "preview_failed",
  "finalize_failed",
]);

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
    return value
      .map((segment) => {
        if (typeof segment === "string") return segment;
        if (segment && typeof segment === "object" && "text" in segment) {
          return String((segment as { text?: unknown }).text ?? "");
        }
        return "";
      })
      .join("");
  }
  if (typeof value === "object" && value && Array.isArray((value as { segments?: unknown[] }).segments)) {
    return (value as { segments: unknown[] }).segments
      .map((segment) => {
        if (typeof segment === "string") return segment;
        if (segment && typeof segment === "object" && "text" in segment) {
          return String((segment as { text?: unknown }).text ?? "");
        }
        return "";
      })
      .join("");
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
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
  const merged = mergeRanges(ranges);
  let cursor = 0;
  let output = "";
  for (const range of merged) {
    output += visibleText.slice(cursor, range.start);
    output += `{${visibleText.slice(range.start, range.end)}}`;
    cursor = range.end;
  }
  output += visibleText.slice(cursor);
  return output;
}

export function rangeContainsIndex(ranges: DeleteRange[], index: number): boolean {
  return ranges.some((range) => index >= range.start && index < range.end);
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
    const payload = (await response.json().catch(() => null)) as { detail?: unknown; message?: unknown } | null;
    throw new Error(formatApiError(payload) ?? `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function formatApiError(payload: unknown): string | null {
  if (payload == null) return null;
  if (typeof payload === "string") return payload;
  if (typeof payload !== "object") return String(payload);

  const record = payload as Record<string, unknown>;
  for (const key of ["message", "detail", "error"]) {
    const message = formatApiError(record[key]);
    if (message) return message;
  }

  try {
    return JSON.stringify(payload);
  } catch {
    return String(payload);
  }
}

function normalizeTask(payload: any): SmartCutTask {
  return {
    id: payload.id,
    user_id: payload.user_id,
    company_id: payload.company_id ?? null,
    status: payload.status,
    current_stage: payload.current_stage ?? null,
    task_title: payload.task_title ?? null,
    visible_in_task_center: payload.visible_in_task_center ?? false,
    session_scope_id: payload.session_scope_id ?? null,
    current_run_id: payload.current_run_id ?? null,
    latest_successful_run_id: payload.latest_successful_run_id ?? null,
    failed_stage: payload.failed_stage ?? null,
    revision_count: payload.revision_count ?? 0,
    original_video_url: resolveTosUrl(payload.original_video_url ?? null),
    reference_text_url: resolveTosUrl(payload.reference_text_url ?? null),
    analyze_script: toScriptText(payload.current_edited_script ?? payload.analyze_script),
    asr_result_tos_key: payload.asr_result_tos_key ?? null,
    active_edit_id: payload.active_edit_id ?? null,
    audio_b_url: resolveTosUrl(payload.audio_b_url ?? null),
    final_video_url: resolveTosUrl(payload.final_video_url ?? null),
    subtitle_srt_url: resolveTosUrl(payload.subtitle_srt_url ?? null),
    groundtruth_url: resolveTosUrl(payload.groundtruth_url ?? null),
    error_message: payload.error_message ?? null,
    status_detail: payload.status_detail ?? null,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
  };
}

export function getSmartCutSubtitleDownloadUrl(
  task: Pick<SmartCutTask, "subtitle_srt_url" | "final_video_url"> | null | undefined,
): string | null {
  if (!task) return null;
  if (task.subtitle_srt_url) return task.subtitle_srt_url;
  if (!task.final_video_url) return null;

  const baseUrl = task.final_video_url.split("#")[0]?.split("?")[0] ?? "";
  if (!/\.mp4$/i.test(baseUrl)) return null;
  return baseUrl.replace(/\.mp4$/i, ".srt");
}

function normalizeEdit(payload: any): SmartCutEdit {
  return {
    id: payload.id,
    task_id: payload.task_id,
    edited_script: toScriptText(payload.edited_script) ?? "",
    status: payload.status,
    audio_a_url: resolveTosUrl(payload.audio_a_url ?? null),
    audio_b_url: resolveTosUrl(payload.audio_b_url ?? null),
    edited_delay_cuts_tos_key: payload.edited_delay_cuts_tos_key ?? null,
    pause_cuts_on_original_tos_key: payload.pause_cuts_on_original_tos_key ?? null,
    error_message: payload.error_message ?? null,
    version_number: payload.version_number,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
  };
}

function normalizeRun(payload: any): SmartCutTaskRun {
  return {
    id: payload.id,
    task_id: payload.task_id,
    run_type: payload.run_type,
    status: payload.status,
    sequence_number: payload.sequence_number,
    scheduler_task_id: payload.scheduler_task_id ?? null,
    source_edit_id: payload.source_edit_id ?? null,
    payload_snapshot: payload.payload_snapshot,
    result_snapshot: payload.result_snapshot,
    error_message: payload.error_message ?? null,
    created_at: payload.created_at,
    started_at: payload.started_at ?? null,
    completed_at: payload.completed_at ?? null,
    updated_at: payload.updated_at,
  };
}

function normalizeTaskSummary(payload: any): SmartCutTaskSummary {
  return {
    id: payload.id,
    company_id: payload.company_id ?? null,
    status: payload.status,
    current_stage: payload.current_stage ?? null,
    status_detail: payload.status_detail ?? null,
    active_edit_id: payload.active_edit_id ?? null,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
  };
}

export function isSmartCutAutoResumeStatus(status?: string | null): boolean {
  return Boolean(status && SMART_CUT_AUTO_RESUME_STATUSES.has(status));
}

export function isSmartCutPreviewAvailable(status?: string | null): boolean {
  return Boolean(status && SMART_CUT_PREVIEW_AVAILABLE_STATUSES.has(status));
}

export function isSmartCutFinalizeAvailable(status?: string | null): boolean {
  return Boolean(status && SMART_CUT_FINALIZE_AVAILABLE_STATUSES.has(status));
}

export function isSmartCutDeletable(status?: string | null): boolean {
  return Boolean(status && SMART_CUT_DELETABLE_STATUSES.has(status));
}

export function getSmartCutContinueLabel(status?: string | null): "继续处理" | "继续编辑" | null {
  if (!status || status === "abandoned") return null;
  if (status === "success") return "继续编辑";
  return "继续处理";
}

export function canAccessSmartCutTask(
  task: Pick<SmartCutTask, "user_id" | "company_id">,
  user: { username: string; company_id: number | null },
): boolean {
  if (task.user_id === user.username) return true;
  if (task.company_id === null || user.company_id === null) return false;
  return task.company_id === user.company_id;
}

export async function listSmartCutTasks(opts: { userId?: string; limit?: number } = {}): Promise<SmartCutTaskSummary[]> {
  const params = new URLSearchParams();
  if (opts.userId) params.set("user_id", opts.userId);
  if (opts.limit) params.set("limit", String(opts.limit));
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const payload = await fetchJson<any[]>(`/api/proxy/api/smart-cut/tasks${query}`);
  return payload.map(normalizeTaskSummary);
}

export async function getSmartCutTask(taskId: string): Promise<SmartCutTask> {
  const payload = await fetchJson<any>(`/api/proxy/api/smart-cut/tasks/${taskId}`);
  return normalizeTask(payload);
}

export async function getSmartCutEdits(taskId: string): Promise<SmartCutEdit[]> {
  const payload = await fetchJson<any[]>(`/api/proxy/api/smart-cut/tasks/${taskId}/edits`);
  return payload.map(normalizeEdit);
}

export async function getSmartCutRuns(taskId: string): Promise<SmartCutTaskRun[]> {
  const payload = await fetchJson<any[]>(`/api/proxy/api/smart-cut/tasks/${taskId}/runs`);
  return payload.map(normalizeRun);
}

export async function startSmartCutTask(userId: string, companyId?: number | null): Promise<SmartCutTask> {
  const payload = await fetchJson<any>(`/api/proxy/api/smart-cut/tasks/start`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, company_id: companyId ?? null }),
  });
  return getSmartCutTask(payload.task_id);
}

export async function uploadDirectInputs(
  taskId: string,
  videoFile: File,
  referenceFile: File,
  options?: {
    onProgress?: (percent: number) => void;
    signal?: AbortSignal;
    autoFinalizeAfterAnalyze?: boolean;
    outputMode?: "original" | "vertical_1080p";
    feedToAi?: boolean;
  },
): Promise<SmartCutTask> {
  const videoExt = videoFile.name.split(".").pop()?.toLowerCase() ?? "mp4";
  const prepare = await fetchJson<{
    upload_session_id: string;
    video_upload_url: string;
    video_key: string;
    text_upload_url: string;
    text_key: string;
    expires_at: string;
  }>(`/api/proxy/api/smart-cut/tasks/${taskId}/upload-prepare?video_ext=${encodeURIComponent(videoExt)}`, {
    method: "POST",
  });

  const totalBytes = videoFile.size + referenceFile.size;

  async function uploadToPresignedUrl(
    url: string,
    file: File,
    offset: number,
  ): Promise<void> {
    await new Promise<void>((resolve, reject) => {
      if (options?.signal?.aborted) {
        reject(new DOMException("Upload aborted", "AbortError"));
        return;
      }
      const xhr = new XMLHttpRequest();
      const abort = () => {
        xhr.abort();
        reject(new DOMException("Upload aborted", "AbortError"));
      };
      options?.signal?.addEventListener("abort", abort, { once: true });
      xhr.open("PUT", url);
      xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable || !options?.onProgress) return;
        const loaded = offset + event.loaded;
        options.onProgress(Math.round((loaded / totalBytes) * 100));
      };
      xhr.onerror = () => {
        options?.signal?.removeEventListener("abort", abort);
        reject(new Error("上传到 TOS 失败，请检查网络后重试"));
      };
      xhr.onload = () => {
        options?.signal?.removeEventListener("abort", abort);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve();
          return;
        }
        reject(new Error(`TOS upload failed: ${xhr.status}`));
      };
      xhr.send(file);
    });
  }

  await uploadToPresignedUrl(prepare.video_upload_url, videoFile, 0);
  await uploadToPresignedUrl(prepare.text_upload_url, referenceFile, videoFile.size);

  await fetchJson(`/api/proxy/api/smart-cut/tasks/${taskId}/upload-complete`, {
    method: "POST",
    body: JSON.stringify({
      upload_session_id: prepare.upload_session_id,
      uploaded_keys: [prepare.video_key, prepare.text_key],
      auto_finalize_after_analyze: options?.autoFinalizeAfterAnalyze ?? false,
      output_mode: options?.outputMode ?? "original",
      feed_to_ai: options?.feedToAi ?? true,
    }),
  });

  options?.onProgress?.(100);
  return getSmartCutTask(taskId);
}

type AnalyzeOptions = {
  autoFinalizeAfterAnalyze?: boolean;
  outputMode?: "original" | "vertical_1080p";
  feedToAi?: boolean;
};

function toAnalyzeBody(options?: AnalyzeOptions): string {
  return JSON.stringify({
    auto_finalize_after_analyze: options?.autoFinalizeAfterAnalyze ?? false,
    output_mode: options?.outputMode ?? "original",
    feed_to_ai: options?.feedToAi ?? true,
  });
}

export async function startAnalyze(taskId: string, options?: AnalyzeOptions): Promise<SmartCutTask> {
  await fetchJson(`/api/proxy/api/smart-cut/tasks/${taskId}/analyze`, {
    method: "POST",
    body: toAnalyzeBody(options),
  });
  return getSmartCutTask(taskId);
}

export async function reconcileUpload(taskId: string, options?: AnalyzeOptions): Promise<SmartCutTask> {
  await fetchJson(`/api/proxy/api/smart-cut/tasks/${taskId}/upload-reconcile`, {
    method: "POST",
    body: toAnalyzeBody(options),
  });
  return getSmartCutTask(taskId);
}

export async function updateSmartCutTaskTitle(taskId: string, taskTitle: string): Promise<SmartCutTask> {
  const payload = await fetchJson<any>(`/api/proxy/api/smart-cut/tasks/${taskId}/title`, {
    method: "PATCH",
    body: JSON.stringify({ task_title: taskTitle }),
  });
  return normalizeTask(payload);
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
): Promise<{ schedulerTaskId: string; status: string; visibleInTaskCenter: boolean; taskTitle: string }> {
  const payload = await fetchJson<any>(`/api/proxy/api/smart-cut/tasks/${taskId}/finalize`, {
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

export async function abandonTask(taskId: string): Promise<void> {
  await fetchJson(`/api/proxy/api/smart-cut/tasks/${taskId}/abandon`, {
    method: "POST",
  });
}
