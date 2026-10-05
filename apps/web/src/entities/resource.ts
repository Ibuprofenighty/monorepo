/**
 * Entity: business representation for the UI. Built FROM the generated
 * contract type — never a second hand-written copy of it (blueprint 02 §4).
 */
import type { Resource as ResourceDTO } from "@project/api-client";

export interface ResourceVM {
  id: string;
  name: string;
  locked: boolean;
  createdAtLabel: string;
}

export function toViewModel(dto: ResourceDTO): ResourceVM {
  return {
    id: dto.id,
    name: dto.name,
    locked: dto.locked,
    createdAtLabel: new Date(dto.created_at).toLocaleString(),
  };
}
