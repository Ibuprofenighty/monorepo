/**
 * Client failure protocol (blueprint 03 §7). Callers branch on `kind`,
 * never on English detail text.
 */
import type { Problem } from "./problem";

export type ApiResult<T> =
  | { ok: true; value: T }
  | { ok: false; kind: "remote_problem"; problem: Problem }
  | { ok: false; kind: "transport_failure"; message: string }
  | { ok: false; kind: "protocol_failure"; message: string }
  | { ok: false; kind: "cancelled" };

export function isOk<T>(r: ApiResult<T>): r is { ok: true; value: T } {
  return r.ok;
}
