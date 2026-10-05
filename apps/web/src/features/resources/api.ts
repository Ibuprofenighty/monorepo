/**
 * Feature: resources list/create/delete. Feature owns its API calls and
 * view-model mapping; pages only orchestrate.
 */
import { isOk, type ApiResult, type Problem } from "@project/api-client";
import { api } from "../../shared/api/client";
import { toViewModel, type ResourceVM } from "../../entities/resource";

export interface ResourcesState {
  items: ResourceVM[];
  total: number;
  error: Problem | null;
  failure: string | null;
}

export async function fetchResources(page = 1): Promise<ResourcesState> {
  const r = await api.listResources(page);
  if (!isOk(r)) return toState(r);
  return {
    items: r.value.items.map(toViewModel),
    total: r.value.total,
    error: null,
    failure: null,
  };
}

function toState(r: ApiResult<{ items: unknown[]; total: number }>): ResourcesState {
  if (r.ok) return { items: [], total: 0, error: null, failure: null };
  if (r.kind === "remote_problem") return { items: [], total: 0, error: r.problem, failure: null };
  if (r.kind === "cancelled") return { items: [], total: 0, error: null, failure: null };
  return { items: [], total: 0, error: null, failure: r.message };
}

/**
 * `idempotencyKey` identifies one user intent: retries of the same intent must
 * reuse it so the backend executes the create at most once.
 */
export async function createResource(
  name: string,
  idempotencyKey: string,
): Promise<{ ok: true; vm: ResourceVM } | { ok: false; problem: Problem } | { ok: false; failure: string }> {
  const r = await api.createResource({ name }, idempotencyKey);
  if (r.ok) return { ok: true, vm: toViewModel(r.value) };
  if (r.kind === "remote_problem") return { ok: false, problem: r.problem };
  if (r.kind === "cancelled") return { ok: false, failure: "cancelled" };
  return { ok: false, failure: r.message };
}

export async function deleteResource(id: string): Promise<{ ok: true } | { ok: false; code: string }> {
  const r = await api.deleteResource(id);
  if (r.ok) return { ok: true };
  if (r.kind === "remote_problem") return { ok: false, code: r.problem.code };
  return { ok: false, code: "TRANSPORT" };
}
