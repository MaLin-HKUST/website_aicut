import { expect, Page, test } from "@playwright/test";

const USER = {
  id: 2,
  username: "route_smoke_user",
  role: "user",
  company_id: 1,
  company_name: "日标住建",
} as const;

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
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            task_id: "smartcut_route_smoke_001",
          },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "smartcut_route_smoke_001",
          user_id: USER.username,
          status: "waiting_user",
          current_stage: "preview",
          active_edit_id: "edit_route_smoke_001",
          created_at: "2026-04-18T08:00:00Z",
          updated_at: "2026-04-18T10:10:00Z",
        },
      ]),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_route_smoke_001", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "smartcut_route_smoke_001",
        user_id: USER.username,
        status: "waiting_user",
        current_stage: "preview",
        error_stage: null,
        error_message: null,
        original_video_url: null,
        original_video_tos_key: "smart-cut/smartcut_route_smoke_001/input/source_video.mp4",
        reference_text_url: null,
        reference_text_tos_key: "smart-cut/smartcut_route_smoke_001/input/reference.txt",
        analyze_script: "今天我们{先删掉这句}继续讲重点。",
        analyze_script_tos_key: "smart-cut/smartcut_route_smoke_001/analyze/script.txt",
        asr_result_tos_key: "smart-cut/smartcut_route_smoke_001/analyze/asr.json",
        active_edit_id: "edit_route_smoke_001",
        finalize_source_edit_id: "edit_route_smoke_001",
        final_video_url: null,
        final_video_tos_key: null,
        groundtruth_url: null,
        groundtruth_tos_key: null,
        feed_to_ai: true,
        output_mode: "original",
        last_scheduler_task_id: "sched_route_smoke_001",
        created_at: "2026-04-18T08:00:00Z",
        updated_at: "2026-04-18T10:10:00Z",
      }),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_route_smoke_001/edits", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
});

const CASES: Array<{
  path: string;
  assertVisible: (page: Page) => Promise<void>;
}> = [
  {
    path: "/login",
    assertVisible: async (page) => {
      await expect(page.getByText("营销视频剪辑智能体")).toBeVisible();
    },
  },
  {
    path: "/welcome",
    assertVisible: async (page) => {
      await expect(page.getByText("请点击左侧「文案生成语音」开始使用")).toBeVisible();
    },
  },
  {
    path: "/tts",
    assertVisible: async (page) => {
      await expect(page.getByRole("heading", { name: "把文案直接转成音频" })).toBeVisible();
    },
  },
  {
    path: "/smart-cut",
    assertVisible: async (page) => {
      await expect(page).toHaveURL(/\/smart-cut\/smartcut_route_smoke_001$/);
      await expect(page.getByRole("heading", { name: "上传与分析" })).toBeVisible();
    },
  },
  {
    path: "/tasks",
    assertVisible: async (page) => {
      await expect(page.getByRole("heading", { name: "任务列表" })).toBeVisible();
    },
  },
] as const;

for (const item of CASES) {
  test(`rel0415 route loads: ${item.path}`, async ({ page }) => {
    await page.goto(item.path);
    await item.assertVisible(page);
  });
}
