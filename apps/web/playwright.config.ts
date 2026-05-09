import { defineConfig, devices } from "@playwright/test";

const port = 3000;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${port}`;
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
const chromiumArgs = process.env.PLAYWRIGHT_CHROMIUM_ARGS?.split(/\s+/).filter(Boolean);
const chromiumLaunchOptions =
  executablePath || chromiumArgs
    ? {
        launchOptions: {
          ...(executablePath ? { executablePath } : {}),
          ...(chromiumArgs ? { args: chromiumArgs } : {}),
        },
      }
    : {};

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: "INTERNAL_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000",
        url: baseURL,
        reuseExistingServer: true,
        timeout: 120_000,
      },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        ...chromiumLaunchOptions,
      },
    },
  ],
});
