export type TaskCenterStatus = "queued" | "running" | "waiting" | "finished" | "failed";
export type TaskCenterType = "smart_cut" | "tts" | "batch";

export type TaskCenterItem = {
  id: string;
  title: string;
  taskType: TaskCenterType;
  status: TaskCenterStatus;
  progress: number;
  currentStage: string;
  updatedAt: string;
  createdAt: string;
  queuePosition?: number | null;
  downloadUrl?: string | null;
  errorMessage?: string | null;
  inputSummary: string[];
  outputSummary?: string[];
  userId?: string | null;
  companyId?: number | null;
  schedulerTaskId?: string | null;
  schedulerStatus?: string | null;
  workerId?: string | null;
};

type TaskCenterApiItem = {
  id: string;
  title: string;
  task_type: string;
  status: TaskCenterStatus;
  current_stage: string;
  progress: number;
  progress_detail?: string | null;
  updated_at: string;
  created_at: string;
  queue_position?: number | null;
  download_url?: string | null;
  error_message?: string | null;
  input_files?: string[];
  output_files?: string[];
  user_id?: string | null;
  company_id?: number | null;
  scheduler_task_id?: string | null;
  scheduler_status?: string | null;
  worker_id?: string | null;
};

const DEFAULT_TOS_PUBLIC_BASE_URL = "https://autocut-malin.tos-cn-shanghai.volces.com";

function resolveTosUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  if (/^https?:\/\//i.test(value)) return value;
  const baseUrl = process.env.NEXT_PUBLIC_TOS_PUBLIC_BASE_URL || DEFAULT_TOS_PUBLIC_BASE_URL;
  return `${baseUrl.replace(/\/+$/, "")}/${value.replace(/^\/+/, "")}`;
}

export const STATUS_META: Record<
  TaskCenterStatus,
  {
    label: string;
    badgeClassName: string;
    progressClassName: string;
  }
> = {
  queued: {
    label: "Queued",
    badgeClassName: "border border-slate-300 bg-slate-50 text-slate-600",
    progressClassName: "bg-slate-400",
  },
  running: {
    label: "Running",
    badgeClassName: "border border-blue-300 bg-blue-50 text-blue-700",
    progressClassName: "bg-blue-500",
  },
  waiting: {
    label: "Waiting",
    badgeClassName: "border border-amber-300 bg-amber-50 text-amber-700",
    progressClassName: "bg-amber-500",
  },
  finished: {
    label: "Finished",
    badgeClassName: "border border-emerald-300 bg-emerald-50 text-emerald-700",
    progressClassName: "bg-emerald-500",
  },
  failed: {
    label: "Failed",
    badgeClassName: "border border-rose-300 bg-rose-50 text-rose-700",
    progressClassName: "bg-rose-500",
  },
};

export const FILTER_OPTIONS = [
  { key: "all", label: "All" },
  { key: "running", label: "Running" },
  { key: "waiting", label: "Waiting" },
  { key: "finished", label: "Finished" },
  { key: "failed", label: "Failed" },
] as const;

export type TaskCenterFilter = (typeof FILTER_OPTIONS)[number]["key"];

function normalizeItem(payload: TaskCenterApiItem): TaskCenterItem {
  return {
    id: payload.id,
    title: payload.title,
    taskType: payload.task_type as TaskCenterType,
    status: payload.status,
    progress: payload.progress,
    currentStage: payload.progress_detail || payload.current_stage,
    updatedAt: payload.updated_at,
    createdAt: payload.created_at,
    queuePosition: payload.queue_position ?? null,
    downloadUrl: resolveTosUrl(payload.download_url ?? null),
    errorMessage: payload.error_message ?? null,
    inputSummary: payload.input_files ?? [],
    outputSummary: payload.output_files ?? [],
    userId: payload.user_id ?? null,
    companyId: payload.company_id ?? null,
    schedulerTaskId: payload.scheduler_task_id ?? null,
    schedulerStatus: payload.scheduler_status ?? null,
    workerId: payload.worker_id ?? null,
  };
}

export function getTaskSubtitle(task: TaskCenterItem): string {
  if (task.status === "waiting" && task.queuePosition) return `Queue #${task.queuePosition}`;
  if (task.status === "finished" && task.downloadUrl) return "Result ready to download";
  if (task.status === "failed" && task.errorMessage) return task.errorMessage;
  return task.currentStage;
}

export function getTimelineItems(task: TaskCenterItem): string[] {
  if (task.taskType === "smart_cut") return ["Upload", "Analyze", "Preview", "Finalize"];
  if (task.taskType === "tts") return ["Submit", "Generate", "Review", "Export"];
  return ["Queued", "Running", "Review", "Done"];
}

export function formatUpdatedAt(value: string): string {
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

export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function listTaskCenterItems(opts: { mode: "user" | "admin"; userId?: string; companyId?: number | null }): Promise<TaskCenterItem[]> {
  const basePath =
    opts.mode === "admin" ? "/api/proxy/api/admin/task-center/tasks" : "/api/proxy/api/task-center/tasks";
  let query = "";
  if (opts.mode === "user") {
    const params = new URLSearchParams();
    if (opts.companyId != null) {
      params.set("company_id", String(opts.companyId));
    } else if (opts.userId) {
      params.set("user_id", opts.userId);
    }
    const serialized = params.toString();
    query = serialized ? `?${serialized}` : "";
  }
  const payload = await fetchJson<TaskCenterApiItem[]>(`${basePath}${query}`);
  return payload.map(normalizeItem);
}
