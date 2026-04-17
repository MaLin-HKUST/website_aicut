import fs from "node:fs";

import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test("rel0415 smart cut browser flow reaches task center", async ({ page }, testInfo) => {
  test.setTimeout(180_000);

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
      url: "https://xiaomajianji.cn",
      httpOnly: true,
      secure: false,
      sameSite: "Lax",
    },
  ]);

  const userApi = page.context().request;
  const taskCreate = await userApi.post("/api/proxy/api/smart-cut/tasks", {
    data: { user_id: username },
  });
  expect(taskCreate.ok()).toBeTruthy();
  const taskCreatePayload = await taskCreate.json();
  const taskId = taskCreatePayload.data.task_id as string;

  await page.goto(`/smart-cut/${taskId}`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await expect(page.getByText("上传输入并开始分析")).toBeVisible({ timeout: 60_000 });
  const videoPath = testInfo.outputPath("source_video.mp4");
  const textPath = testInfo.outputPath("reference.txt");
  const videoBuffer = Buffer.from("rel0415-browser-video");
  const textBuffer = Buffer.from("这是 Playwright 浏览器验收文案。", "utf-8");
  fs.writeFileSync(videoPath, videoBuffer);
  fs.writeFileSync(textPath, textBuffer);

  const uploadResp = await userApi.post(`/api/proxy/api/smart-cut/tasks/${taskId}/upload-direct`, {
    multipart: {
      video_file: {
        name: "source_video.mp4",
        mimeType: "video/mp4",
        buffer: videoBuffer,
      },
      reference_file: {
        name: "reference.txt",
        mimeType: "text/plain",
        buffer: textBuffer,
      },
    },
  });
  expect(uploadResp.ok()).toBeTruthy();
  const analyzeResp = await userApi.post(`/api/proxy/api/smart-cut/tasks/${taskId}/analyze`);
  expect(analyzeResp.ok()).toBeTruthy();

  await expect
    .poll(async () => {
      const detail = await userApi.get(`/api/proxy/api/smart-cut/tasks/${taskId}`);
      const payload = await detail.json();
      return payload.status;
    }, { timeout: 90_000 })
    .toBe("waiting_user");

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByRole("button", { name: "生成试听" })).toBeEnabled({ timeout: 90000 });

  await page.getByRole("button", { name: "生成试听" }).click();
  await expect
    .poll(async () => {
      const detail = await userApi.get(`/api/proxy/api/smart-cut/tasks/${taskId}`);
      const payload = await detail.json();
      return payload.audio_b_url;
    }, { timeout: 90_000 })
    .not.toBeNull();

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator("audio")).toBeVisible({ timeout: 90000 });

  await page.getByRole("button", { name: "生成视频" }).click();
  await expect(page).toHaveURL(/\/tasks\?taskId=/, { timeout: 15000 });
  await expect(page.getByText("My Job Queue")).toBeVisible();
  await expect(page.getByText(taskId)).toBeVisible({ timeout: 90000 });
});
