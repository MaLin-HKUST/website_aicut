import { expect, test } from "@playwright/test";

import { normalizeMarketingVideoWorkflow } from "../lib/marketing-video";
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
  company_id: 1,
  company_name: "通安样例公司",
} as const;

const WORKFLOW_ID = STAGE5C_WORKFLOW_ID;
const UPLOAD_KEY = "video-workflows/staging/tongan/uploads/upl_stage6c/script_txt/07.txt";
const FINAL_VIDEO_URL = STAGE5C_FINAL_VIDEO_URL;

function workflowDetail(status: "running" | "succeeded") {
  if (status === "succeeded") {
    return {
      ...stage5cSucceededDetail,
      download: {
        ...stage5cSucceededDetail.download,
        available: false,
      },
    };
  }

  return {
    ...stage5cSucceededDetail,
    status,
    status_label: status === "succeeded" ? "已完成" : "生成中",
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

test("real-mode adapter parses Stage 5C failed special-node detail payload", async () => {
  const workflow = normalizeMarketingVideoWorkflow(stage5cFailedSpecialNodeDetail);

  expect(workflow.current_node_label).toBe("智能匹配素材");
  expect(workflow.error_message).toContain("智能匹配素材");
  expect(workflow.error_message).toContain("special worker returned non-zero exit code");
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
});

test("real mode parses nested presign, uploads, creates, shows Stage 5C nodes, polls, and downloads", async ({ page }) => {
  let tosPutSeen = false;
  let createPayload: Record<string, any> | null = null;
  let detailPolls = 0;

  await page.route("**/api/proxy/api/marketing-video/uploads/presign", async (route) => {
    const payload = route.request().postDataJSON() as Record<string, unknown>;
    expect(payload).toMatchObject({
      customer_id: "tongan",
      company_id: "tongan",
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
    expect(route.request().postData()).toBe("TONGAN real contract script");
    tosPutSeen = true;
    await route.fulfill({
      status: 200,
      headers: { "access-control-allow-origin": "*" },
      body: "",
    });
  });

  await page.route("**/api/proxy/api/marketing-video/workflows", async (route) => {
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
    detailPolls += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(workflowDetail("succeeded")),
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
  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "07.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("TONGAN real contract script"),
  });
  await page.getByRole("button", { name: "创建营销视频任务" }).click();

  await expect(page.getByText(WORKFLOW_ID)).toBeVisible();
  await expect(page.getByText("准备素材与基础视频").first()).toBeVisible();
  await expect(page.getByText("智能匹配素材").first()).toBeVisible();
  await expect(page.getByText("渲染成片").first()).toBeVisible();
  await expect(page.getByText("成片已生成")).toBeVisible({ timeout: 5000 });
  await expect(page.getByText(FINAL_VIDEO_URL)).toBeVisible();

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
  expect(detailPolls).toBeGreaterThanOrEqual(1);
});

test("real mode shows failure at the Stage 5C special matching node", async ({ page }) => {
  await page.route("**/api/proxy/api/marketing-video/uploads/presign", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        upload_session_id: "upl_stage6c_failed",
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
    await route.fulfill({
      status: 200,
      headers: { "access-control-allow-origin": "*" },
      body: "",
    });
  });

  await page.route("**/api/proxy/api/marketing-video/workflows", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(stage5cFailedSpecialNodeDetail),
    });
  });

  await page.goto("/marketing-video");
  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "07.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("TONGAN real contract script"),
  });
  await page.getByRole("button", { name: "创建营销视频任务" }).click();

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
  test.setTimeout(90_000);

  let bridgedTosPut = false;
  let livePresignPayload: string | null = null;

  await page.route("**/api/proxy/api/marketing-video/uploads/presign", async (route) => {
    livePresignPayload = route.request().postData();
    await route.continue();
  });

  await page.route(/https:\/\/.*tos.*\/video-workflows\/staging\/tongan\/uploads\/.*/, async (route) => {
    const request = route.request();
    const response = await fetch(request.url(), {
      method: request.method(),
      headers: {
        "Content-Type": request.headers()["content-type"] ?? "text/plain",
      },
      body: request.postDataBuffer(),
    });

    bridgedTosPut = response.ok;
    await route.fulfill({
      status: response.status,
      headers: { "access-control-allow-origin": "*" },
      body: await response.text(),
    });
  });

  await page.goto("/marketing-video");
  await expect(page.getByText("Real", { exact: true })).toBeVisible();

  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "07.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("TONGAN stage 6C live browser smoke script"),
  });

  const createResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/proxy/api/marketing-video/workflows") && response.request().method() === "POST",
    { timeout: 60_000 },
  );

  await page.getByRole("button", { name: "创建营销视频任务" }).click();
  const createResponse = await Promise.race([
    createResponsePromise,
    page.locator(".bg-red-50").waitFor({ state: "visible", timeout: 60_000 }).then(async () => {
      const message = await page.locator(".bg-red-50").innerText();
      throw new Error(`Live browser smoke stopped before workflow create: ${message}`);
    }),
  ]);
  if (!createResponse.ok()) {
    throw new Error(
      `Live workflow create failed ${createResponse.status()}: ${await createResponse.text()} request=${createResponse.request().postData()} presign=${livePresignPayload}`,
    );
  }
  const created = (await createResponse.json()) as { workflow_id: string };

  await expect(page.getByText(created.workflow_id)).toBeVisible();
  expect(bridgedTosPut).toBe(true);
  await page.waitForResponse(
    (response) =>
      response.url().includes(`/api/proxy/api/marketing-video/workflows/${created.workflow_id}`) &&
      response.request().method() === "GET",
    { timeout: 15_000 },
  );
});
