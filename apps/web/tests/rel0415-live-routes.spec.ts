import { expect, test } from "@playwright/test";

const CASES = [
  { path: "/welcome", marker: "Audio Workspace" },
  { path: "/smart-cut", marker: "Smart Cut" },
  { path: "/tasks", marker: "/app/tasks/page-" },
  { path: "/tts", marker: "/app/tts/page-" },
  { path: "/admin/tasks", marker: "/app/admin/tasks/page-" },
] as const;

for (const item of CASES) {
  test(`rel0415 live route responds: ${item.path}`, async ({ request }) => {
    const response = await request.get(item.path);
    expect(response.ok()).toBeTruthy();
    const body = await response.text();
    expect(body).toContain(item.marker);
  });
}
