import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test("rel0415 smart cut browser flow reaches task center", async ({ page }) => {
  test.setTimeout(180_000);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });

  const username = "rbzj";
  const password = "123456";

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

  await page.goto("/welcome", { waitUntil: "networkidle", timeout: 60_000 });
  await expect(page.getByRole("button", { name: "智能气口剪辑" })).toBeVisible({ timeout: 30_000 });

  const authHeaders = { Cookie: `session_token=${userToken}` };
  const taskCreate = await page.request.post("/api/proxy/api/smart-cut/tasks", {
    headers: authHeaders,
    data: { user_id: username },
  });
  expect(taskCreate.ok()).toBeTruthy();
  const taskCreatePayload = await taskCreate.json();
  const taskId = taskCreatePayload.data?.task_id ?? null;
  expect(taskId).toBeTruthy();

  const uploadResp = await page.request.post(`/api/proxy/api/smart-cut/tasks/${taskId}/upload-direct`, {
    headers: authHeaders,
    multipart: {
      video_file: {
        name: "source_video.mp4",
        mimeType: "video/mp4",
        buffer: Buffer.from("rel0415-browser-video"),
      },
      reference_file: {
        name: "reference.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("这是 Playwright 浏览器验收文案。", "utf-8"),
      },
    },
  });
  expect(uploadResp.ok()).toBeTruthy();

  const analyzeResp = await page.request.post(`/api/proxy/api/smart-cut/tasks/${taskId}/analyze`, {
    headers: authHeaders,
  });
  expect(analyzeResp.ok()).toBeTruthy();

  await page.goto(`/smart-cut/${taskId}`, { waitUntil: "networkidle", timeout: 60_000 });
  await expect(page).toHaveURL(/\/smart-cut\/[0-9a-f-]+$/, { timeout: 30_000 });
  await expect(page.getByText("请上传你要处理的视频和标准文案")).toBeVisible({ timeout: 60_000 });

  await expect
    .poll(async () => {
      return page.evaluate(async (id) => {
        const detail = await fetch(`/api/proxy/api/smart-cut/tasks/${id}`);
        const payload = await detail.json();
        return payload.status;
      }, taskId);
    }, { timeout: 90_000 })
    .toBe("waiting_user");

  await expect
    .poll(
      async () =>
        page.evaluate(async (id) => {
          const auth = await fetch("/api/proxy/auth/me");
          if (!auth.ok) return `auth:${auth.status}`;

          const detail = await fetch(`/api/proxy/api/smart-cut/tasks/${id}`);
          if (!detail.ok) return `detail:${detail.status}`;

          const payload = await detail.json();
          const script = payload.current_edited_script ?? payload.analyze_script;
          const hasScript =
            typeof script === "string"
              ? script.trim().length > 0
              : Array.isArray(script)
                ? script.length > 0
                : Boolean(script);
          return `${payload.status}:${hasScript}`;
        }, taskId),
      { timeout: 90_000 },
    )
    .toBe("waiting_user:true");

  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "删除线脚本调整" })).toBeVisible({ timeout: 90_000 });
  await expect(page.getByRole("button", { name: "标记删除" })).toBeVisible({ timeout: 90_000 });
  await expect(page.getByRole("button", { name: "恢复保留" })).toBeVisible({ timeout: 90_000 });
  await expect(page.getByRole("button", { name: "清空删除标记" })).toBeVisible({ timeout: 90_000 });
  await expect(page.getByRole("button", { name: "生成试听" })).toBeEnabled({ timeout: 90_000 });

  await page.getByRole("button", { name: "生成试听" }).click();
  await expect
    .poll(async () => {
      return page.evaluate(async (id) => {
        const detail = await fetch(`/api/proxy/api/smart-cut/tasks/${id}`);
        const payload = await detail.json();
        return payload.audio_b_url;
      }, taskId);
    }, { timeout: 90_000 })
    .not.toBeNull();

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator("audio")).toBeVisible({ timeout: 90000 });

  await page.getByRole("button", { name: "生成视频" }).click();
  await expect(page).toHaveURL(/\/tasks\?taskId=/, { timeout: 15000 });
  await expect(page.getByRole("heading", { name: "任务列表" })).toBeVisible();
  await expect(page.getByText(taskId).first()).toBeVisible({ timeout: 90_000 });
});
