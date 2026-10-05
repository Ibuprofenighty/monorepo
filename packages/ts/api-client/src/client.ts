/**
 * Typed API client built on the GENERATED contract types.
 * No hand-written duplicates of HTTP types (blueprint 02 §4).
 */
import type { components } from "./generated/schema";
import { parseProblem, type Problem } from "./runtime/problem";
import type { ApiResult } from "./runtime/result";
import type { ApiRequest, Transport } from "./runtime/transport";

export type Health = components["schemas"]["Health"];
export type Resource = components["schemas"]["Resource"];
export type ResourceCreate = components["schemas"]["ResourceCreate"];
export type ResourceList = components["schemas"]["ResourceList"];

export interface ClientOptions {
  /** e.g. "https://api.example.com". Empty = same-origin / dev proxy. */
  baseUrl?: string;
  /** Called per request; return undefined for anonymous calls. */
  token?: () => string | undefined;
  timeoutMs?: number;
}

function encodeQuery(params: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly token?: () => string | undefined;

  constructor(
    private readonly transport: Transport,
    opts: ClientOptions = {},
  ) {
    this.baseUrl = opts.baseUrl ?? "";
    this.timeoutMs = opts.timeoutMs ?? 15000;
    this.token = opts.token;
  }

  private async request<T>(
    method: ApiRequest["method"],
    path: string,
    opts: {
      query?: Record<string, string | number | undefined>;
      body?: unknown;
      headers?: Record<string, string>;
      signal?: AbortSignal;
    } = {},
  ): Promise<ApiResult<T>> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(opts.headers ?? {}),
    };
    const token = this.token?.();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    let body: string | undefined;
    if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(opts.body);
    }

    let res;
    try {
      res = await this.transport.send({
        method,
        path: `${this.baseUrl}${path}${encodeQuery(opts.query ?? {})}`,
        headers,
        body,
        timeoutMs: this.timeoutMs,
        signal: opts.signal,
      });
    } catch (e) {
      // DOM runtimes signal cancellation via AbortError; other adapters
      // (e.g. miniprogram) throw Error("cancelled"). Guard the DOMException
      // reference — it doesn't exist outside browsers.
      const isDomAbort =
        typeof DOMException !== "undefined" && e instanceof DOMException && e.name === "AbortError";
      if (isDomAbort) return { ok: false, kind: "cancelled" };
      // Non-DOM environments (miniprogram): adapters throw Error("cancelled").
      if (e instanceof Error && e.message === "cancelled") return { ok: false, kind: "cancelled" };
      return { ok: false, kind: "transport_failure", message: e instanceof Error ? e.message : String(e) };
    }

    if (res.status === 204) return { ok: true, value: undefined as T };

    const problem: Problem | null =
      res.status >= 400 ? parseProblem(res.body) : null;
    if (problem) return { ok: false, kind: "remote_problem", problem };

    if (res.status >= 200 && res.status < 300) {
      try {
        return { ok: true, value: JSON.parse(res.body) as T };
      } catch {
        return { ok: false, kind: "protocol_failure", message: `invalid JSON on ${method} ${path}` };
      }
    }
    // Non-Problem error payload (proxy HTML etc.) → protocol failure, not a business error.
    return {
      ok: false,
      kind: "protocol_failure",
      message: `unexpected status ${res.status} on ${method} ${path}`,
    };
  }

  getHealth(signal?: AbortSignal): Promise<ApiResult<Health>> {
    return this.request<Health>("GET", "/api/v1/health", { signal });
  }

  listResources(
    page = 1,
    pageSize = 20,
    signal?: AbortSignal,
  ): Promise<ApiResult<ResourceList>> {
    return this.request<ResourceList>("GET", "/api/v1/resources", {
      query: { page, page_size: pageSize },
      signal,
    });
  }

  createResource(
    input: ResourceCreate,
    idempotencyKey?: string,
    signal?: AbortSignal,
  ): Promise<ApiResult<Resource>> {
    return this.request<Resource>("POST", "/api/v1/resources", {
      body: input,
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {},
      signal,
    });
  }

  getResource(id: string, signal?: AbortSignal): Promise<ApiResult<Resource>> {
    return this.request<Resource>("GET", `/api/v1/resources/${encodeURIComponent(id)}`, { signal });
  }

  deleteResource(id: string, signal?: AbortSignal): Promise<ApiResult<void>> {
    return this.request<void>("DELETE", `/api/v1/resources/${encodeURIComponent(id)}`, { signal });
  }
}
