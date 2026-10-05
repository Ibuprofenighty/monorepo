/**
 * App-wide ApiClient singleton. Base URL + token wiring lives here —
 * pages/features only import this, never fetch() directly.
 */
import { ApiClient } from "@project/api-client";
import { BrowserTransport } from "./browser-transport";
import { apiBaseUrl } from "../config/env";

function loadToken(): string | undefined {
  try {
    return sessionStorage.getItem("access_token") ?? undefined;
  } catch {
    return undefined;
  }
}

export const api = new ApiClient(new BrowserTransport(), {
  baseUrl: apiBaseUrl,
  token: loadToken,
});
