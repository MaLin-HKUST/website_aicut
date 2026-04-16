export type SmartCutTask = {
  id: string;
  user_id: number;
  status: string;
  current_stage: string | null;
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
  audio_b_url: string | null;
  audio_b_tos_key: string | null;
  edited_delay_cuts_tos_key: string | null;
  pause_cuts_on_original_tos_key: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type DeleteRange = { start: number; end: number };

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
