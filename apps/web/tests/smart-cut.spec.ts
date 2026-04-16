import { expect, test } from "@playwright/test";

test("user can enter smart cut workspace and submit preview/finalize actions", async ({ page }) => {
  await page.route("**/api/proxy/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user: {
          username: "qa_user",
          role: "user",
        },
      }),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "smartcut_mock_001",
            status: "ready_finalize",
            current_stage: "finalize",
            active_edit_id: "edit_mock_001",
            created_at: "2026-04-16T08:00:00Z",
            updated_at: "2026-04-16T09:00:00Z",
          },
        ]),
      });
      return;
    }

    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: "smartcut_mock_002",
        user_id: 1,
        status: "waiting_upload",
        current_stage: null,
        error_stage: null,
        error_message: null,
        original_video_url: null,
        original_video_tos_key: null,
        reference_text_url: null,
        reference_text_tos_key: null,
        analyze_script: null,
        analyze_script_tos_key: null,
        asr_result_tos_key: null,
        active_edit_id: null,
        finalize_source_edit_id: null,
        final_video_url: null,
        final_video_tos_key: null,
        groundtruth_url: null,
        groundtruth_tos_key: null,
        feed_to_ai: false,
        output_mode: null,
        last_scheduler_task_id: null,
        created_at: "2026-04-16T09:00:00Z",
        updated_at: "2026-04-16T09:00:00Z",
      }),
    });
  });

  await page.route("**/api/proxy/api/smart-cut/tasks/smartcut_mock_001", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "smartcut_mock_001",
          user_id: 1,
          status: "ready_finalize",
          current_stage: "finalize",
          error_stage: null,
          error_message: null,
          original_video_url: "/api/fake-tos/smart-cut/smart-cut/smartcut_mock_001/input/source_video.mp4",
          original_video_tos_key: "smart-cut/smartcut_mock_001/input/source_video.mp4",
          reference_text_url: "/api/fake-tos/smart-cut/smart-cut/smartcut_mock_001/input/reference.txt",
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
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "smartcut_mock_001",
        user_id: 1,
        status: method === "POST" ? "finalizing" : "ready_finalize",
        current_stage: "finalize",
        error_stage: null,
        error_message: null,
        original_video_url: null,
        original_video_tos_key: "smart-cut/smartcut_mock_001/input/source_video.mp4",
        reference_text_url: null,
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
      }),
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
          audio_b_url: "https://example.com/audio_b.mp3",
          audio_b_tos_key: "smart-cut/smartcut_mock_001/preview/edit_mock_001/audio_b.mp3",
          edited_delay_cuts_tos_key: "smart-cut/smartcut_mock_001/preview/edit_mock_001/edited_delay_cuts.json",
          pause_cuts_on_original_tos_key: "smart-cut/smartcut_mock_001/preview/edit_mock_001/pause_cuts_on_original.json",
          error_message: null,
          created_at: "2026-04-16T08:20:00Z",
          updated_at: "2026-04-16T08:30:00Z",
        },
      ]),
    });
  });

  await page.goto("/welcome");
  await expect(page.getByRole("button", { name: "智能气口剪辑" })).toBeVisible();
  await page.getByRole("button", { name: "智能气口剪辑" }).click();
  await expect(page).toHaveURL(/\/smart-cut$/);
  await expect(page.getByText("三段式智能气口剪辑工作台")).toBeVisible();
  await expect(page.getByText("smartcut_mock_001")).toBeVisible();

  await page.getByRole("button", { name: "smartcut_mock_001" }).click();
  await expect(page).toHaveURL(/\/smart-cut\/smartcut_mock_001$/);
  await expect(page.getByText("删除线脚本调整")).toBeVisible();
  await expect(page.getByRole("button", { name: "生成试听" })).toBeVisible();
  await expect(page.getByRole("button", { name: "生成视频" })).toBeVisible();
});
