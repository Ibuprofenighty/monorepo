import { describe, expect, it } from "vitest";
import { toVM } from "../../src/features/resources/api";
import { errorCopy } from "../../src/shared/api/client-errors";

describe("miniprogram feature mapping", () => {
  it("maps DTO to view model", () => {
    expect(toVM({ id: "1", name: "n", locked: false, created_at: "" })).toEqual({
      id: "1",
      name: "n",
      locked: false,
    });
  });

  it("centralizes error copy and falls back safely", () => {
    expect(errorCopy("CATALOG.RESOURCE_LOCKED")).toContain("锁定");
    expect(errorCopy("FUTURE.UNKNOWN")).toBe(errorCopy("INTERNAL"));
  });
});
