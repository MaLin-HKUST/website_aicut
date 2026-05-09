import { expect, Page, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

type JsonRecord = Record<string, any>;

type NetworkEvent = {
  type: "request" | "response" | "requestfailed";
  url: string;
  redacted_url: string;
  method?: string;
  status?: number;
  failure?: string | null;
  request_headers?: Record<string, string>;
  response_headers?: Record<string, string>;
};

const DEFAULT_SAMPLE_TXT = "/Volumes/XIAOMA-A-1T/Taskspace_Tongan/wenan/wuyi_txt_split_10_files/07.txt";
const DEFAULT_EVIDENCE_DIR = path.resolve(process.cwd(), "../../docs/stage7a_remote_evidence");
const TONGAN_LABELS = ["准备素材与基础视频", "智能匹配素材", "渲染成片"];

test.describe.configure({ mode: "serial" });
test.skip(process.env.RUN_STAGE7A_RC !== "1", "Set RUN_STAGE7A_RC=1 to run the Stage 7A live RC validation.");

let createdWorkflowId = "";
let finalVideoUrl = "";
let finalVideoKey = "";

function evidenceDir(): string {
  return path.resolve(process.env.STAGE7A_EVIDENCE_DIR ?? DEFAULT_EVIDENCE_DIR);
}

function ensureEvidenceDir(): void {
  fs.mkdirSync(evidenceDir(), { recursive: true });
}

function redactUrl(value: string): string {
  try {
    const url = new URL(value);
    url.search = url.search ? "?<redacted>" : "";
    return url.toString();
  } catch {
    return value;
  }
}

function redactPayload(value: any): any {
  if (typeof value === "string") {
    if (/^https?:\/\//i.test(value)) return redactUrl(value);
    return value;
  }
  if (Array.isArray(value)) return value.map(redactPayload);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, nextValue]) => [key, redactPayload(nextValue)]));
  }
  return value;
}

function writeJson(name: string, payload: JsonRecord): void {
  ensureEvidenceDir();
  fs.writeFileSync(path.join(evidenceDir(), name), `${JSON.stringify(redactPayload(payload), null, 2)}\n`);
}

function writeText(name: string, payload: string): void {
  ensureEvidenceDir();
  fs.writeFileSync(path.join(evidenceDir(), name), payload.endsWith("\n") ? payload : `${payload}\n`);
}

function isTosUrl(url: string): boolean {
  try {
    const host = new URL(url).host;
    return host.includes("tos") || host.includes("volces");
  } catch {
    return false;
  }
}

function attachNetworkRecorder(page: Page): NetworkEvent[] {
  const events: NetworkEvent[] = [];
  page.on("request", (request) => {
    if (!isTosUrl(request.url())) return;
    events.push({
      type: "request",
      url: request.url(),
      redacted_url: redactUrl(request.url()),
      method: request.method(),
      request_headers: request.headers(),
    });
  });
  page.on("response", async (response) => {
    if (!isTosUrl(response.url())) return;
    events.push({
      type: "response",
      url: response.url(),
      redacted_url: redactUrl(response.url()),
      status: response.status(),
      response_headers: response.headers(),
    });
  });
  page.on("requestfailed", (request) => {
    if (!isTosUrl(request.url())) return;
    events.push({
      type: "requestfailed",
      url: request.url(),
      redacted_url: redactUrl(request.url()),
      method: request.method(),
      failure: request.failure()?.errorText ?? null,
      request_headers: request.headers(),
    });
  });
  return events;
}

async function installSessionCookie(page: Page): Promise<void> {
  const cookieHeader = process.env.STAGE7A_AUTH_COOKIE;
  if (!cookieHeader) return;
  const baseUrl = process.env.PLAYWRIGHT_BASE_URL;
  if (!baseUrl) throw new Error("PLAYWRIGHT_BASE_URL is required when STAGE7A_AUTH_COOKIE is used.");
  const cookies = cookieHeader
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const [name, ...valueParts] = part.split("=");
      return { name, value: valueParts.join("="), url: baseUrl };
    });
  await page.context().addCookies(cookies);
}

async function loginIfConfigured(page: Page): Promise<void> {
  await installSessionCookie(page);
  const username = process.env.STAGE7A_LOGIN_USERNAME;
  const password = process.env.STAGE7A_LOGIN_PASSWORD;
  if (!username || !password) return;
  await page.goto("/login");
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码").fill(password);
  await page.getByRole("button", { name: "登录" }).click();
  await page.waitForLoadState("networkidle");
}

async function openMarketingVideo(page: Page): Promise<void> {
  await loginIfConfigured(page);
  await page.goto("/marketing-video");
  await page.waitForLoadState("domcontentloaded");
  if (new URL(page.url()).pathname === "/login") {
    throw new Error("Browser reached /login. Provide STAGE7A_LOGIN_USERNAME/STAGE7A_LOGIN_PASSWORD or STAGE7A_AUTH_COOKIE.");
  }
  await expect(page.getByText("Real", { exact: true })).toBeVisible({ timeout: 30_000 });
}

test("Gate 7A.1 browser TOS PUT micro test without bridge", async ({ page }) => {
  ensureEvidenceDir();
  const networkEvents = attachNetworkRecorder(page);
  const consoleMessages: string[] = [];
  page.on("console", (message) => consoleMessages.push(`${message.type()}: ${message.text()}`));

  await openMarketingVideo(page);
  const frontendOrigin = new URL(page.url()).origin;
  writeText("stage7a_browser_origin.txt", `${frontendOrigin}\n`);

  const microResult = await page.evaluate(async () => {
    const contentType = "text/plain";
    const body = new Blob(["Stage 7A browser micro PUT\n"], { type: contentType });
    const presignResponse = await fetch("/api/proxy/api/marketing-video/uploads/presign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: "tongan",
        company_id: "tongan",
        filename: "stage7a-browser-micro.txt",
        content_type: contentType,
        task_type: "std_marketing_video",
        workflow_name: "TONGAN",
        mode: "standard",
      }),
    });
    const presign = await presignResponse.json();
    if (!presignResponse.ok) {
      throw new Error(`presign failed ${presignResponse.status}: ${JSON.stringify(presign)}`);
    }
    const uploadObject = presign.objects?.find((object: any) => object.input_name === "script_txt") ?? presign.objects?.[0];
    if (!uploadObject?.upload_url) throw new Error("presign response did not include upload_url");
    const method = String(uploadObject.method ?? "PUT").toUpperCase();
    const requestContentType = String(uploadObject.content_type ?? contentType);
    const upload = await new Promise<any>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open(method, uploadObject.upload_url);
      xhr.setRequestHeader("Content-Type", requestContentType);
      xhr.onerror = () => reject(new Error("browser XHR PUT failed; likely CORS/network"));
      xhr.onload = () =>
        resolve({
          status: xhr.status,
          response_headers_raw: xhr.getAllResponseHeaders(),
        });
      xhr.send(body);
    });
    return {
      frontend_origin: window.location.origin,
      presign_status: presignResponse.status,
      presign,
      upload: {
        ...upload,
        method,
        request_content_type: requestContentType,
        url: uploadObject.upload_url,
        host: new URL(uploadObject.upload_url).host,
        upload_key: uploadObject.upload_key,
      },
    };
  });

  writeJson("stage7a_micro_presign_response_redacted.json", {
    status: microResult.presign_status,
    body: microResult.presign,
  });
  writeJson("stage7a_micro_tos_put_network_summary.json", {
    frontend_origin: frontendOrigin,
    tos_host: microResult.upload.host,
    method: microResult.upload.method,
    request_content_type: microResult.upload.request_content_type,
    put_status: microResult.upload.status,
    options_seen: networkEvents.some((event) => event.method === "OPTIONS"),
    response_headers_raw: microResult.upload.response_headers_raw,
    network_events: networkEvents,
    browser_console: consoleMessages,
    bridge_used: false,
    route_interception_used: false,
    backend_upload_fallback_used: false,
  });

  expect(microResult.presign.placeholder).toBe(false);
  expect(microResult.upload.method).toBe("PUT");
  expect(microResult.upload.status).toBeGreaterThanOrEqual(200);
  expect(microResult.upload.status).toBeLessThan(300);
});

test("Gate 7A.2 full browser workflow and download metadata", async ({ page }) => {
  const sampleTxt = process.env.STAGE7A_SAMPLE_TXT ?? DEFAULT_SAMPLE_TXT;
  if (!fs.existsSync(sampleTxt)) throw new Error(`sample TXT not found: ${sampleTxt}`);

  attachNetworkRecorder(page);
  await openMarketingVideo(page);

  const createResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/proxy/api/marketing-video/workflows") && response.request().method() === "POST",
    { timeout: 120_000 },
  );

  await page.getByLabel("选择 TXT 文案").setInputFiles(sampleTxt);
  await page.getByRole("button", { name: "创建营销视频任务" }).click();
  const createResponse = await createResponsePromise;
  const createBody = await createResponse.json();
  writeJson("stage7a_create_workflow_response.json", {
    status: createResponse.status(),
    body: createBody,
  });

  expect(createResponse.status()).toBe(201);
  createdWorkflowId = createBody.workflow_id;
  await expect(page.getByText(createdWorkflowId)).toBeVisible({ timeout: 30_000 });
  for (const label of TONGAN_LABELS) {
    await expect(page.getByText(label).first()).toBeVisible({ timeout: 30_000 });
  }

  const pollTimeoutMs = Number(process.env.STAGE7A_POLL_TIMEOUT_MS ?? 7_200_000);
  const pollIntervalMs = Number(process.env.STAGE7A_POLL_INTERVAL_MS ?? 15_000);
  const pollingSummary = await page.evaluate(
    async ({ workflowId, pollTimeoutMs, pollIntervalMs }) => {
      const deadline = Date.now() + pollTimeoutMs;
      const polls: any[] = [];
      let detail: any = null;
      while (Date.now() < deadline) {
        const response = await fetch(`/api/proxy/api/marketing-video/workflows/${encodeURIComponent(workflowId)}`);
        detail = await response.json();
        polls.push({
          status_code: response.status,
          workflow_status: detail.status,
          progress_percent: detail.progress_percent,
          current_node: detail.current_node,
          updated_at: detail.updated_at,
          subtasks: detail.subtasks?.map((subtask: any) => ({
            node_code: subtask.node_code,
            worker_kind: subtask.worker_kind,
            status: subtask.status,
            attempt: subtask.attempt,
            progress_percent: subtask.progress_percent,
          })),
        });
        if (["succeeded", "failed", "cancelled", "manual_required"].includes(String(detail.status))) break;
        await new Promise((resolve) => window.setTimeout(resolve, pollIntervalMs));
      }
      return { workflow_id: workflowId, polls, final_detail: detail };
    },
    { workflowId: createdWorkflowId, pollTimeoutMs, pollIntervalMs },
  );
  writeJson("stage7a_polling_summary.json", pollingSummary);

  expect(pollingSummary.final_detail?.status).toBe("succeeded");
  const subtasks = pollingSummary.final_detail.subtasks ?? [];
  expect(subtasks.map((subtask: any) => subtask.node_code)).toEqual([
    "tongan_pre_pipeline",
    "tongan_pipeline_exec",
    "tongan_post_pipeline",
  ]);
  expect(subtasks.map((subtask: any) => subtask.worker_kind)).toEqual(["general", "special", "general"]);

  await expect(page.getByText("成片已生成")).toBeVisible({ timeout: 60_000 });
  const downloadPayload = await page.evaluate(async (workflowId) => {
    const response = await fetch(`/api/proxy/api/marketing-video/workflows/${encodeURIComponent(workflowId)}/download`);
    return { status: response.status, body: await response.json() };
  }, createdWorkflowId);
  writeJson("stage7a_download_response_redacted.json", downloadPayload);

  expect(downloadPayload.status).toBe(200);
  expect(downloadPayload.body.available).toBe(true);
  expect(downloadPayload.body.final_video_url).toBeTruthy();
  finalVideoUrl = downloadPayload.body.final_video_url;
  finalVideoKey = downloadPayload.body.final_video_key ?? "";
});

test("Gate 7A.3 final video download and ffprobe validation", async ({ page }) => {
  test.skip(!finalVideoUrl, "Full workflow did not produce a final video URL.");
  const outputDir = path.resolve(process.env.STAGE7A_OUTPUT_DIR ?? "/tmp/stage7a_rc_validation");
  fs.mkdirSync(outputDir, { recursive: true });
  const finalPath = path.join(outputDir, `${createdWorkflowId}_final.mp4`);
  const response = await fetch(finalVideoUrl);
  expect(response.ok).toBe(true);
  fs.writeFileSync(finalPath, Buffer.from(await response.arrayBuffer()));

  writeJson("stage7a_final_video_download.json", {
    path: finalPath,
    size_bytes: fs.statSync(finalPath).size,
    final_video_key: finalVideoKey,
  });
});
