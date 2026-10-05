/**
 * Server transport: runs in Node (RSC / route handlers). Never imported by
 * client components — importing this from "use client" code is a review
 * blocker (blueprint 06 §2). Uses undici fetch (Node 20 built-in).
 */
import type { ApiRequest, ApiResponse, Transport } from "@project/api-client";

export class ServerTransport implements Transport {
  async send(req: ApiRequest): Promise<ApiResponse> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), req.timeoutMs);
    try {
      const res = await fetch(req.path, {
        method: req.method,
        headers: req.headers,
        body: req.body,
        signal: req.signal ?? ctrl.signal,
      });
      const headers: Record<string, string> = {};
      res.headers.forEach((v, k) => {
        headers[k] = v;
      });
      return { status: res.status, headers, body: await res.text() };
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") throw new Error("cancelled");
      throw e;
    } finally {
      clearTimeout(timer);
    }
  }
}
