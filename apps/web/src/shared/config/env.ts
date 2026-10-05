/**
 * Public (browser-safe) config. VITE_* values are baked into the bundle —
 * never put server secrets here (blueprint 08 §7).
 */
export const apiBaseUrl: string = import.meta.env.VITE_API_URL ?? "";
