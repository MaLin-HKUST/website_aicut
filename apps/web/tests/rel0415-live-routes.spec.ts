import { expect, Page, test } from "@playwright/test";

const USER = {
  username: "route_smoke_user",
  role: "user",
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
      await expect(page.getByRole("heading", { name: "三段式智能气口剪辑工作台" })).toBeVisible();
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
