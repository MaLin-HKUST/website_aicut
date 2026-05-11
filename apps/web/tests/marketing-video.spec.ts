import { expect, test, type Page } from "@playwright/test";

type TestUser = {
  username: string;
  role: "user";
  company_id: number;
  company_name: string;
};

const FULL_ACCESS_USER: TestUser = {
  username: "marketing_video_user",
  role: "user",
  company_id: 10,
  company_name: "同安影视城",
} as const;

async function mockAuth(page: Page, user: TestUser) {
  await page.route("**/api/proxy/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ user }),
    });
  });
}

test.beforeEach(async ({ page }) => {
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
});

test("marketing video mock workspace creates a TONGAN task and shows terminal states", async ({ page }) => {
  await mockAuth(page, FULL_ACCESS_USER);
  await page.goto("/marketing-video");

  await expect(page.getByRole("heading", { name: "生成营销视频" })).toBeVisible();
  await expect(page.getByText("TONGAN 标准", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "创建营销视频任务" })).toBeDisabled();

  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "07.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("TONGAN sample script"),
  });

  await expect(page.getByText(/07\.txt/)).toBeVisible();
  await page.getByRole("button", { name: "创建营销视频任务" }).click();

  await expect(page.getByText(/Mock 任务已创建/)).toBeVisible();
  await expect(page.getByText("文案校验")).toBeVisible();
  await expect(page.getByText("视频合成")).toBeVisible();

  await page.getByRole("button", { name: "查看失败示例" }).click();
  await expect(page.getByText("样例 07 文案解析失败，请检查 TXT 内容后重试。").first()).toBeVisible();

  await page.getByRole("button", { name: "查看成功示例" }).click();
  await expect(page.getByText("成片已生成")).toBeVisible();
  await expect(page.getByRole("button", { name: "下载成片" })).toBeVisible();
});

test("company 2 keeps full marketing video access", async ({ page }) => {
  await mockAuth(page, { ...FULL_ACCESS_USER, company_id: 2, company_name: "小马AI" });
  await page.goto("/marketing-video");

  await expect(page.getByTestId("marketing-video-development-lock")).toHaveCount(0);
  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "07.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("TONGAN sample script"),
  });
  await expect(page.getByRole("button", { name: "创建营销视频任务" })).toBeEnabled();
});

for (const user of [
  { ...FULL_ACCESS_USER, username: "ribu_user", company_id: 1, company_name: "日标住建" },
  { ...FULL_ACCESS_USER, username: "xiaoyingtao_user", company_id: 9, company_name: "小樱桃文化" },
] as const) {
  test(`company ${user.company_id} can see marketing video page but cannot operate it`, async ({ page }) => {
    await mockAuth(page, user);
    await page.goto("/marketing-video");

    await expect(page.getByRole("heading", { name: "生成营销视频" })).toBeVisible();
    await expect(page.getByTestId("marketing-video-development-lock")).toBeVisible();
    await expect(page.getByText("页面正在开发中")).toBeVisible();
    await expect(page.getByRole("button", { name: "创建营销视频任务" })).toBeDisabled();
  });
}
