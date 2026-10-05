// Root eslint config: base rules + frontend layer boundaries (blueprint 01 §8).
import base from "./tooling/typescript/eslint.base.mjs";
import boundaries from "./tooling/architecture/frontend/boundaries.mjs";

export default [
  ...base,
  // boundaries apply per-app; scope them to the apps that use src/ + app/ layouts
  ...boundaries.flatMap((rule) => {
    const files = (rule.files ?? []).flatMap((p) => [
      `apps/web/${p}`,
      `apps/web-next/${p}`,
      `apps/miniprogram/${p}`,
    ]);
    return [{ ...rule, files }];
  }),
];
