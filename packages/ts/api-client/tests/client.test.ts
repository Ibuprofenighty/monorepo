import { describe, expect, it } from "vitest";
import { ApiClient } from "../src/index.js";
import type { ApiRequest, ApiResponse, Transport } from "../src/index.js";

function stubTransport(respond: (req: ApiRequest) => ApiResponse): Transport {
  return {
    send: async (req) => respond(req),
  };
}

const ok = (body: unknown, status = 200): ApiResponse => ({
  status,
  headers: {},
  body: JSON.stringify(body),
});

const problem = (code: string, status: number): ApiResponse => ({
  status,
  headers: { "content-type": "application/problem+json" },
  body: JSON.stringify({
    type: `https://api.example.com/problems/x`,
    title: code,
    status,
    code,
    trace_id: "t",
  }),
});

describe("serialization", () => {
  it("parses a typed success body", async () => {
    const t = stubTransport(() => ok({ status: "ok", version: "1.0.0" }));
    const r = await new ApiClient(t).getHealth();
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value.version).toBe("1.0.0");
  });

  it("sends query params encoded", async () => {
    let seen = "";
    const t = stubTransport((req) => {
      seen = req.path;
      return ok({ items: [], total: 0, page: 2, page_size: 5 });
    });
    await new ApiClient(t).listResources(2, 5);
    expect(seen).toContain("page=2");
    expect(seen).toContain("page_size=5");
  });

  it("treats 204 as void success", async () => {
    const t = stubTransport(() => ({ status: 204, headers: {}, body: "" }));
    const r = await new ApiClient(t).deleteResource("res_1");
    expect(r).toEqual({ ok: true, value: undefined });
  });

  it("forwards the idempotency key header", async () => {
    let seen = "";
    const t = stubTransport((req) => {
      seen = req.headers["Idempotency-Key"] ?? "";
      return ok({ id: "res_1", name: "n", locked: false, created_at: "" }, 201);
    });
    await new ApiClient(t).createResource({ name: "n" }, "key-123");
    expect(seen).toBe("key-123");
  });
});

describe("problem", () => {
  it("maps a Problem response to remote_problem with the public code", async () => {
    const t = stubTransport(() => problem("CATALOG.RESOURCE_LOCKED", 409));
    const r = await new ApiClient(t).deleteResource("res_1");
    expect(r.ok).toBe(false);
    if (!r.ok && r.kind === "remote_problem") {
      expect(r.problem.code).toBe("CATALOG.RESOURCE_LOCKED");
    } else {
      throw new Error("expected remote_problem");
    }
  });

  it("accepts unknown public codes without crashing", async () => {
    const t = stubTransport(() => problem("FUTURE.UNKNOWN_CODE", 599));
    const r = await new ApiClient(t).getHealth();
    expect(r.ok).toBe(false);
    if (!r.ok && r.kind === "remote_problem") {
      expect(r.problem.code).toBe("FUTURE.UNKNOWN_CODE");
    } else {
      throw new Error("expected remote_problem");
    }
  });

  it("treats non-Problem error payloads as protocol failures", async () => {
    const t = stubTransport(() => ({ status: 502, headers: {}, body: "<html>proxy</html>" }));
    const r = await new ApiClient(t).getHealth();
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.kind).toBe("protocol_failure");
  });
});

describe("transport-contract", () => {
  it("classifies transport throws as transport_failure", async () => {
    const t: Transport = {
      send: async () => {
        throw new Error("network down");
      },
    };
    const r = await new ApiClient(t).getHealth();
    expect(r).toEqual({ ok: false, kind: "transport_failure", message: "network down" });
  });

  it("classifies adapter cancellation as cancelled", async () => {
    const t: Transport = {
      send: async () => {
        throw new Error("cancelled");
      },
    };
    const r = await new ApiClient(t).getHealth();
    expect(r).toEqual({ ok: false, kind: "cancelled" });
  });

  it("attaches the bearer token when provided", async () => {
    let seen = "";
    const t = stubTransport((req) => {
      seen = req.headers["Authorization"] ?? "";
      return ok({ status: "ok", version: "1" });
    });
    await new ApiClient(t, { token: () => "tok123" }).getHealth();
    expect(seen).toBe("Bearer tok123");
  });
});
