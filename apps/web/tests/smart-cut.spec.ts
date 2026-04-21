import { expect, test, type Page } from "@playwright/test";

const USER = {
  id: 2,
  username: "qa_user",
  role: "user",
  company_id: 1,
  company_name: "日标住建",
} as const;

const DRAFT_TASK = {
  id: "smartcut_mock_001",
  user_id: USER.username,
  status: "waiting_user",
  current_stage: "preview",
  error_stage: null,
  error_message: null,
  original_video_url: "/api/fake-tos/smart-cut/smartcut_mock_001/input/source_video.mp4",
  original_video_tos_key: "smart-cut/smartcut_mock_001/input/source_video.mp4",
  reference_text_url: "/api/fake-tos/smart-cut/smartcut_mock_001/input/reference.txt",
  reference_text_tos_key: "smart-cut/smartcut_mock_001/input/reference.txt",
  analyze_script: "今天我们{先删掉这句}继续讲重点。",
  analyze_script_tos_key: "smart-cut/smartcut_mock_001/analyze/script.txt",
  asr_result_tos_key: "smart-cut/smartcut_mock_001/analyze/asr.json",
  active_edit_id: "edit_mock_001",
  finalize_source_edit_id: "edit_mock_001",
  final_video_url: null,
  final_video_tos_key: null,
  groundtruth_url: null,
  groundtruth_tos_key: null,
  feed_to_ai: true,
  output_mode: "original",
  last_scheduler_task_id: "sched_mock_001",
  created_at: "2026-04-16T08:00:00Z",
  updated_at: "2026-04-16T09:00:00Z",
} as const;

async function routeBaseApis(page: Page) {
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
}

test("opening /smart-cut no longer auto-creates an empty task", async ({ page }) => {
  let createCount = 0;

  await routeBaseApis(page);

  await page.route("**/api/proxy/api/smart-cut/tasks/draft/current", async (route) => {
    await route.fulfill({
      status: 204,
      body: "",
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks", async (route) => {
    if (route.request().method() === "POST") {
      createCount += 1;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.goto("/smart-cut");
  await expect(page).toHaveURL(/\/smart-cut$/);
  await expect(page.getByText("空工作台，不自动建任务")).toBeVisible();
  await expect(page.getByText("请上传你要处理的视频和标准文案")).toBeVisible();
  expect(createCount).toBe(0);

  await page.reload();
  await expect(page).toHaveURL(/\/smart-cut$/);
  await expect(page.getByText("空工作台，不自动建任务")).toBeVisible();
  expect(createCount).toBe(0);
});

test("analyze result renders script and audio_a in the current draft workspace", async ({ page }) => {
  let createCount = 0;

  await routeBaseApis(page);

  await page.route("**/api/proxy/api/smart-cut/tasks/draft/current", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ task: DRAFT_TASK }),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks", async (route) => {
    if (route.request().method() === "POST") {
      createCount += 1;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_mock_001", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(DRAFT_TASK),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_mock_001/edits", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "edit_mock_001",
          task_id: "smartcut_mock_001",
          edited_script: "今天我们{先删掉这句}继续讲重点。",
          status: "success",
          audio_a_url: "https://example.com/audio_a.mp3",
          audio_b_url: null,
          audio_b_tos_key: null,
          edited_delay_cuts_tos_key: null,
          pause_cuts_on_original_tos_key: null,
          error_message: null,
          created_at: "2026-04-16T08:20:00Z",
          updated_at: "2026-04-16T08:30:00Z",
        },
      ]),
    });
  });

  await page.goto("/smart-cut");
  await expect(page).toHaveURL(/\/smart-cut$/);
  await expect(page.getByRole("heading", { name: "删除线脚本调整" })).toBeVisible();
  await expect(page.getByText("分析完成，可调整删除线")).toBeVisible();
  await expect(page.getByText("分析音频 audio_a")).toBeVisible();
  await expect(page.locator("audio")).toHaveAttribute("src", "https://example.com/audio_a.mp3");
  expect(createCount).toBe(0);
});

test("preview keeps正文不可改 and renders audio_b in the current workspace", async ({ page }) => {
  let previewRequestScript = "";
  let previewSubmitted = false;

  await routeBaseApis(page);

  await page.route("**/api/proxy/api/smart-cut/tasks/draft/current", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ task: DRAFT_TASK }),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_mock_001", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...DRAFT_TASK,
        status: "waiting_user",
        current_stage: "preview",
        updated_at: previewSubmitted ? "2026-04-16T09:10:00Z" : DRAFT_TASK.updated_at,
      }),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_mock_001/edits", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        previewSubmitted
          ? {
              id: "edit_mock_002",
              task_id: "smartcut_mock_001",
              edited_script: previewRequestScript,
              status: "success",
              audio_a_url: "https://example.com/audio_a.mp3",
              audio_b_url: "https://example.com/audio_b.mp3",
              audio_b_tos_key: "smart-cut/smartcut_mock_001/preview/edit_mock_002/audio_b.mp3",
              edited_delay_cuts_tos_key: "smart-cut/smartcut_mock_001/preview/edit_mock_002/edited_delay_cuts.json",
              pause_cuts_on_original_tos_key: "smart-cut/smartcut_mock_001/preview/edit_mock_002/pause_cuts_on_original.json",
              error_message: null,
              created_at: "2026-04-16T08:40:00Z",
              updated_at: "2026-04-16T08:42:00Z",
            }
          : {
              id: "edit_mock_001",
              task_id: "smartcut_mock_001",
              edited_script: "今天我们{先删掉这句}继续讲重点。",
              status: "success",
              audio_a_url: "https://example.com/audio_a.mp3",
              audio_b_url: null,
              audio_b_tos_key: null,
              edited_delay_cuts_tos_key: null,
              pause_cuts_on_original_tos_key: null,
              error_message: null,
              created_at: "2026-04-16T08:20:00Z",
              updated_at: "2026-04-16T08:30:00Z",
            },
      ]),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_mock_001/preview", async (route) => {
    const payload = route.request().postDataJSON() as { edited_script: string };
    previewRequestScript = payload.edited_script;
    previewSubmitted = true;
    await new Promise((resolve) => setTimeout(resolve, 150));
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        edit_id: "edit_mock_002",
        scheduler_task_id: "sched_preview_001",
        status: "previewing",
      }),
    });
  });

  await page.goto("/smart-cut");
  await expect(page.getByRole("heading", { name: "删除线脚本调整" })).toBeVisible();
  await expect(page.locator("textarea")).toHaveCount(0);
  await expect(page.locator('[contenteditable="true"]')).toHaveCount(0);
  await page.getByRole("button", { name: "开始生成试听" }).click();

  await expect(page.getByText("正在生成试听")).toBeVisible();
  await expect.poll(() => previewRequestScript).toBe("今天我们{先删掉这句}继续讲重点。");
  await expect(page.getByText("试听音频 audio_b")).toBeVisible();
  await expect(page.locator("audio")).toHaveAttribute("src", "https://example.com/audio_b.mp3");
});

test("finalize promotes the task and resets the workspace to idle", async ({ page }) => {
  let finalizePayload: { output_mode: string; feed_to_ai: boolean } | null = null;

  await routeBaseApis(page);

  await page.route("**/api/proxy/api/smart-cut/tasks/draft/current", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ task: DRAFT_TASK }),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_mock_001", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(DRAFT_TASK),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_mock_001/edits", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "edit_mock_002",
          task_id: "smartcut_mock_001",
          edited_script: "今天我们{先删掉这句}{继续}讲重点。",
          status: "success",
          audio_a_url: "https://example.com/audio_a.mp3",
          audio_b_url: "https://example.com/audio_b.mp3",
          audio_b_tos_key: "smart-cut/smartcut_mock_001/preview/edit_mock_002/audio_b.mp3",
          edited_delay_cuts_tos_key: "smart-cut/smartcut_mock_001/preview/edit_mock_002/edited_delay_cuts.json",
          pause_cuts_on_original_tos_key: "smart-cut/smartcut_mock_001/preview/edit_mock_002/pause_cuts_on_original.json",
          error_message: null,
          created_at: "2026-04-16T08:40:00Z",
          updated_at: "2026-04-16T08:42:00Z",
        },
      ]),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_mock_001/finalize", async (route) => {
    finalizePayload = route.request().postDataJSON() as { output_mode: string; feed_to_ai: boolean };
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        scheduler_task_id: "sched_finalize_001",
        status: "finalizing",
        visible_in_task_center: true,
        task_title: "智能剪气口-20260421-233000",
      }),
    });
  });

  await page.goto("/smart-cut");
  await expect(page.getByText("试听音频 audio_b")).toBeVisible();

  await page.getByLabel("1080P竖屏高清").check();
  await page.getByLabel("投喂本文案给 AI").uncheck();
  await page.getByRole("button", { name: "开始生成视频" }).click();

  await expect.poll(() => finalizePayload).toEqual({
    output_mode: "vertical_1080p",
    feed_to_ai: false,
  });
  await expect(page).toHaveURL(/\/smart-cut$/);
  await expect(page.getByText("任务已转入任务列表")).toBeVisible();
  await expect(page.getByText("智能剪气口-20260421-233000 已升格为正式任务")).toBeVisible();
  await expect(page.getByText("空工作台，不自动建任务")).toBeVisible();
  await expect(page.getByText("还没有生成音频")).toBeVisible();
});
