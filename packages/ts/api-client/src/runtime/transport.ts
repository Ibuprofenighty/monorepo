/**
 * Platform-agnostic transport contract (blueprint 02 §5).
 *
 * The public SDK never touches window, DOM Response, wx, or localStorage.
 * Each client injects an adapter:
 *   web (vite)      → apps/web/src/shared/api/browser-transport.ts
 *   web (next/ssr)   → apps/web-next/src/shared/api/server.ts
 *   miniprogram     → apps/miniprogram/src/shared/api/wechat-transport.ts
 *
 * Pure data in, pure data out. Cancellation uses an AbortSignal where the
 * platform supports it; adapters that can't cancel must document it.
 */
export interface ApiRequest {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** Path relative to the API root, e.g. "/api/v1/resources". Query already encoded. */
  path: string;
  headers: Record<string, string>;
  /** Pre-serialized body (JSON string). Undefined for bodyless requests. */
  body?: string;
  timeoutMs: number;
  signal?: AbortSignal;
}

export interface ApiResponse {
  status: number;
  headers: Record<string, string>;
  /** Raw body text. May be "" (e.g. 204). */
  body: string;
}

export interface Transport {
  send(req: ApiRequest): Promise<ApiResponse>;
}
