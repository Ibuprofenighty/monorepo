import { useCallback, useEffect, useRef, useState } from "react";
import {
  createResource,
  deleteResource,
  fetchResources,
  type ResourcesState,
} from "../features/resources/api";

export function ResourcesPage() {
  const [state, setState] = useState<ResourcesState>({ items: [], total: 0, error: null, failure: null });
  const [name, setName] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  // One key per create intent: kept across retries, renewed on success or a new name.
  const createKey = useRef(crypto.randomUUID());

  const reload = useCallback(async () => {
    setState(await fetchResources(1));
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const onNameChange = (value: string) => {
    setName(value);
    createKey.current = crypto.randomUUID();
  };

  const onCreate = async () => {
    if (!name.trim() || creating) return;
    setCreating(true);
    const r = await createResource(name.trim(), createKey.current);
    setCreating(false);
    if (r.ok) {
      createKey.current = crypto.randomUUID();
      setName("");
      setNotice(null);
      await reload();
    } else if ("problem" in r) {
      setNotice(`Error ${r.problem.code}: ${r.problem.title}`);
    } else {
      setNotice(`Failed: ${r.failure}`);
    }
  };

  const onDelete = async (id: string) => {
    const r = await deleteResource(id);
    if (r.ok) {
      await reload();
    } else {
      // Branch on the PUBLIC code, never on English text (blueprint 03 §8).
      setNotice(r.code === "CATALOG.RESOURCE_LOCKED" ? "Resource is locked — cannot delete." : `Error ${r.code}`);
    }
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Resources</h1>
      {notice && <p role="alert" style={{ color: "crimson" }}>{notice}</p>}
      {state.error && <p role="alert">Error {state.error.code}</p>}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input value={name} onChange={(e) => onNameChange(e.target.value)} placeholder="New resource name" />
        <button onClick={onCreate} disabled={creating}>
          Create
        </button>
      </div>
      <ul>
        {state.items.map((it) => (
          <li key={it.id}>
            {it.name} {it.locked ? "🔒" : ""} <small>({it.createdAtLabel})</small>{" "}
            <button onClick={() => onDelete(it.id)}>Delete</button>
          </li>
        ))}
      </ul>
      <p>Total: {state.total}</p>
    </main>
  );
}
