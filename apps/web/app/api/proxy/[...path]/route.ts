import { NextRequest } from "next/server";

const LEGACY_API_BASE_URL = process.env.LEGACY_API_BASE_URL ?? process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8000";
const SMART_CUT_API_BASE_URL =
  process.env.SMART_CUT_API_BASE_URL ?? process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8000";
const MARKETING_VIDEO_API_BASE_URL =
  process.env.MARKETING_VIDEO_API_BASE_URL ?? process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8000";

function getTargetBaseUrl(path: string[]): string {
  if (path[0] !== "api") return LEGACY_API_BASE_URL;
  if (path[1] === "marketing-video") return MARKETING_VIDEO_API_BASE_URL;
  return SMART_CUT_API_BASE_URL;
}

async function handler(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const targetPath = path.join("/");
  const targetBaseUrl = getTargetBaseUrl(path);
  const url = `${targetBaseUrl}/${targetPath}${request.nextUrl.search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");

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
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
  });
}

export { handler as GET, handler as POST, handler as PUT, handler as PATCH, handler as DELETE, handler as OPTIONS };
