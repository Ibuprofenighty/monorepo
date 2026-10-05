import { serverApi } from "@/shared/api/server-client";
import { isOk } from "@project/api-client";

export default async function HomePage() {
  const r = await serverApi.getHealth();
  const status = isOk(r) ? `ok (v${r.value.version})` : `error: ${r.kind}`;
  return (
    <main style={{ padding: 24 }}>
      <h1>Project</h1>
      <p>
        API status: <strong data-testid="api-health">{status}</strong>
      </p>
      <p>Server Component fetches through the same ApiClient via a server transport.</p>
    </main>
  );
}
