import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev only: proxy /api to the Python backend. Production serves the built
// SPA behind nginx which proxies /api (infra/nginx). Never use this proxy
// as the production API path (blueprint 09 §5).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
});
