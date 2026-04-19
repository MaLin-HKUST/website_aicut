import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test("real-data smart cut task is visible and downloadable in the live UI", async ({ page }) => {
  const taskId = process.env.PLAYWRIGHT_REAL_DATA_TASK_ID;
  test.skip(!taskId, "PLAYWRIGHT_REAL_DATA_TASK_ID is required for the real-data UI verification");

  test.setTimeout(120_000);

  const username = process.env.PLAYWRIGHT_USERNAME ?? "rbzj";
  const password = process.env.PLAYWRIGHT_PASSWORD ?? "123456";

  const userLogin = await page.request.post("/api/proxy/auth/login", {
    data: { username, password },
  });
  expect(userLogin.ok()).toBeTruthy();
  const userSetCookie = userLogin.headers()["set-cookie"] ?? "";
  const userToken = /session_token=([^;]+)/.exec(userSetCookie)?.[1];
  expect(userToken).toBeTruthy();

  await page.context().clearCookies();
  await page.context().addCookies([
    {
      name: "session_token",
      value: userToken!,
      domain: "xiaomajianji.cn",
      path: "/",
      httpOnly: true,
      secure: true,
      sameSite: "Lax",
    },
  ]);

  await page.goto(`/tasks?taskId=${taskId}`, { waitUntil: "networkidle", timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "任务列表" })).toBeVisible({ timeout: 30_000 });

  const taskDetailResponse = await page.request.get(`/api/proxy/api/smart-cut/tasks/${taskId}`, {
    headers: { Cookie: `session_token=${userToken}` },
  });
  expect(taskDetailResponse.ok()).toBeTruthy();
  const taskDetailPayload = (await taskDetailResponse.json()) as {
    id: string;
    status: string;
    current_stage?: string | null;
    final_video_url?: string | null;
  };
  expect(taskDetailPayload.id).toBe(taskId);
  expect(taskDetailPayload.status).toBe("success");
  expect(taskDetailPayload.current_stage).toBe("complete");
  expect(taskDetailPayload.final_video_url).toBeTruthy();

  await page.goto(`/smart-cut/${taskId}`, { waitUntil: "networkidle", timeout: 60_000 });
  await expect(page).toHaveURL(new RegExp(`/smart-cut/${taskId}$`), { timeout: 30_000 });
  await expect(page.getByText("阶段 1：生成试听")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("audio")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("下载视频")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("a[href*='smart-cut/']").first()).toBeVisible({ timeout: 30_000 });
});
