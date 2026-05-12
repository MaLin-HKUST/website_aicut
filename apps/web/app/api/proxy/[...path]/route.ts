import { NextRequest } from "next/server";

import { getProxyTargetBaseUrl } from "@/lib/proxy-target";
import type { AuthResponse } from "@/lib/auth";

async function handler(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const targetPath = path.join("/");
  const targetBaseUrl = getProxyTargetBaseUrl(path);
  const targetUrl = new URL(`${targetBaseUrl}/${targetPath}${request.nextUrl.search}`);

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  headers.delete("x-aicut-user-id");
  headers.delete("x-aicut-company-id");
  headers.delete("x-aicut-role");

  const auth = shouldInjectUserContext(path) ? await fetchAuthenticatedUser(request) : null;
  if (auth?.user) {
    headers.set("X-AICUT-User-Id", auth.user.username);
    if (auth.user.company_id !== null) headers.set("X-AICUT-Company-Id", String(auth.user.company_id));
    headers.set("X-AICUT-Role", auth.user.role);
    enforceUserCompanyQuery(path, targetUrl, auth);
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    const contentType = headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      init.body = await scopedJsonBody(request, path, auth);
    } else {
      // Preserve multipart and large uploads as a stream so the proxy does not
      // buffer the full request body or break upstream writes on big files.
      init.body = request.body;
      (init as RequestInit & { duplex: "half" }).duplex = "half";
    }
  }

  const response = await fetch(targetUrl, init);
  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-length");
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("transfer-encoding");
  responseHeaders.delete("connection");

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export { handler as GET, handler as POST, handler as PUT, handler as PATCH, handler as DELETE, handler as OPTIONS };

function shouldInjectUserContext(path: string[]): boolean {
  if (path[0] !== "api") return false;
  if (path[1] === "admin") return false;
  return true;
}

async function fetchAuthenticatedUser(request: NextRequest): Promise<AuthResponse | null> {
  const authBaseUrl = getProxyTargetBaseUrl(["auth", "me"]);
  const authHeaders = new Headers(request.headers);
  authHeaders.delete("host");
  authHeaders.delete("content-length");
  authHeaders.delete("x-aicut-user-id");
  authHeaders.delete("x-aicut-company-id");
  authHeaders.delete("x-aicut-role");
  const response = await fetch(`${authBaseUrl.replace(/\/+$/, "")}/auth/me`, {
    headers: authHeaders,
    redirect: "manual",
  });
  if (!response.ok) return null;
  return (await response.json()) as AuthResponse;
}

function enforceUserCompanyQuery(path: string[], targetUrl: URL, auth: AuthResponse) {
  if (auth.user.company_id === null) return;
  const isTaskCenterList = path[0] === "api" && path[1] === "task-center" && path[2] === "tasks";
  const isSmartCutList = path[0] === "api" && path[1] === "smart-cut" && path[2] === "tasks" && path.length === 3;
  if (isTaskCenterList || isSmartCutList) {
    targetUrl.searchParams.set("company_id", String(auth.user.company_id));
  }
}

async function scopedJsonBody(request: NextRequest, path: string[], auth: AuthResponse | null): Promise<string> {
  const bodyText = await request.text();
  if (!auth?.user || auth.user.company_id === null || !shouldInjectUserContext(path)) return bodyText;
  if (!bodyText.trim()) return bodyText;
  let payload: unknown;
  try {
    payload = JSON.parse(bodyText) as unknown;
  } catch {
    return bodyText;
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return bodyText;
  const scoped: Record<string, unknown> = { ...payload, company_id: auth.user.company_id };
  if ("user_id" in scoped) scoped.user_id = auth.user.username;
  return JSON.stringify(scoped);
}
