import { expect, Page, test } from "@playwright/test";

const USER = {
  id: 2,
  username: "route_smoke_user",
  role: "user",
  company_id: 1,
  company_name: "日标住建",
} as const;

const SMART_CUT_DETAILS: Record<string, Record<string, unknown>> = {
  smartcut_route_smoke_001: {
    id: "smartcut_route_smoke_001",
    user_id: USER.username,
    company_id: USER.company_id,
    status: "waiting_user",
    current_stage: "preview",
    task_title: "我的待处理任务",
    error_message: null,
    original_video_url: "smart-cut/smartcut_route_smoke_001/input/source_video.mp4",
    reference_text_url: "smart-cut/smartcut_route_smoke_001/input/reference.txt",
    analyze_script: "今天我们{先删掉这句}继续讲重点。",
    asr_result_tos_key: "smart-cut/smartcut_route_smoke_001/analyze/asr.json",
    active_edit_id: "edit_route_smoke_001",
    audio_b_url: "smart-cut/smartcut_route_smoke_001/preview/edit_route_smoke_001/audio_b.mp3",
    final_video_url: null,
    groundtruth_url: null,
    created_at: "2026-04-18T08:00:00Z",
    updated_at: "2026-04-18T10:10:00Z",
  },
  smartcut_success_self_001: {
    id: "smartcut_success_self_001",
    user_id: USER.username,
    company_id: USER.company_id,
    status: "success",
    current_stage: "complete",
    task_title: "我自己的已完成任务",
    error_message: null,
    original_video_url: "smart-cut/smartcut_success_self_001/input/source_video.mp4",
    reference_text_url: "smart-cut/smartcut_success_self_001/input/reference.txt",
    analyze_script: "已完成版本。",
    asr_result_tos_key: "smart-cut/smartcut_success_self_001/analyze/asr.json",
    active_edit_id: "edit_success_self_001",
    audio_b_url: "smart-cut/smartcut_success_self_001/preview/edit_success_self_001/audio_b.mp3",
    final_video_url: "https://example.com/smartcut_success_self_001/final_video.mp4",
    groundtruth_url: null,
    created_at: "2026-04-18T07:00:00Z",
    updated_at: "2026-04-18T09:30:00Z",
  },
  smartcut_success_shared_001: {
    id: "smartcut_success_shared_001",
    user_id: "other_user",
    company_id: USER.company_id,
    status: "success",
    current_stage: "complete",
    task_title: "共享完成任务",
    error_message: null,
    original_video_url: "smart-cut/smartcut_success_shared_001/input/source_video.mp4",
    reference_text_url: "smart-cut/smartcut_success_shared_001/input/reference.txt",
    analyze_script: "共享任务成片。",
    asr_result_tos_key: "smart-cut/smartcut_success_shared_001/analyze/asr.json",
    active_edit_id: "edit_success_shared_001",
    audio_b_url: "smart-cut/smartcut_success_shared_001/preview/edit_success_shared_001/audio_b.mp3",
    final_video_url: "https://example.com/smartcut_success_shared_001/final_video.mp4",
    groundtruth_url: null,
    created_at: "2026-04-18T06:00:00Z",
    updated_at: "2026-04-18T09:00:00Z",
  },
  smartcut_analyze_failed_001: {
    id: "smartcut_analyze_failed_001",
    user_id: USER.username,
    company_id: USER.company_id,
    status: "analyze_failed",
    current_stage: "analyze",
    task_title: "分析失败任务",
    error_message: "analyze worker failed",
    original_video_url: "smart-cut/smartcut_analyze_failed_001/input/source_video.mp4",
    reference_text_url: "smart-cut/smartcut_analyze_failed_001/input/reference.txt",
    analyze_script: null,
    asr_result_tos_key: null,
    active_edit_id: null,
    audio_b_url: null,
    final_video_url: null,
    groundtruth_url: null,
    created_at: "2026-04-18T05:00:00Z",
    updated_at: "2026-04-18T08:00:00Z",
  },
};

const SMART_CUT_EDITS: Record<string, Array<Record<string, unknown>>> = {
  smartcut_route_smoke_001: [
    {
      id: "edit_route_smoke_001",
      task_id: "smartcut_route_smoke_001",
      edited_script: "今天我们{先删掉这句}继续讲重点。",
      status: "success",
      audio_a_url: "smart-cut/smartcut_route_smoke_001/analyze/audio_a.mp3",
      audio_b_url: "smart-cut/smartcut_route_smoke_001/preview/edit_route_smoke_001/audio_b.mp3",
      edited_delay_cuts_tos_key: "smart-cut/smartcut_route_smoke_001/preview/edit_route_smoke_001/edited_delay_cuts.json",
      pause_cuts_on_original_tos_key: "smart-cut/smartcut_route_smoke_001/preview/edit_route_smoke_001/pause_cuts.json",
      error_message: null,
      version_number: 1,
      created_at: "2026-04-18T09:50:00Z",
      updated_at: "2026-04-18T10:10:00Z",
    },
  ],
  smartcut_success_self_001: [
    {
      id: "edit_success_self_001",
      task_id: "smartcut_success_self_001",
      edited_script: "已完成版本。",
      status: "success",
      audio_a_url: "smart-cut/smartcut_success_self_001/analyze/audio_a.mp3",
      audio_b_url: "smart-cut/smartcut_success_self_001/preview/edit_success_self_001/audio_b.mp3",
      edited_delay_cuts_tos_key: "smart-cut/smartcut_success_self_001/preview/edit_success_self_001/edited_delay_cuts.json",
      pause_cuts_on_original_tos_key: "smart-cut/smartcut_success_self_001/preview/edit_success_self_001/pause_cuts.json",
      error_message: null,
      version_number: 2,
      created_at: "2026-04-18T08:50:00Z",
      updated_at: "2026-04-18T09:30:00Z",
    },
  ],
  smartcut_success_shared_001: [
    {
      id: "edit_success_shared_001",
      task_id: "smartcut_success_shared_001",
      edited_script: "共享任务成片。",
      status: "success",
      audio_a_url: "smart-cut/smartcut_success_shared_001/analyze/audio_a.mp3",
      audio_b_url: "smart-cut/smartcut_success_shared_001/preview/edit_success_shared_001/audio_b.mp3",
      edited_delay_cuts_tos_key: "smart-cut/smartcut_success_shared_001/preview/edit_success_shared_001/edited_delay_cuts.json",
      pause_cuts_on_original_tos_key: "smart-cut/smartcut_success_shared_001/preview/edit_success_shared_001/pause_cuts.json",
      error_message: null,
      version_number: 3,
      created_at: "2026-04-18T08:10:00Z",
      updated_at: "2026-04-18T09:00:00Z",
    },
  ],
};

function detailFor(taskId: string) {
  return SMART_CUT_DETAILS[taskId] ?? SMART_CUT_DETAILS.smartcut_route_smoke_001;
}

function editsFor(taskId: string) {
  return SMART_CUT_EDITS[taskId] ?? [];
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

  await page.route(/\/api\/proxy\/api\/smart-cut\/tasks\/([^/?]+)\/abandon(\?.*)?$/, async (route) => {
    const taskId = route.request().url().match(/\/tasks\/([^/?]+)\/abandon/)?.[1] ?? "";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: taskId,
        status: "abandoned",
        abandoned_at: "2026-04-18T12:30:00Z",
      }),
    });
  });

  await page.route(/\/api\/proxy\/api\/task-center\/tasks(\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "smartcut_success_shared_001",
          title: "共享完成任务",
          task_type: "smart_cut",
          status: "finished",
          current_stage: "complete",
          progress: 100,
          progress_detail: "Done",
          updated_at: "2026-04-18T09:00:00Z",
          created_at: "2026-04-18T06:00:00Z",
          queue_position: null,
          download_url: "https://example.com/smartcut_success_shared_001/final_video.mp4",
          error_message: null,
          input_files: ["source_video.mp4", "reference.txt"],
          output_files: ["final_video.mp4"],
        },
      ]),
    });
  });

  await page.route(/\/api\/proxy\/api\/smart-cut\/tasks(\?.*)?$/, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          task_id: "smartcut_new_task_001",
          status: "waiting_upload",
          current_stage: "upload",
          company_id: USER.company_id,
          task_title: "智能剪气口-20260418-120000",
          created_at: "2026-04-18T12:00:00Z",
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
          company_id: USER.company_id,
          status: "waiting_user",
          current_stage: "preview",
          active_edit_id: "edit_route_smoke_001",
          created_at: "2026-04-18T08:00:00Z",
          updated_at: "2026-04-18T10:10:00Z",
        },
        {
          id: "smartcut_success_self_001",
          company_id: USER.company_id,
          status: "success",
          current_stage: "complete",
          active_edit_id: "edit_success_self_001",
          created_at: "2026-04-18T07:00:00Z",
          updated_at: "2026-04-18T09:30:00Z",
        },
        {
          id: "smartcut_analyze_failed_001",
          company_id: USER.company_id,
          status: "analyze_failed",
          current_stage: "analyze",
          active_edit_id: null,
          created_at: "2026-04-18T05:00:00Z",
          updated_at: "2026-04-18T08:00:00Z",
        },
      ]),
    });
  });

  await page.route(/\/api\/proxy\/api\/smart-cut\/tasks\/([^/?]+)\/edits(\?.*)?$/, async (route) => {
    const taskId = route.request().url().match(/\/tasks\/([^/?]+)\/edits/)?.[1] ?? "";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(editsFor(taskId)),
    });
  });

  await page.route(/\/api\/proxy\/api\/smart-cut\/tasks\/([^/?]+)\/runs(\?.*)?$/, async (route) => {
    const taskId = route.request().url().match(/\/tasks\/([^/?]+)\/runs/)?.[1] ?? "";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: `${taskId}_run_1`,
          task_id: taskId,
          run_type: "analyze",
          status: "success",
          sequence_number: 1,
          scheduler_task_id: `sched_${taskId}_1`,
          source_edit_id: null,
          payload_snapshot: {},
          result_snapshot: {},
          error_message: null,
          created_at: "2026-04-18T09:00:00Z",
          started_at: "2026-04-18T09:01:00Z",
          completed_at: "2026-04-18T09:02:00Z",
          updated_at: "2026-04-18T09:02:00Z",
        },
      ]),
    });
  });

  await page.route(/\/api\/proxy\/api\/smart-cut\/tasks\/([^/?]+)\/title(\?.*)?$/, async (route) => {
    const taskId = route.request().url().match(/\/tasks\/([^/?]+)\/title/)?.[1] ?? "";
    const payload = route.request().postDataJSON() as { task_title?: string };
    const detail = detailFor(taskId);
    detail.task_title = payload.task_title ?? detail.task_title;
    detail.updated_at = "2026-04-18T12:40:00Z";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(detail),
    });
  });

  await page.route(/\/api\/proxy\/api\/smart-cut\/tasks\/([^/?]+)$/, async (route) => {
    const taskId = route.request().url().match(/\/tasks\/([^/?]+)$/)?.[1] ?? "";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(detailFor(taskId)),
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
      await expect(page.getByRole("heading", { name: "我的待处理任务" })).toBeVisible();
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

test("tasks detail keeps page in place and switches to continue edit for shared success task", async ({ page }) => {
  await page.goto("/tasks?taskId=smartcut_success_shared_001");
  await expect(page.getByRole("heading", { name: "共享完成任务" })).toBeVisible();
  await expect(page.getByRole("button", { name: "继续编辑" })).toBeVisible();
});

test("tasks detail continue edit enters shared company workspace", async ({ page }) => {
  await page.goto("/tasks?taskId=smartcut_success_shared_001");
  await page.getByRole("button", { name: "继续编辑" }).click();
  await expect(page).toHaveURL(/\/smart-cut\/smartcut_success_shared_001$/);
  await expect(page.getByText("当前打开的是 other_user 的同公司共享任务。")).toBeVisible();
});

test("analyze failed workspace shows delete action", async ({ page }) => {
  await page.goto("/smart-cut/smartcut_analyze_failed_001");
  await expect(page.getByText("分析阶段失败")).toBeVisible();
  await expect(page.getByRole("button", { name: "删除任务" })).toBeVisible();
});

test("tasks detail shows delete action for own failed task", async ({ page }) => {
  await page.goto("/tasks?taskId=smartcut_analyze_failed_001");
  await expect(page.getByRole("button", { name: "删除任务" })).toBeVisible();
});

test("tasks detail delete removes failed task from the list", async ({ page }) => {
  await page.goto("/tasks?taskId=smartcut_analyze_failed_001");
  await page.getByRole("button", { name: "删除任务" }).click();
  await expect(page.getByText("分析失败任务")).toHaveCount(0);
});

test("tasks detail lets the owner rename a Smart Cut task", async ({ page }) => {
  await page.goto("/tasks?taskId=smartcut_route_smoke_001");
  await expect(page.getByRole("heading", { name: "我的待处理任务" })).toBeVisible();

  await page.getByRole("button", { name: "修改名称" }).click();
  await page.getByLabel("任务名称").fill("客户素材剪辑第一版");
  await page.getByRole("button", { name: "保存" }).click();

  await expect(page.getByText("任务名称已更新。")).toBeVisible();
  await expect(page.getByRole("heading", { name: "客户素材剪辑第一版" })).toBeVisible();
  await expect(page.getByText("我的待处理任务")).toHaveCount(0);
});
