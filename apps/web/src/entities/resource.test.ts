import { describe, expect, it } from "vitest";
import { toViewModel } from "./resource";

describe("resource entity", () => {
  it("maps the contract DTO to a view model without duplicating types", () => {
    const vm = toViewModel({
      id: "res_1",
      name: "n",
      locked: true,
      created_at: "2026-10-02T12:00:00Z",
    });
    expect(vm.id).toBe("res_1");
    expect(vm.locked).toBe(true);
    expect(vm.createdAtLabel).toContain("2026");
  });
});
