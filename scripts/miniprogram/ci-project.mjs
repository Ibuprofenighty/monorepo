/**
 * Shared miniprogram-ci setup for preview.mjs / upload.mjs (blueprint 07 §6).
 *
 * miniprogram-ci is a locked devDependency of apps/miniprogram. projectPath is
 * the directory holding project.config.json (apps/miniprogram); that file's
 * miniprogramRoot (dist/) selects the built code, so run build.mjs first.
 *
 * Env: MP_APPID, MP_PRIVATE_KEY (path to the code-upload key file, never
 * committed), optional MP_ROBOT (1-30, default 1).
 */
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
export const APP = resolve(HERE, "../../apps/miniprogram");

export const ci = createRequire(join(APP, "package.json"))("miniprogram-ci");

export function requireEnv(names) {
  const missing = names.filter((n) => !process.env[n]);
  if (missing.length) {
    console.error(`[mp-ci] missing env: ${missing.join(", ")}`);
    process.exit(1);
  }
}

export function createProject() {
  requireEnv(["MP_APPID", "MP_PRIVATE_KEY"]);
  if (!existsSync(process.env.MP_PRIVATE_KEY)) {
    console.error("[mp-ci] MP_PRIVATE_KEY does not point to an existing key file");
    process.exit(1);
  }
  if (!existsSync(join(APP, "dist", "app.json"))) {
    console.error("[mp-ci] apps/miniprogram/dist is missing — run: make mp-build");
    process.exit(1);
  }
  return new ci.Project({
    appid: process.env.MP_APPID,
    type: "miniProgram",
    projectPath: APP,
    privateKeyPath: process.env.MP_PRIVATE_KEY,
    ignores: ["node_modules/**/*"],
  });
}

export function robot() {
  const n = Number(process.env.MP_ROBOT ?? "1");
  if (!Number.isInteger(n) || n < 1 || n > 30) {
    console.error("[mp-ci] MP_ROBOT must be an integer in 1..30");
    process.exit(1);
  }
  return n;
}
