import { useEffect, useState } from "react";
import { api } from "../shared/api/client";
import { isOk } from "@project/api-client";

export function HomePage() {
  const [health, setHealth] = useState<string>("…");

  useEffect(() => {
    api
      .getHealth()
      .then((r) => setHealth(isOk(r) ? `ok (v${r.value.version})` : `error: ${r.kind}`))
      .catch(() => setHealth("unreachable"));
  }, []);

  return (
    <main style={{ padding: 24 }}>
      <h1>Project</h1>
      <p>
        API status: <strong data-testid="api-health">{health}</strong>
      </p>
      <p>Headless backend owns all business logic; this SPA is a thin client.</p>
    </main>
  );
}
