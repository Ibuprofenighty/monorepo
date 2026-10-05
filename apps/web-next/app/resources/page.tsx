import { serverApi } from "@/shared/api/server-client";
import { isOk } from "@project/api-client";

export default async function ResourcesPage() {
  const r = await serverApi.listResources(1, 20);
  const items = isOk(r) ? r.value.items : [];
  return (
    <main style={{ padding: 24 }}>
      <h1>Resources</h1>
      {!isOk(r) && <p role="alert">Failed to load: {r.kind}</p>}
      <ul>
        {items.map((it) => (
          <li key={it.id}>
            {it.name} {it.locked ? "🔒" : ""}
          </li>
        ))}
      </ul>
    </main>
  );
}
