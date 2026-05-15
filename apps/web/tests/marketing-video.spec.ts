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

async function createMockMarketingVideoTask(page: Page, filename = "07.txt") {
  await page.goto("/marketing-video");
  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: filename,
    mimeType: "text/plain",
    buffer: Buffer.from("TONGAN sample script"),
  });
  await page.getByRole("button", { name: "创建营销视频任务" }).click();
  await expect(page.getByText("任务已进入任务中心")).toBeVisible();
  const workflowText = await page.locator("text=/wf_mock_/").first().innerText();
  return workflowText.trim();
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

  await page.route(/\/api\/proxy\/api\/smart-cut\/tasks(\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
});

test("marketing video create enters task center and allows another task", async ({ page }) => {
  await mockAuth(page, FULL_ACCESS_USER);
  const firstWorkflowId = await createMockMarketingVideoTask(page);

  await page.getByRole("button", { name: "继续创建" }).click();
  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "08.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Second TONGAN sample script"),
  });
  await page.getByRole("button", { name: "创建营销视频任务" }).click();
  await expect(page.getByText("任务已进入任务中心")).toBeVisible();

  await page.getByRole("button", { name: "查看任务详情" }).click();
  await expect(page).toHaveURL(/\/tasks\?taskId=wf_mock_/);
  await expect(page.getByText("准备素材与基础视频").first()).toBeVisible();
  await expect(page.getByText("智能匹配素材").first()).toBeVisible();
  await expect(page.getByText("渲染成片").first()).toBeVisible();
  await expect(page.getByText(firstWorkflowId)).toBeVisible();
});

test("tasks page restores marketing video detail, renames, stops, and archives", async ({ page }) => {
  await mockAuth(page, FULL_ACCESS_USER);
  const workflowId = await createMockMarketingVideoTask(page);

  await page.goto(`/tasks?taskId=${encodeURIComponent(workflowId)}`);
  await expect(page.getByText(workflowId).first()).toBeVisible();
  await expect(page.getByText("准备素材与基础视频").first()).toBeVisible();

  await page.getByLabel("营销视频任务名称").fill("新的营销视频任务名");
  await page.getByRole("button", { name: "保存名称" }).click();
  await expect(page.getByText("任务名称已更新。")).toBeVisible();
  await expect(page.getByRole("heading", { name: "新的营销视频任务名" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "新的营销视频任务名" })).toBeVisible();
  await expect(page.getByText("准备素材与基础视频").first()).toBeVisible();

  await page.getByRole("button", { name: "停止任务" }).click();
  await expect(page.getByText("任务已停止。")).toBeVisible();
  await expect(page.getByText("已停止").first()).toBeVisible();

  await page.getByRole("button", { name: "删除任务" }).click();
  await expect(page.getByText(workflowId)).toHaveCount(0);
});

test("succeeded marketing video task shows download entry in task center", async ({ page }) => {
  await mockAuth(page, FULL_ACCESS_USER);
  const workflowId = await createMockMarketingVideoTask(page);

  await page.waitForTimeout(9500);
  await page.goto(`/tasks?taskId=${encodeURIComponent(workflowId)}`);
  await expect(page.getByText("成片已生成")).toBeVisible();
  await expect(page.getByRole("button", { name: "下载成片" })).toBeVisible();
});

test("Smart Cut task center smoke still loads", async ({ page }) => {
  await mockAuth(page, FULL_ACCESS_USER);
  await page.goto("/tasks");

  await expect(page.getByRole("heading", { name: "任务列表" })).toBeVisible();
  await expect(page.getByText("当前筛选下没有任务")).toBeVisible();
});

test("company 2 keeps full marketing video access", async ({ page }) => {
  await mockAuth(page, { ...FULL_ACCESS_USER, company_id: 2, company_name: "小马AI" });
  await page.goto("/marketing-video");

  await expect(page.getByTestId("marketing-video-development-lock")).toHaveCount(0);
  await expect(page.getByText("标准视频模式")).toBeVisible();
  await expect(page.getByText("输入短视频的文案(txt文件格式)")).toBeVisible();
  await expect(page.getByText("上传短视频的文案并创建 TONGAN 标准营销视频任务。")).toBeVisible();
  await expect(page.getByText("只支持一个 TXT 文案文件。RBZJ/KDT IP 模式暂未开放。")).toHaveCount(0);
  await expect(page.getByText("上传一个 TXT 文案并创建 TONGAN 标准营销视频任务。")).toHaveCount(0);
  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "07.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("TONGAN sample script"),
  });
  await expect(page.getByRole("button", { name: "创建营销视频任务" })).toBeEnabled();
});

test("company 1 sees KDT controls and can create a mock KDT task", async ({ page }) => {
  await mockAuth(page, { ...FULL_ACCESS_USER, username: "ribu_user", company_id: 1, company_name: "日标住建" });
  await page.goto("/marketing-video");

  await expect(page.getByTestId("marketing-video-development-lock")).toHaveCount(0);
  await expect(page.getByText("KDT IP营销视频")).toBeVisible();
  await expect(page.getByText("IP 视频模式")).toBeVisible();
  await expect(page.getByTestId("kdt-open-end-controls")).toBeVisible();
  await page.getByLabel("选择 TXT 文案").setInputFiles({
    name: "kdt.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("KDT sample script"),
  });
  await expect(page.getByRole("button", { name: "创建营销视频任务" })).toBeEnabled();
  await page.getByRole("button", { name: "创建营销视频任务" }).click();
  await expect(page.getByText("任务已进入任务中心")).toBeVisible();
  await page.getByRole("button", { name: "查看任务详情" }).click();
  await expect(page).toHaveURL(/\/tasks\?taskId=wf_mock_/);
  await expect(page.getByText("校验输入").first()).toBeVisible();
  await expect(page.getByText("准备素材").first()).toBeVisible();
  await expect(page.getByText("智能匹配").first()).toBeVisible();
});

test("company 9 can see marketing video page but cannot operate it", async ({ page }) => {
  await mockAuth(page, { ...FULL_ACCESS_USER, username: "xiaoyingtao_user", company_id: 9, company_name: "小樱桃文化" });
  await page.goto("/marketing-video");

  await expect(page.getByRole("heading", { name: "生成营销视频" })).toBeVisible();
  await expect(page.getByTestId("marketing-video-development-lock")).toBeVisible();
  await expect(page.getByText("页面正在开发中")).toBeVisible();
  await expect(page.getByRole("button", { name: "创建营销视频任务" })).toBeDisabled();
});
