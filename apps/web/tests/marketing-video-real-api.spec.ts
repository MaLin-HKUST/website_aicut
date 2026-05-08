import { expect, test } from "@playwright/test";

const USER = {
  username: "marketing_video_real_user",
  role: "user",
  company_id: 1,
  company_name: "通安样例公司",
} as const;

const WORKFLOW_ID = "wf_stage6b_real_contract";
const UPLOAD_KEY = "video-workflows/staging/tongan/uploads/upl_stage6b/script_txt/07.txt";
const FINAL_VIDEO_URL = "https://example.com/stage6b/final/b_video.mp4";

function workflowDetail(status: "running" | "succeeded") {
  return {
    workflow_id: WORKFLOW_ID,
    customer_id: "tongan",
    company_id: "tongan",
    task_type: "std_marketing_video",
    task_type_label: "标准营销视频剪辑",
    workflow_name: "TONGAN",
    title: "07",
    status,
    status_label: status === "succeeded" ? "已完成" : "生成中",
    current_node: status === "succeeded" ? null : "tongan_legacy_run",
    current_node_label: status === "succeeded" ? "已完成" : "TONGAN 全量生成",
    progress_percent: status === "succeeded" ? 100 : 5,
    created_at: "2026-05-08T10:00:00+00:00",
    updated_at: "2026-05-08T10:00:05+00:00",
    error_message: null,
    download: {
      available: status === "succeeded",
      final_video_url: status === "succeeded" ? FINAL_VIDEO_URL : null,
      task_manifest_key:
        status === "succeeded"
          ? `video-workflows/staging/tongan/${WORKFLOW_ID}/final/task_manifest.json`
          : null,
    },
    subtasks: [
      {
        subtask_id: "st_stage6b_real_contract",
        node_code: "tongan_legacy_run",
        node_name: "TONGAN 全量生成",
        worker_kind: "general",
        status: status === "succeeded" ? "succeeded" : "accepted",
        attempt: 1,
        progress_percent: status === "succeeded" ? 100 : 0,
        error_message: null,
      },
    ],
  };
}

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

test("real mode parses nested Stage 5B presign, uploads, creates, polls, and downloads", async ({ page }) => {
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
        upload_session_id: "upl_stage6b",
        status: "created",
        placeholder: false,
        objects: [
          {
            input_name: "script_txt",
            upload_key: UPLOAD_KEY,
            upload_url: "/mock-tos/stage6b/07.txt",
            content_type: "text/plain",
            method: "PUT",
          },
        ],
      }),
    });
  });

  await page.route("**/mock-tos/stage6b/07.txt", async (route) => {
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
      upload_session_id: "upl_stage6b",
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
  await expect(page.getByText("TONGAN 全量生成").first()).toBeVisible();
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

test("real mode displays Stage 5B nested API error messages", async ({ page }) => {
  await page.route("**/api/proxy/api/marketing-video/uploads/presign", async (route) => {
    await route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "unsupported_stage5b_mode",
          message: "RBZJ/KDT IP mode is not enabled in Stage 5B.",
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

  await expect(page.getByText("RBZJ/KDT IP mode is not enabled in Stage 5B.")).toBeVisible();
});

test("live Stage 5B browser smoke creates a real TONGAN workflow through the proxy", async ({ page }) => {
  test.skip(process.env.RUN_STAGE6B_LIVE_SMOKE !== "1", "Set RUN_STAGE6B_LIVE_SMOKE=1 to create a real Stage 5B workflow.");
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
    buffer: Buffer.from("TONGAN stage 6B live browser smoke script"),
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
