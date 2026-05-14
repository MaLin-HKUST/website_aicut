import { NextRequest } from "next/server";

import { getProxyTargetBaseUrl } from "@/lib/proxy-target";

type AuthUser = {
  id?: number | string;
  username?: string;
  role?: string;
  company_id?: number | string | null;
};

const TRUSTED_CONTEXT_HEADERS = ["x-aicut-company-id", "x-aicut-user-id", "x-aicut-role"];

function shouldInjectTrustedContext(path: string[]) {
  return path[0] === "api" && path[1] === "marketing-video";
}

async function getTrustedUser(request: NextRequest): Promise<AuthUser | null> {
  const legacyBaseUrl = getProxyTargetBaseUrl(["auth", "me"]);
  const cookie = request.headers.get("cookie") ?? "";
  const response = await fetch(`${legacyBaseUrl}/auth/me`, {
    headers: cookie ? { cookie } : undefined,
    cache: "no-store",
  }).catch(() => null);
  if (!response?.ok) return null;
  const payload = (await response.json().catch(() => null)) as { user?: AuthUser } | null;
  return payload?.user ?? null;
}

async function handler(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const targetPath = path.join("/");
  const targetBaseUrl = getProxyTargetBaseUrl(path);
  const url = `${targetBaseUrl}/${targetPath}${request.nextUrl.search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  for (const header of TRUSTED_CONTEXT_HEADERS) {
    headers.delete(header);
  }

  if (shouldInjectTrustedContext(path)) {
    const user = await getTrustedUser(request);
    if (user?.company_id !== undefined && user.company_id !== null) {
      headers.set("X-AICUT-Company-Id", String(user.company_id));
      headers.set("X-AICUT-User-Id", String(user.id ?? user.username ?? ""));
      headers.set("X-AICUT-Role", String(user.role ?? "user"));
    }
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    const contentType = headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      init.body = await request.text();
    } else {
      // Preserve multipart and large uploads as a stream so the proxy does not
      // buffer the full request body or break upstream writes on big files.
      init.body = request.body;
      (init as RequestInit & { duplex: "half" }).duplex = "half";
    }
  }

  const response = await fetch(url, init);
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
