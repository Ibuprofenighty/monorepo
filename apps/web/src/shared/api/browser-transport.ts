/**
 * Browser transport adapter (blueprint 02 §5). The ONLY file in this app
 * that touches fetch/DOM. Everything else talks to ApiClient.
 */
import type { ApiRequest, ApiResponse, Transport } from "@project/api-client";

export class BrowserTransport implements Transport {
  async send(req: ApiRequest): Promise<ApiResponse> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), req.timeoutMs);
    // Bridge platform cancellation into the SDK's AbortSignal contract.
    req.signal?.addEventListener("abort", () => ctrl.abort());
    try {
      const res = await fetch(req.path, {
        method: req.method,
        headers: req.headers,
        body: req.body,
        signal: ctrl.signal,
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
