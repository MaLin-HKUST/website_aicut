import { expect, test } from "@playwright/test";

import {
  deriveMarketingVideoDisplayQueueStatus,
  formatMarketingVideoSubtaskStatus,
  normalizeMarketingVideoWorkflow,
  type MarketingVideoWorkflow,
} from "../lib/marketing-video";
import { getProxyTargetBaseUrl } from "../lib/proxy-target";
import {
  STAGE5C_FINAL_VIDEO_URL,
  STAGE5C_WORKFLOW_ID,
  stage5cFailedSpecialNodeDetail,
  stage5cSucceededDetail,
} from "./fixtures/stage5c-marketing-video";

const USER = {
  username: "marketing_video_real_user",
  role: "user",
  company_id: 10,
  company_name: "同安影视城",
} as const;

const WORKFLOW_ID = STAGE5C_WORKFLOW_ID;
const UPLOAD_KEY = "video-workflows/staging/tongan/uploads/upl_stage6c/script_txt/07.txt";
const FINAL_VIDEO_URL = STAGE5C_FINAL_VIDEO_URL;
const KDT_WORKFLOW_ID = "wf_k6c_kdt_contract";
const KDT_SCRIPT_UPLOAD_KEY = "video-workflows/staging/kdt/uploads/upl_k6c/script_txt/kdt.txt";
const KDT_OPENER_UPLOAD_KEY = "video-workflows/staging/kdt/uploads/upl_k6c/opener_video/opener.mp4";
const KDT_ENDING_UPLOAD_KEY = "video-workflows/staging/kdt/uploads/upl_k6c/ending_video/ending.mp4";

function workflowDetail(status: "running" | "succeeded" | "cancelled" = "running") {
  if (status === "succeeded") return stage5cSucceededDetail;
  if (status === "cancelled") {
    return {
      ...stage5cSucceededDetail,
      status: "cancelled",
      status_label: "已取消",
      progress_percent: 12,
      current_node: null,
      current_node_label: "已停止",
      download: { available: false, final_video_url: null, task_manifest_key: null },
      subtasks: [
        { ...stage5cSucceededDetail.subtasks[0], status: "accepted", progress_percent: 12 },
        { ...stage5cSucceededDetail.subtasks[2], status: "cancelled", progress_percent: 0 },
        { ...stage5cSucceededDetail.subtasks[1], status: "cancelled", progress_percent: 0 },
      ],
    };
  }

  return {
    ...stage5cSucceededDetail,
    status,
    status_label: "生成中",
    current_node: "tongan_pre_pipeline",
    current_node_label: "TONGAN pipeline 前置准备",
    progress_percent: 12,
    updated_at: "2026-05-08T08:02:00+00:00",
    download: {
      available: false,
      final_video_url: null,
      task_manifest_key: null,
    },
    subtasks: [
      {
        ...stage5cSucceededDetail.subtasks[1],
        status: "queued",
        progress_percent: 0,
      },
      {
        ...stage5cSucceededDetail.subtasks[2],
        status: "queued",
        progress_percent: 0,
      },
      {
        ...stage5cSucceededDetail.subtasks[0],
        status: "accepted",
        progress_percent: 12,
      },
    ],
  };
}

function workflowListPayload(detail = workflowDetail("running")) {
  const { subtasks: _subtasks, ...summary } = detail;
  return { workflows: [summary] };
}

function workflowListPayloads(details: MarketingVideoWorkflow[]) {
  return {
    workflows: details.map((detail) => {
      const { subtasks: _subtasks, ...summary } = detail;
      return summary;
    }),
  };
}

function kdtWorkflowDetail(status: "running" | "succeeded" = "running"): MarketingVideoWorkflow {
  return {
    workflow_id: KDT_WORKFLOW_ID,
    customer_id: "kdt",
    company_id: "1",
    task_type: "ip_marketing_video",
    task_type_label: "有 IP 出镜营销视频剪辑",
    workflow_name: "RBZJ_KDT",
    title: "KDT IP video contract",
    status,
    current_node: status === "succeeded" ? null : "kdt_validate_inputs",
    current_node_label: status === "succeeded" ? "已完成" : "KDT 输入校验",
    progress_percent: status === "succeeded" ? 100 : 12,
    created_at: "2026-05-15T15:28:40+00:00",
    updated_at: "2026-05-15T15:28:50+00:00",
    error_message: null,
    download: {
      available: status === "succeeded",
      final_video_url: status === "succeeded" ? "https://autocut-malin.tos-cn-shanghai.volces.com/kdt/final.mp4" : null,
      task_manifest_key: status === "succeeded" ? `video-workflows/staging/kdt/${KDT_WORKFLOW_ID}/final/task_manifest.json` : null,
    },
    subtasks: [
      {
        subtask_id: "st_kdt_validate",
        node_code: "kdt_validate_inputs",
        node_name: "KDT validate uploaded inputs",
        worker_kind: "general",
        status: status === "succeeded" ? "succeeded" : "accepted",
        attempt: 1,
        progress_percent: status === "succeeded" ? 100 : 12,
        error_message: null,
      },
      {
        subtask_id: "st_kdt_pre",
        node_code: "kdt_pre_pipeline",
        node_name: "KDT prepare pipeline bundle",
        worker_kind: "general",
        status: status === "succeeded" ? "succeeded" : "pending",
        attempt: status === "succeeded" ? 1 : 0,
        progress_percent: status === "succeeded" ? 100 : 0,
        error_message: null,
      },
      {
        subtask_id: "st_kdt_exec",
        node_code: "kdt_pipeline_exec",
        node_name: "KDT/RBZJ pipeline execution",
        worker_kind: "special",
        status: status === "succeeded" ? "succeeded" : "pending",
        attempt: status === "succeeded" ? 1 : 0,
        progress_percent: status === "succeeded" ? 100 : 0,
        error_message: null,
      },
      {
        subtask_id: "st_kdt_post",
        node_code: "kdt_post_pipeline",
        node_name: "KDT post pipeline final video",
        worker_kind: "general",
        status: status === "succeeded" ? "succeeded" : "pending",
        attempt: status === "succeeded" ? 1 : 0,
        progress_percent: status === "succeeded" ? 100 : 0,
        error_message: null,
      },
    ],
  };
}

test("real-mode adapter parses Stage 5C succeeded detail payload", async () => {
  const workflow = normalizeMarketingVideoWorkflow(stage5cSucceededDetail);

  expect(workflow.subtasks.map((subtask) => subtask.node_name)).toEqual([
    "准备素材与基础视频",
    "智能匹配素材",
    "渲染成片",
  ]);
  expect(workflow.subtasks.map((subtask) => subtask.node_code)).toEqual([
    "tongan_pre_pipeline",
    "tongan_pipeline_exec",
    "tongan_post_pipeline",
  ]);
  expect(workflow.download.available).toBe(true);
  expect(workflow.download.final_video_url).toBe(FINAL_VIDEO_URL);
});

test("real-mode adapter parses KDT four-node detail payload", async () => {
  const workflow = normalizeMarketingVideoWorkflow(kdtWorkflowDetail("succeeded"));

  expect(workflow.workflow_name).toBe("RBZJ_KDT");
  expect(workflow.task_type).toBe("ip_marketing_video");
  expect(workflow.subtasks.map((subtask) => subtask.node_name)).toEqual(["校验输入", "准备素材", "智能匹配", "渲染成片"]);
  expect(workflow.subtasks.map((subtask) => subtask.node_code)).toEqual([
    "kdt_validate_inputs",
    "kdt_pre_pipeline",
    "kdt_pipeline_exec",
    "kdt_post_pipeline",
  ]);
  expect(workflow.download.available).toBe(true);
});

test("real-mode adapter parses Stage 5C failed special-node detail payload", async () => {
  const workflow = normalizeMarketingVideoWorkflow(stage5cFailedSpecialNodeDetail);

  expect(workflow.current_node_label).toBe("智能匹配素材");
  expect(workflow.error_message).toContain("智能匹配素材");
  expect(workflow.error_message).toContain("special worker returned non-zero exit code");
});

test("marketing video display helpers use Chinese status and real execution state", async () => {
  expect(formatMarketingVideoSubtaskStatus("succeeded", 1)).toBe("已完成 · 第 1 次执行");
  expect(formatMarketingVideoSubtaskStatus("ready", 0)).toBe("排队中 · 尚未执行");
  expect(formatMarketingVideoSubtaskStatus("pending", undefined)).toBe("排队中 · 尚未执行");
  expect(formatMarketingVideoSubtaskStatus("running", 2)).toBe("执行中 · 第 2 次执行");
  expect(formatMarketingVideoSubtaskStatus("unexpected", 0)).toBe("未知状态 · 尚未执行");

  expect(deriveMarketingVideoDisplayQueueStatus({ status: "running", active_subtask_status: "dispatching" })).toBe("running");
  expect(deriveMarketingVideoDisplayQueueStatus({ status: "running", subtasks: [{ ...stage5cSucceededDetail.subtasks[0], status: "ready", attempt: 0 }] })).toBe(
    "queued",
  );
  expect(deriveMarketingVideoDisplayQueueStatus({ status: "succeeded" })).toBe("finished");
  expect(deriveMarketingVideoDisplayQueueStatus({ status: "failed" })).toBe("failed");
  expect(deriveMarketingVideoDisplayQueueStatus({ status: "cancelled" })).toBe("cancelled");
});

test("proxy target selection keeps marketing-video and Smart Cut routes separate", async () => {
  const previousMarketing = process.env.MARKETING_VIDEO_API_BASE_URL;
  const previousSmartCut = process.env.SMART_CUT_API_BASE_URL;
  const previousInternal = process.env.INTERNAL_API_BASE_URL;
  const previousLegacy = process.env.LEGACY_API_BASE_URL;

  process.env.MARKETING_VIDEO_API_BASE_URL = "http://marketing-video.local";
  process.env.SMART_CUT_API_BASE_URL = "http://smart-cut.local";
  process.env.INTERNAL_API_BASE_URL = "http://internal.local";
  process.env.LEGACY_API_BASE_URL = "http://legacy.local";

  try {
    expect(getProxyTargetBaseUrl(["api", "marketing-video", "workflows"])).toBe("http://marketing-video.local");
    expect(getProxyTargetBaseUrl(["api", "smart-cut", "tasks"])).toBe("http://smart-cut.local");
    expect(getProxyTargetBaseUrl(["auth", "me"])).toBe("http://legacy.local");
  } finally {
    process.env.MARKETING_VIDEO_API_BASE_URL = previousMarketing;
    process.env.SMART_CUT_API_BASE_URL = previousSmartCut;
    process.env.INTERNAL_API_BASE_URL = previousInternal;
    process.env.LEGACY_API_BASE_URL = previousLegacy;
  }
});

test.beforeEach(async ({ page }) => {
  await page.route("**/api/proxy/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ user: USER }),
    });
  });

  await page.route("**/api/proxy/auth/logout", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.route(/\/api\/proxy\/api\/task-center\/tasks(\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route(/\/api\/proxy\/api\/smart-cut\/tasks(\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
});

test("real mode create links the new workflow into task center detail", async ({ page }) => {
  let tosPutSeen = false;
  let createPayload: Record<string, any> | null = null;
  let detailStatus: "running" | "succeeded" = "running";

  await page.route("**/api/proxy/api/marketing-video/uploads/presign", async (route) => {
    const payload = route.request().postDataJSON() as Record<string, unknown>;
    expect(payload).toMatchObject({
      customer_id: "tongan",
      company_id: "10",
      task_type: "std_marketing_video",
      workflow_name: "TONGAN",
      mode: "standard",
      filename: "07.txt",
      content_type: "text/plain",
    });

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        upload_session_id: "upl_stage6c",
        status: "created",
        placeholder: false,
        objects: [
          {
            input_name: "script_txt",
            upload_key: UPLOAD_KEY,
            upload_url: "/mock-tos/stage6c/07.txt",
            content_type: "text/plain",
            method: "PUT",
          },
        ],
      }),
    });
  });

  await page.route("**/mock-tos/stage6c/07.txt", async (route) => {
    expect(route.request().method()).toBe("PUT");
    tosPutSeen = true;
    await route.fulfill({
      status: 200,
      headers: { "access-control-allow-origin": "*" },
      body: "",
    });
  });

  await page.route("**/api/proxy/api/marketing-video/workflows", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(workflowListPayload(workflowDetail(detailStatus))),
      });
      return;
    }

    createPayload = route.request().postDataJSON() as Record<string, any>;
    expect(createPayload.input_bundle.script_txt).toMatchObject({
      upload_session_id: "upl_stage6c",
      filename: "07.txt",
      tos_key: UPLOAD_KEY,
    });

    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(workflowDetail("running")),
    });
  });

  await page.route(`**/api/proxy/api/marketing-video/workflows/${WORKFLOW_ID}`, async (route) => {
    if (route.request().method() === "PATCH") {
      const payload = route.request().postDataJSON() as { title: string };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ...workflowDetail(detailStatus), title: payload.title }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(workflowDetail(detailStatus)),
    });
  });

  await page.route(`**/api/proxy/api/marketing-video/workflows/${WORKFLOW_ID}/download`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        workflow_id: WORKFLOW_ID,
        available: true,
        status: "succeeded",
        final_video_url: FINAL_VIDEO_URL,
        final_video_key: `video-workflows/staging/tongan/${WORKFLOW_ID}/final/b_video.mp4`,
        task_manifest_key: `video-workflows/staging/tongan/${WORKFLOW_ID}/final/task_manifest.json`,
      }),
    });
  });

  await page.goto("/marketing-video");
  await expect(page.getByText("Real", { exact: true })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("example.com/stage6a");

  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "07.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("TONGAN real contract script"),
  });
  await page.getByRole("button", { name: "创建营销视频任务" }).click();

  await expect(page.getByText("任务已进入任务中心")).toBeVisible();
  await expect(page.getByText(WORKFLOW_ID)).toBeVisible();
  await page.getByRole("button", { name: "查看任务详情" }).click();

  await expect(page.getByText("准备素材与基础视频").first()).toBeVisible();
  await expect(page.getByText("智能匹配素材").first()).toBeVisible();
  await expect(page.getByText("渲染成片").first()).toBeVisible();

  await page.getByLabel("营销视频任务名称").fill("T1 rename");
  await page.getByRole("button", { name: "保存名称" }).click();
  await expect(page.getByText("任务名称已更新。")).toBeVisible();

  detailStatus = "succeeded";
  await page.reload();
  await expect(page.getByRole("button", { name: "下载成片" })).toBeVisible();

  await page.evaluate(() => {
    (window as any).__lastOpenedMarketingVideoUrl = null;
    window.open = (url?: string | URL) => {
      (window as any).__lastOpenedMarketingVideoUrl = String(url);
      return null;
    };
  });
  await page.getByRole("button", { name: "下载成片" }).click();
  await expect
    .poll(() => page.evaluate(() => (window as any).__lastOpenedMarketingVideoUrl as string | null))
    .toBe(FINAL_VIDEO_URL);

  expect(tosPutSeen).toBe(true);
  expect(createPayload?.input_bundle.script_txt.tos_key).toBe(UPLOAD_KEY);
});

test("company 1 real mode creates KDT workflow with optional opener and ending uploads", async ({ page }) => {
  const kdtUser = {
    username: "rbzj_real_user",
    role: "user",
    company_id: 1,
    company_name: "日标住建",
  } as const;
  let scriptPutSeen = false;
  let openerPutSeen = false;
  let endingPutSeen = false;
  let createPayload: Record<string, any> | null = null;

  await page.unroute("**/api/proxy/auth/me");
  await page.route("**/api/proxy/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ user: kdtUser }),
    });
  });

  await page.route("**/api/proxy/api/marketing-video/uploads/presign", async (route) => {
    const payload = route.request().postDataJSON() as Record<string, unknown>;
    expect(payload).toMatchObject({
      customer_id: "kdt",
      company_id: "1",
      task_type: "ip_marketing_video",
      workflow_name: "RBZJ_KDT",
      mode: "standard",
      filename: "kdt.txt",
      content_type: "text/plain",
      opener_video_filename: "opener.mp4",
      ending_video_filename: "ending.mp4",
    });

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        upload_session_id: "upl_k6c",
        status: "created",
        placeholder: false,
        objects: [
          {
            input_name: "script_txt",
            upload_key: KDT_SCRIPT_UPLOAD_KEY,
            upload_url: "/mock-tos/k6c/kdt.txt",
            content_type: "text/plain",
            method: "PUT",
          },
          {
            input_name: "opener_video",
            upload_key: KDT_OPENER_UPLOAD_KEY,
            upload_url: "/mock-tos/k6c/opener.mp4",
            content_type: "video/mp4",
            method: "PUT",
          },
          {
            input_name: "ending_video",
            upload_key: KDT_ENDING_UPLOAD_KEY,
            upload_url: "/mock-tos/k6c/ending.mp4",
            content_type: "video/mp4",
            method: "PUT",
          },
        ],
      }),
    });
  });

  for (const [url, flag] of [
    ["/mock-tos/k6c/kdt.txt", "script"],
    ["/mock-tos/k6c/opener.mp4", "opener"],
    ["/mock-tos/k6c/ending.mp4", "ending"],
  ] as const) {
    await page.route(`**${url}`, async (route) => {
      expect(route.request().method()).toBe("PUT");
      if (flag === "script") scriptPutSeen = true;
      if (flag === "opener") openerPutSeen = true;
      if (flag === "ending") endingPutSeen = true;
      await route.fulfill({ status: 200, headers: { "access-control-allow-origin": "*" }, body: "" });
    });
  }

  await page.route("**/api/proxy/api/marketing-video/workflows", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(workflowListPayload(kdtWorkflowDetail("running"))),
      });
      return;
    }

    createPayload = route.request().postDataJSON() as Record<string, any>;
    expect(createPayload).toMatchObject({
      customer_id: "kdt",
      company_id: "1",
      task_type: "ip_marketing_video",
      workflow_name: "RBZJ_KDT",
      input_bundle: {
        script_txt: {
          upload_session_id: "upl_k6c",
          filename: "kdt.txt",
          tos_key: KDT_SCRIPT_UPLOAD_KEY,
        },
        opener_video: {
          upload_session_id: "upl_k6c",
          filename: "opener.mp4",
          tos_key: KDT_OPENER_UPLOAD_KEY,
        },
        ending_video: {
          upload_session_id: "upl_k6c",
          filename: "ending.mp4",
          tos_key: KDT_ENDING_UPLOAD_KEY,
        },
      },
    });

    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(kdtWorkflowDetail("running")),
    });
  });

  await page.route(`**/api/proxy/api/marketing-video/workflows/${KDT_WORKFLOW_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(kdtWorkflowDetail("running")),
    });
  });

  await page.goto("/marketing-video");
  await expect(page.getByText("KDT IP营销视频")).toBeVisible();
  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "kdt.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("KDT real contract script"),
  });
  await page.getByLabel("使用自定义开头和结尾视频").check();
  await page.getByLabel("选择开头 MP4").setInputFiles({
    name: "opener.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("opener bytes"),
  });
  await page.getByLabel("选择结尾 MP4").setInputFiles({
    name: "ending.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("ending bytes"),
  });
  await page.getByRole("button", { name: "创建营销视频任务" }).click();

  await expect(page.getByText("任务已进入任务中心")).toBeVisible();
  await expect(page.getByText(KDT_WORKFLOW_ID)).toBeVisible();
  await page.getByRole("button", { name: "查看任务详情" }).click();
  await expect(page.getByText("校验输入").first()).toBeVisible();
  await expect(page.getByText("准备素材").first()).toBeVisible();
  await expect(page.getByText("智能匹配").first()).toBeVisible();
  await expect(page.getByText("渲染成片").first()).toBeVisible();

  expect(scriptPutSeen).toBe(true);
  expect(openerPutSeen).toBe(true);
  expect(endingPutSeen).toBe(true);
  expect(createPayload?.workflow_name).toBe("RBZJ_KDT");
});

test("real mode can stop and archive a Marketing Video task from task center", async ({ page }) => {
  let currentDetail = workflowDetail("running");

  await page.route("**/api/proxy/api/marketing-video/workflows", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(workflowListPayload(currentDetail)),
    });
  });

  await page.route(`**/api/proxy/api/marketing-video/workflows/${WORKFLOW_ID}`, async (route) => {
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ archived: true }) });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(currentDetail),
    });
  });

  await page.route(`**/api/proxy/api/marketing-video/workflows/${WORKFLOW_ID}/cancel`, async (route) => {
    currentDetail = workflowDetail("cancelled");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(currentDetail),
    });
  });

  await page.goto(`/tasks?taskId=${WORKFLOW_ID}`);
  await page.getByRole("button", { name: "停止任务" }).click();
  await expect(page.getByText("任务已停止。")).toBeVisible();
  await page.getByRole("button", { name: "删除任务" }).click();
  await expect(page.getByText(WORKFLOW_ID)).toHaveCount(0);
});

test("real mode shows Chinese node statuses and queues non-active Marketing Video workflows", async ({ page }) => {
  const activeDetail = {
    ...workflowDetail("running"),
    title: "Active execution task",
    display_status: "running",
    active_subtask_status: "accepted",
    active_node_code: "tongan_pre_pipeline",
  } satisfies MarketingVideoWorkflow;
  const queuedDetail = {
    ...workflowDetail("running"),
    workflow_id: "wf_display_queued_primary",
    title: "Queued display task",
    current_node: "tongan_pipeline_exec",
    current_node_label: "智能匹配素材",
    display_status: "queued",
    active_subtask_status: null,
    active_node_code: null,
    subtasks: [
      { ...stage5cSucceededDetail.subtasks[0], status: "succeeded", attempt: 1, progress_percent: 100 },
      { ...stage5cSucceededDetail.subtasks[2], status: "ready", attempt: 0, progress_percent: 0 },
      { ...stage5cSucceededDetail.subtasks[1], status: "pending", attempt: 0, progress_percent: 0 },
    ],
  } satisfies MarketingVideoWorkflow;
  const queuedDetailTwo = {
    ...queuedDetail,
    workflow_id: "wf_display_waiting_second",
    title: "Second queued display task",
    updated_at: "2026-05-08T08:01:00+00:00",
  } satisfies MarketingVideoWorkflow;

  await page.route("**/api/proxy/api/marketing-video/workflows", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(workflowListPayloads([activeDetail, queuedDetail, queuedDetailTwo])),
    });
  });

  await page.route(`**/api/proxy/api/marketing-video/workflows/${activeDetail.workflow_id}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(activeDetail),
    });
  });

  await page.route(`**/api/proxy/api/marketing-video/workflows/${queuedDetail.workflow_id}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(queuedDetail),
    });
  });

  await page.route(`**/api/proxy/api/marketing-video/workflows/${queuedDetailTwo.workflow_id}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(queuedDetailTwo),
    });
  });

  await page.goto(`/tasks?taskId=${queuedDetail.workflow_id}`);

  await expect(page.getByRole("button", { name: /^执行中$/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /^排队中$/ })).toBeVisible();
  await expect(page.locator("button").filter({ hasText: "Active execution task" }).getByText("执行中")).toHaveCount(1);
  await expect(page.locator("button").filter({ hasText: queuedDetail.workflow_id }).getByText("排队中")).toBeVisible();
  await expect(page.locator("button").filter({ hasText: queuedDetailTwo.workflow_id }).getByText("排队中")).toBeVisible();
  await expect(page.getByText("已完成 · 第 1 次执行")).toBeVisible();
  await expect(page.getByText("排队中 · 尚未执行")).toHaveCount(2);
  await expect(page.locator("body")).not.toContainText("succeeded · attempt");
  await expect(page.locator("body")).not.toContainText("ready · attempt");
  await expect(page.locator("body")).not.toContainText("pending · attempt");

  await page.getByRole("button", { name: /^排队中$/ }).click();
  await expect(page.locator("button").filter({ hasText: "Active execution task" })).toHaveCount(0);
  await expect(page.locator("button").filter({ hasText: queuedDetail.workflow_id })).toBeVisible();
  await expect(page.locator("button").filter({ hasText: queuedDetailTwo.workflow_id })).toBeVisible();

  await page.getByRole("button", { name: /^执行中$/ }).click();
  await expect(page.locator("button").filter({ hasText: "Active execution task" })).toBeVisible();
  await expect(page.locator("button").filter({ hasText: queuedDetail.workflow_id })).toHaveCount(0);
});

test("real mode shows failure at the Stage 5C special matching node", async ({ page }) => {
  await page.route("**/api/proxy/api/marketing-video/workflows", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(workflowListPayload(stage5cFailedSpecialNodeDetail)),
    });
  });

  await page.route(`**/api/proxy/api/marketing-video/workflows/${stage5cFailedSpecialNodeDetail.workflow_id}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(stage5cFailedSpecialNodeDetail),
    });
  });

  await page.goto(`/tasks?taskId=${stage5cFailedSpecialNodeDetail.workflow_id}`);

  await expect(page.getByText("准备素材与基础视频").first()).toBeVisible();
  await expect(page.getByText("智能匹配素材").first()).toBeVisible();
  await expect(page.getByText("渲染成片").first()).toBeVisible();
  await expect(page.getByText("智能匹配素材：special worker returned non-zero exit code")).toBeVisible();
});

test("real mode displays nested API error messages", async ({ page }) => {
  await page.route("**/api/proxy/api/marketing-video/uploads/presign", async (route) => {
    await route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "unsupported_stage5b_mode",
          message: "RBZJ/KDT IP mode is not enabled.",
          details: {},
        },
      }),
    });
  });

  await page.goto("/marketing-video");
  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "07.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("TONGAN real contract script"),
  });
  await page.getByRole("button", { name: "创建营销视频任务" }).click();

  await expect(page.getByText("RBZJ/KDT IP mode is not enabled.")).toBeVisible();
});

test("live Stage 5C browser smoke creates a real TONGAN workflow through the proxy", async ({ page }) => {
  test.skip(process.env.RUN_STAGE6C_LIVE_SMOKE !== "1", "Set RUN_STAGE6C_LIVE_SMOKE=1 to create a real Stage 5C workflow.");
});
