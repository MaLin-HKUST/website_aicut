import type { MarketingVideoWorkflow } from "../../lib/marketing-video";

export const STAGE5C_WORKFLOW_ID = "wf_0963371cc1a241e488b475f92fbf3365";
export const STAGE5C_FINAL_VIDEO_URL = "https://example.com/stage5c/wf_0963371cc1a241e488b475f92fbf3365/b_video.mp4";

export const stage5cSucceededDetail = {
  company_id: "10",
  created_at: "2026-05-08T08:01:21.871462+00:00",
  current_node: null,
  current_node_label: null,
  customer_id: "tongan",
  download: {
    available: true,
    final_video_url: STAGE5C_FINAL_VIDEO_URL,
    task_manifest_key: `video-workflows/staging/tongan/${STAGE5C_WORKFLOW_ID}/final/task_manifest.json`,
  },
  error_message: null,
  progress_percent: 100,
  status: "succeeded",
  task_type: "std_marketing_video",
  task_type_label: "标准营销视频剪辑",
  title: "TONGAN 07 staging API E2E",
  updated_at: "2026-05-08T08:35:22.567713+00:00",
  workflow_id: STAGE5C_WORKFLOW_ID,
  workflow_name: "TONGAN",
  subtasks: [
    {
      attempt: 1,
      error_message: null,
      node_code: "tongan_pre_pipeline",
      node_name: "TONGAN pipeline 前置准备",
      progress_percent: 100,
      status: "succeeded",
      subtask_id: "st_bf52238c1eb4463a9ef4094101c8a36f",
      worker_kind: "general",
    },
    {
      attempt: 5,
      error_message: null,
      node_code: "tongan_post_pipeline",
      node_name: "TONGAN Step C 渲染收尾",
      progress_percent: 100,
      status: "succeeded",
      subtask_id: "st_82baf502961a43e5b4f30138873e9dd7",
      worker_kind: "general",
    },
    {
      attempt: 1,
      error_message: null,
      node_code: "tongan_pipeline_exec",
      node_name: "TONGAN Codex pipeline 执行",
      progress_percent: 100,
      status: "succeeded",
      subtask_id: "st_8af7b4c0b5cb49fda76a602f95f19923",
      worker_kind: "special",
    },
  ],
} satisfies MarketingVideoWorkflow;

export const stage5cFailedSpecialNodeDetail = {
  ...stage5cSucceededDetail,
  current_node: "tongan_pipeline_exec",
  current_node_label: "TONGAN Codex pipeline 执行",
  download: {
    available: false,
    final_video_url: null,
    task_manifest_key: null,
  },
  error_message: "special worker returned non-zero exit code",
  progress_percent: 44,
  status: "failed",
  updated_at: "2026-05-08T08:18:00.000000+00:00",
  workflow_id: "wf_stage5c_failed_special",
  subtasks: [
    {
      ...stage5cSucceededDetail.subtasks[1],
      status: "queued",
      progress_percent: 0,
    },
    {
      ...stage5cSucceededDetail.subtasks[2],
      status: "failed",
      progress_percent: 44,
      error_message: "special worker returned non-zero exit code",
    },
    {
      ...stage5cSucceededDetail.subtasks[0],
      status: "succeeded",
      progress_percent: 100,
    },
  ],
} satisfies MarketingVideoWorkflow;
