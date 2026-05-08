import { NextRequest } from "next/server";

import { getProxyTargetBaseUrl } from "@/lib/proxy-target";

async function handler(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const targetPath = path.join("/");
  const targetBaseUrl = getProxyTargetBaseUrl(path);
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
