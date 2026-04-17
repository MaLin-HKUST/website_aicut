import { expect, test } from "@playwright/test";

test("admin can complete the bootstrap flow and a normal user is routed to welcome", async ({ page }) => {
  const stamp = Date.now();
  const companyName = `QA Company ${stamp}`;
  const username = `qa_user_${stamp}`;
  const password = "QaPass123!";
  const materialName = `QA Material ${stamp}`;
  const materialRemark = `Created during Playwright admin flow ${stamp}`;

  await page.goto("/login");

  await page.getByLabel("用户名").fill("admin");
  await page.getByLabel("密码").fill(process.env.ADMIN_PASSWORD ?? "Malin123456");
  await page.getByRole("button", { name: "登录" }).click();

  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByText("Signed in as admin")).toBeVisible();

  await page.getByPlaceholder("Company name").fill(companyName);
  await page.getByRole("button", { name: "Create Company" }).click();
  await expect(page.getByTestId("companies-panel").getByText(companyName)).toBeVisible();

  await page.getByPlaceholder("Username").fill(username);
  await page.getByPlaceholder("Password").fill(password);
  await page.locator("form").filter({ hasText: "Create User" }).getByRole("combobox").nth(1).selectOption({ label: companyName });
  await page.getByRole("button", { name: "Create User" }).click();
  await expect(page.getByTestId("users-panel").getByText(`${username}`)).toBeVisible();
  await expect(page.getByTestId("users-panel").getByText(`user · ${companyName}`)).toBeVisible();

  await page.getByPlaceholder("Material name").fill(materialName);
  await page.getByPlaceholder("Remark").fill(materialRemark);
  await page.locator("form").filter({ hasText: "Create Material" }).getByRole("combobox").selectOption({ label: companyName });
  await page.getByRole("button", { name: "Create Material" }).click();
  await expect(page.getByTestId("materials-panel").getByText(materialName)).toBeVisible();
  await expect(page.getByTestId("materials-panel").getByText(materialRemark)).toBeVisible();

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码").fill(password);
  await page.getByRole("button", { name: "登录" }).click();

  await expect(page).toHaveURL(/\/welcome$/);
  await expect(page.getByRole("button", { name: "文案生成语音" })).toBeVisible();

  await page.route("**/api/proxy/user/tts/generate", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        audio_base64: Buffer.from("fake-audio").toString("base64"),
        mime_type: "audio/mpeg",
        file_name: "qa-output.mp3",
        usage_credits: 30,
        usage_characters: 30,
      }),
    });
  });

  await page.getByRole("button", { name: "文案生成语音" }).click();
  await expect(page).toHaveURL(/\/tts$/);
  await expect(page.getByText("本月累计TOKEN：30")).toBeVisible();
  await page.locator("#tts-text").fill("123456789012345678901234567890");
  await expect(page.getByText("本月累计TOKEN：30")).toBeVisible();
  await page.getByRole("button", { name: "生成音频" }).click();
  await expect(page.getByText("qa-output.mp3")).toBeVisible();
  await expect(page.getByRole("button", { name: "下载音频" })).toBeVisible();
});
