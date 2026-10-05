/**
 * Feature: resources. Pure mapping + orchestration around the shared client.
 * No wx.* here — pages own the platform glue.
 */
import { isOk, type Problem, type Resource as ResourceDTO } from "@project/api-client";
import { api } from "../../shared/api/client";

export interface ItemVM {
  id: string;
  name: string;
  locked: boolean;
}

export function toVM(dto: ResourceDTO): ItemVM {
  return { id: dto.id, name: dto.name, locked: dto.locked };
}

export interface ListState {
  items: ItemVM[];
  error: Problem | null;
  failure: string | null;
}

export async function fetchResources(page = 1): Promise<ListState> {
  const r = await api.listResources(page);
  if (isOk(r)) return { items: r.value.items.map(toVM), error: null, failure: null };
  if (r.kind === "remote_problem") return { items: [], error: r.problem, failure: null };
  if (r.kind === "cancelled") return { items: [], error: null, failure: null };
  return { items: [], error: null, failure: r.message };
}

export async function deleteResource(
  id: string,
): Promise<{ ok: true } | { ok: false; code: string }> {
  const r = await api.deleteResource(id);
  if (r.ok) return { ok: true };
  if (r.kind === "remote_problem") return { ok: false, code: r.problem.code };
  return { ok: false, code: "TRANSPORT" };
}
