/**
 * Build-time config. Values are inlined by scripts/miniprogram/build.mjs
 * from environment (never committed secrets — blueprint 08 §7).
 */
declare const __API_BASE_URL__: string;

export const apiBaseUrl: string =
  typeof __API_BASE_URL__ !== "undefined" ? __API_BASE_URL__ : "";
