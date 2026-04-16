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
};

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

export function getTaskSubtitle(task: TaskCenterItem): string {
  if (task.status === "waiting" && task.queuePosition) {
    return `Queue #${task.queuePosition}`;
  }
  if (task.status === "finished" && task.downloadUrl) {
    return "Result ready to download";
  }
  if (task.status === "failed" && task.errorMessage) {
    return task.errorMessage;
  }
  return task.currentStage;
}

export function getTimelineItems(task: TaskCenterItem): string[] {
  if (task.taskType === "smart_cut") {
    return ["Upload", "Analyze", "Preview", "Finalize"];
  }
  if (task.taskType === "tts") {
    return ["Submit", "Generate", "Review", "Export"];
  }
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

export function getMockTaskCenterItems(): TaskCenterItem[] {
  return [
    {
      id: "sc-0415-001",
      title: "Kitchen Edit Batch A",
      taskType: "smart_cut",
      status: "running",
      progress: 56,
      currentStage: "Preview render running",
      updatedAt: "2026-04-17T08:10:00+08:00",
      createdAt: "2026-04-17T07:48:00+08:00",
      inputSummary: ["source_video.mp4", "reference.txt"],
      outputSummary: ["audio_b.mp3"],
    },
    {
      id: "sc-0415-002",
      title: "Live Cut Topic A",
      taskType: "smart_cut",
      status: "waiting",
      progress: 34,
      currentStage: "Need confirm before finalize",
      updatedAt: "2026-04-17T07:58:00+08:00",
      createdAt: "2026-04-17T07:20:00+08:00",
      queuePosition: 2,
      inputSummary: ["source_video.mov", "reference.txt"],
      outputSummary: ["audio_a.mp3", "audio_b.mp3"],
    },
    {
      id: "sc-0415-003",
      title: "Parent Course Export",
      taskType: "smart_cut",
      status: "finished",
      progress: 100,
      currentStage: "Done",
      updatedAt: "2026-04-16T14:22:00+08:00",
      createdAt: "2026-04-16T13:50:00+08:00",
      downloadUrl: "/placeholder/final_video.mp4",
      inputSummary: ["source_video.mp4", "reference.txt"],
      outputSummary: ["final_video.mp4"],
    },
    {
      id: "sc-0415-004",
      title: "Bulk Transcode 08",
      taskType: "smart_cut",
      status: "failed",
      progress: 28,
      currentStage: "Preview failed",
      updatedAt: "2026-04-16T09:10:00+08:00",
      createdAt: "2026-04-16T08:55:00+08:00",
      errorMessage: "Pause cuts parse error",
      inputSummary: ["source_video.mp4", "reference.txt"],
    },
  ];
}
