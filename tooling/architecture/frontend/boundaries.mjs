// Frontend boundary rules (blueprint 01 §8, 05 §4, 06 §2, 07 §4).
// Shared by apps/web and apps/web-next via eslint.config.mjs:
//   import boundaries from "../../tooling/architecture/frontend/boundaries.mjs"
//
// Layers (bottom → top):
//   shared/api      — transport adapters + ApiClient singleton (no UI imports)
//   shared/config   — build-time config (no secrets, no UI imports)
//   features/*      — mapping + orchestration (no platform globals: no wx.*, no window)
//   pages|app       — thin UI glue (may import features + shared)
export default [
  {
    // shared/api must not import UI or feature code.
    files: ["src/shared/api/**/*.ts"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            { group: ["**/features/**"], message: "shared/api must not import features (01 §8)" },
            { group: ["react", "react-dom", "**/*.tsx"], message: "shared/api must not import UI" },
          ],
        },
      ],
    },
  },
  {
    // features must not touch platform globals directly.
    files: ["src/features/**/*.ts"],
    rules: {
      "no-restricted-globals": [
        "error",
        { name: "wx", message: "features must not use wx.* — pages own platform glue (07 §4)" },
        { name: "window", message: "features must not use window — inject via shared/api (05 §4)" },
        { name: "document", message: "features must not use document — inject via shared/api (05 §4)" },
      ],
    },
  },
  {
    // The raw server transport (reads INTERNAL_API_URL) may only be wired
    // through shared/api/server-client.ts. Pages import the singleton, never
    // the transport module directly — this keeps server-only config out of
    // client bundles (06 §2).
    files: ["src/**/*", "app/**/*"],
    ignores: ["src/shared/api/server-client.ts", "src/shared/api/server.ts"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["**/shared/api/server"],
              message: "import the server-client singleton, not the raw server transport (06 §2)",
            },
          ],
        },
      ],
    },
  },
];
