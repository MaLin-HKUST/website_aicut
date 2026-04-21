import { NextRequest, NextResponse } from "next/server";

const LEGACY_API_BASE_URL = process.env.LEGACY_API_BASE_URL ?? process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8000";

type LoginResponse = {
  user?: {
    role?: "admin" | "user";
  };
  detail?: string;
};

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const username = String(formData.get("username") ?? "");
  const password = String(formData.get("password") ?? "");

  const upstream = await fetch(`${LEGACY_API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
    redirect: "manual",
  });

  if (!upstream.ok) {
    const payload = ((await upstream.json().catch(() => null)) as LoginResponse | null) ?? null;
    const location = new URLSearchParams();
    if (payload?.detail) {
      location.set("error", payload.detail);
    } else {
      location.set("error", "登录失败");
    }
    const response = new NextResponse(null, { status: 303 });
    response.headers.set("location", `/login?${location.toString()}`);
    return response;
  }

  const payload = (await upstream.json()) as LoginResponse;
  const response = new NextResponse(null, { status: 303 });
  response.headers.set("location", payload.user?.role === "admin" ? "/admin" : "/welcome");

  if (typeof (upstream.headers as Headers & { getSetCookie?: () => string[] }).getSetCookie === "function") {
    const cookies = (upstream.headers as Headers & { getSetCookie: () => string[] }).getSetCookie();
    for (const cookie of cookies) {
      response.headers.append("set-cookie", cookie);
    }
  } else {
    const cookie = upstream.headers.get("set-cookie");
    if (cookie) {
      response.headers.set("set-cookie", cookie);
    }
  }

  return response;
}
