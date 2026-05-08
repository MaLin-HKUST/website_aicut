function getLegacyApiBaseUrl(): string {
  return process.env.LEGACY_API_BASE_URL ?? process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8000";
}

function getSmartCutApiBaseUrl(): string {
  return process.env.SMART_CUT_API_BASE_URL ?? process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8000";
}

function getMarketingVideoApiBaseUrl(): string {
  return process.env.MARKETING_VIDEO_API_BASE_URL ?? process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8000";
}

export function getProxyTargetBaseUrl(path: string[]): string {
  if (path[0] !== "api") return getLegacyApiBaseUrl();
  if (path[1] === "marketing-video") return getMarketingVideoApiBaseUrl();
  return getSmartCutApiBaseUrl();
}
