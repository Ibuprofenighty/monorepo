/**
 * RFC 9457 problem+json parsing (blueprint 03 §4).
 * Unknown public codes are accepted and surfaced — never crash the client (03 §7).
 */
export interface Problem {
  type: string;
  title: string;
  status: number;
  /** Stable public code, e.g. "CATALOG.RESOURCE_LOCKED". */
  code: string;
  detail?: string;
  instance?: string;
  trace_id?: string;
}

export function isProblemBody(value: unknown): value is Problem {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v["type"] === "string" &&
    typeof v["title"] === "string" &&
    typeof v["status"] === "number" &&
    typeof v["code"] === "string"
  );
}

export function parseProblem(text: string): Problem | null {
  try {
    const v: unknown = JSON.parse(text);
    return isProblemBody(v) ? v : null;
  } catch {
    return null;
  }
}
