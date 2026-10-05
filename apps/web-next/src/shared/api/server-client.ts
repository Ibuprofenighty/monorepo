/**
 * Server-side ApiClient singleton. INTERNAL_API_URL is server-only config —
 * never NEXT_PUBLIC_* here (blueprint 08 §7).
 */
import { ApiClient } from "@project/api-client";
import { ServerTransport } from "./server";

const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

export const serverApi = new ApiClient(new ServerTransport(), { baseUrl });
