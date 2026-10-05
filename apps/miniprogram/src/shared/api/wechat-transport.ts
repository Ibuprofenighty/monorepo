/// <reference types="wechat-miniprogram" />
/**
 * wx.request transport adapter (blueprint 07 §5). The ONLY file here that
 * touches wx.*. No DOM, no fetch, no window.
 */
import type { ApiRequest, ApiResponse, Transport } from "@project/api-client";

function normalizeHeaders(h: WechatMiniprogram.IAnyObject): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of Object.keys(h)) out[k.toLowerCase()] = String(h[k]);
  return out;
}

export class WechatTransport implements Transport {
  send(req: ApiRequest): Promise<ApiResponse> {
    // wx.request has no PATCH; fail loudly instead of mistranslating.
    const method = req.method;
    if (method === "PATCH") {
      return Promise.reject(new Error("wx.request does not support PATCH"));
    }
    return new Promise((resolve, reject) => {
      const task = wx.request({
        url: req.path,
        method,
        header: req.headers,
        data: req.body,
        timeout: req.timeoutMs,
        success: (res) => {
          const body =
            typeof res.data === "string" ? res.data : JSON.stringify(res.data ?? "");
          resolve({ status: res.statusCode, headers: normalizeHeaders(res.header), body });
        },
        fail: (err) => {
          // err.errMsg like "request:fail timeout" — never leak raw text to UI.
          reject(new Error(`request failed: ${err.errMsg ?? "unknown"}`));
        },
      });
      // Bridge SDK cancellation: abort the wx task.
      req.signal?.addEventListener("abort", () => {
        task.abort();
        reject(new Error("cancelled"));
      });
    });
  }
}
