import { expect, test } from "@playwright/test";

const USER = {
  id: 2,
  username: "rel0415_qa_user",
  role: "user",
  company_id: 1,
  company_name: "日标住建",
} as const;

const TASK_CENTER_ITEMS = [
  {
    id: "task_rel0415_001",
    title: "Smart Cut 成片任务",
    task_type: "smart_cut",
    status: "finished",
    current_stage: "finalize",
    progress: 100,
    updated_at: "2026-04-18T10:00:00Z",
    created_at: "2026-04-18T09:00:00Z",
    download_url: "https://example.com/download/final.mp4",
    input_files: ["source_video.mp4", "reference.txt"],
    output_files: ["final.mp4"],
    user_id: USER.username,
  },
  {
    id: "task_rel0415_002",
    title: "TTS 音频生成",
    task_type: "tts",
    status: "running",
    current_stage: "generate",
    progress: 60,
    updated_at: "2026-04-18T10:05:00Z",
    created_at: "2026-04-18T09:30:00Z",
    input_files: ["tts_script.txt"],
    output_files: [],
    user_id: USER.username,
  },
] as const;

const SMART_CUT_TASKS = [
  {
    id: "smartcut_rel0415_001",
    user_id: USER.username,
    status: "waiting_user",
    current_stage: "preview",
    active_edit_id: "edit_rel0415_001",
    created_at: "2026-04-18T08:00:00Z",
    updated_at: "2026-04-18T10:10:00Z",
  },
] as const;

test.beforeEach(async ({ page }) => {
  await page.route("**/api/proxy/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ user: USER }),
    });
  });

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
      body: JSON.stringify(TASK_CENTER_ITEMS),
    });
  });

  await page.route("**/api/proxy/user/tts/generate", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        audio_base64: Buffer.from("rel0415-audio").toString("base64"),
        mime_type: "audio/mpeg",
        file_name: "rel0415-output.mp3",
        usage_credits: 24,
        usage_characters: 24,
      }),
    });
  });

  await page.route(/\/api\/proxy\/api\/smart-cut\/tasks(\?.*)?$/, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            task_id: "smartcut_rel0415_001",
          },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SMART_CUT_TASKS),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_rel0415_001", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "smartcut_rel0415_001",
        user_id: USER.username,
        status: "waiting_user",
        current_stage: "preview",
        error_stage: null,
        error_message: null,
        original_video_url: null,
        original_video_tos_key: "smart-cut/smartcut_rel0415_001/input/source_video.mp4",
        reference_text_url: null,
        reference_text_tos_key: "smart-cut/smartcut_rel0415_001/input/reference.txt",
        analyze_script: "今天我们{先删掉这句}继续讲重点。",
        analyze_script_tos_key: "smart-cut/smartcut_rel0415_001/analyze/script.txt",
        asr_result_tos_key: "smart-cut/smartcut_rel0415_001/analyze/asr.json",
        active_edit_id: "edit_rel0415_001",
        finalize_source_edit_id: "edit_rel0415_001",
        final_video_url: null,
        final_video_tos_key: null,
        groundtruth_url: null,
        groundtruth_tos_key: null,
        feed_to_ai: true,
        output_mode: "original",
        last_scheduler_task_id: "sched_rel0415_001",
        created_at: "2026-04-18T08:00:00Z",
        updated_at: "2026-04-18T10:10:00Z",
      }),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_rel0415_001/edits", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "edit_rel0415_001",
          task_id: "smartcut_rel0415_001",
          edited_script: "今天我们{先删掉这句}继续讲重点。",
          status: "success",
          audio_b_url: "https://example.com/audio_b.mp3",
          audio_b_tos_key: "smart-cut/smartcut_rel0415_001/preview/edit_rel0415_001/audio_b.mp3",
          edited_delay_cuts_tos_key: "smart-cut/smartcut_rel0415_001/preview/edit_rel0415_001/edited_delay_cuts.json",
          pause_cuts_on_original_tos_key: "smart-cut/smartcut_rel0415_001/preview/edit_rel0415_001/pause_cuts_on_original.json",
          error_message: null,
          created_at: "2026-04-18T08:20:00Z",
          updated_at: "2026-04-18T08:30:00Z",
        },
      ]),
    });
  });
});

test("rel0415 user can navigate login welcome tts smart-cut and tasks", async ({ page }) => {
  await page.goto("/login");

  await page.getByLabel("用户名").fill(USER.username);
  await page.getByLabel("密码").fill("123456");
  await page.getByRole("button", { name: "登录" }).click();

  await expect(page).toHaveURL(/\/welcome$/);
  await expect(page.getByText("请点击左侧「文案生成语音」开始使用")).toBeVisible();
  await expect(page.getByRole("button", { name: "文案生成语音" })).toBeVisible();
  await expect(page.getByRole("button", { name: "视频剪辑" })).toBeVisible();
  await expect(page.getByRole("button", { name: "任务列表" })).toBeVisible();

  await page.getByRole("button", { name: "文案生成语音" }).click();
  await expect(page).toHaveURL(/\/tts$/);
  await expect(page.getByRole("heading", { name: "把文案直接转成音频" })).toBeVisible();

  await page.locator("#tts-text").fill("这是 rel0415 的定向导航验收文案。");
  await page.getByRole("button", { name: "生成音频" }).click();
  await expect(page.getByText("rel0415-output.mp3")).toBeVisible();
  await expect(page.getByRole("button", { name: "下载音频" })).toBeVisible();

  await page.getByRole("button", { name: "视频剪辑" }).click();
  await expect(page).toHaveURL(/\/smart-cut\/smartcut_rel0415_001$/);
  await expect(page.getByRole("heading", { name: "上传与分析" })).toBeVisible();
  await expect(page.getByRole("button", { name: "生成试听" })).toBeVisible();

  await page.getByRole("button", { name: "任务列表" }).click();
  await expect(page).toHaveURL(/\/tasks$/);
  await expect(page.getByRole("heading", { name: "任务列表" })).toBeVisible();
  await expect(page.getByText("task_rel0415_001")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Smart Cut 成片任务" })).toBeVisible();
  await expect(page.getByText("final.mp4")).toBeVisible();
  await expect(page.getByRole("link", { name: "下载结果" })).toBeVisible();
});
