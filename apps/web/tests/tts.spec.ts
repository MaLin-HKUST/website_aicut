import { expect, test } from "@playwright/test";

test("tts page lets users select one approved voice and submits it", async ({ page }) => {
  await page.route("**/api/proxy/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user: {
          username: "tts_user",
          role: "user",
          company_id: 10,
          company_name: "日标住建",
        },
      }),
    });
  });

  await page.route("**/api/proxy/api/task-center/tasks**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  let generatePayload: Record<string, unknown> | null = null;
  await page.route("**/api/proxy/user/tts/generate", async (route) => {
    generatePayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        audio_base64: Buffer.from("fake-audio").toString("base64"),
        mime_type: "audio/mpeg",
        file_name: "kdt-voice-output.mp3",
        usage_credits: 30,
        usage_characters: 30,
      }),
    });
  });

  await page.goto("/tts");

  await expect(page.getByLabel("TTS 音色")).toHaveValue("康迪");
  await expect(page.locator("#tts-voice option")).toHaveText(["康迪", "日标住建-小唐", "日标住建-凯迪"]);

  await page.getByLabel("TTS 音色").selectOption("日标住建-凯迪");
  await expect(page.getByText("当前音色")).toBeVisible();
  await expect(page.locator("p").filter({ hasText: "日标住建-凯迪" })).toBeVisible();

  await page.locator("#tts-text").fill("123456789012345678901234567890");
  await page.getByRole("button", { name: "生成音频" }).click();

  expect(generatePayload).toMatchObject({
    text: "123456789012345678901234567890",
    voice_name: "日标住建-凯迪",
  });
  await expect(page.getByText("kdt-voice-output.mp3")).toBeVisible();
});
