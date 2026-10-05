#!/usr/bin/env node
/**
 * Miniprogram builder: src/ → dist/ (blueprint 07 §2, §4).
 *
 * 1. tsc compiles the TS sources under src into dist (CommonJS, ES2017).
 * 2. .wxml/.wxss/.json/.wxs/.png assets are copied preserving paths.
 * 3. The workspace api-client (TS sources) is compiled into dist/api-client/
 *    and its require() calls are rewritten to relative paths.
 * 4. __API_BASE_URL__ is inlined from MP_API_BASE_URL env.
 *
 * Output is a complete, self-contained miniprogram directory:
 * WeChat DevTools and miniprogram-ci open apps/miniprogram (project.config.json
 * sets miniprogramRoot=dist/).
 */
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = resolve(HERE, "../../apps/miniprogram");
const ROOT = resolve(HERE, "../..");
const SRC = join(APP, "src");
const DIST = join(APP, "dist");
const SDK_SRC = resolve(ROOT, "packages/ts/api-client/src");
const SDK_OUT = join(DIST, "api-client");

// The app's locked TypeScript compiler, run by the current node binary (no npx/shell shims).
const TSC = createRequire(join(APP, "package.json")).resolve("typescript/bin/tsc");
const tsc = (args) => execFileSync(process.execPath, [TSC, ...args], { cwd: APP, stdio: "inherit" });

const ASSET_EXTS = new Set([".wxml", ".wxss", ".json", ".wxs", ".png", ".jpg"]);

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}

function main() {
  console.log("[mp-build] cleaning dist/");
  rmSync(DIST, { recursive: true, force: true });
  mkdirSync(DIST, { recursive: true });

  const sdkFiles = walk(SDK_SRC).filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts"));

  console.log("[mp-build] compiling @project/api-client → dist/api-client/");
  mkdirSync(SDK_OUT, { recursive: true });
  tsc([
    "--module", "commonjs",
    "--target", "es2017",
    "--moduleResolution", "node",
    "--esModuleInterop",
    "--skipLibCheck",
    "--declaration", "false",
    "--sourceMap", "false",
    "--outDir", SDK_OUT,
    "--rootDir", SDK_SRC,
    ...sdkFiles,
  ]);

  // Type declarations for the app compile: paths must NOT pull SDK sources
  // into the program (that breaks rootDir), so emit declarations to a temp dir
  // and point a generated tsconfig at them.
  const typesDir = join(APP, ".sdk-types");
  rmSync(typesDir, { recursive: true, force: true });
  console.log("[mp-build] emitting @project/api-client declarations");
  tsc([
    "--emitDeclarationOnly",
    "--declaration", "true",
    "--target", "es2017",
    "--lib", "es2017,dom",
    "--moduleResolution", "node",
    "--esModuleInterop",
    "--skipLibCheck",
    "--outDir", typesDir,
    "--rootDir", SDK_SRC,
    ...sdkFiles,
  ]);
  const tmpConfig = join(APP, "tsconfig.build.tmp.json");
  writeFileSync(
    tmpConfig,
    JSON.stringify({
      extends: "./tsconfig.build.json",
      compilerOptions: { paths: { "@project/api-client": ["./.sdk-types/index.d.ts"] } },
    }),
  );

  console.log("[mp-build] tsc src/ → dist/");
  try {
    tsc(["-p", tmpConfig]);
  } finally {
    rmSync(typesDir, { recursive: true, force: true });
    rmSync(tmpConfig, { force: true });
  }

  console.log("[mp-build] copying assets");
  for (const f of walk(SRC)) {
    const ext = f.slice(f.lastIndexOf("."));
    if (!ASSET_EXTS.has(ext)) continue;
    const rel = relative(SRC, f);
    const dest = join(DIST, rel);
    mkdirSync(dirname(dest), { recursive: true });
    cpSync(f, dest);
  }

  console.log("[mp-build] rewriting api-client requires");
  // The workspace dep name comes from apps/miniprogram/package.json
  // (e.g. @project/api-client); generated projects rename the scope.
  const pkgJson = JSON.parse(readFileSync(join(APP, "package.json"), "utf8"));
  const allDeps = { ...(pkgJson.dependencies ?? {}), ...(pkgJson.devDependencies ?? {}) };
  const sdkSpec = Object.keys(allDeps).find((k) => k.endsWith("/api-client"));
  if (!sdkSpec) {
    console.error("[mp-build] no */api-client dependency in apps/miniprogram/package.json");
    process.exit(1);
  }
  const sdkRequire = `require("${sdkSpec}")`;
  let rewritten = 0;
  for (const f of walk(DIST)) {
    if (!f.endsWith(".js") || f.startsWith(SDK_OUT)) continue;
    let text = readFileSync(f, "utf8");
    if (!text.includes(sdkSpec)) continue;
    const rel = relative(dirname(f), SDK_OUT).split(sep).join("/");
    const target = rel.startsWith(".") ? rel : `./${rel}`;
    text = text.split(sdkRequire).join(`require("${target}")`);
    writeFileSync(f, text);
    rewritten++;
  }

  const apiBase = process.env.MP_API_BASE_URL ?? "";
  console.log(`[mp-build] inlining __API_BASE_URL__=${apiBase || "(empty)"}`);
  for (const f of walk(DIST)) {
    if (!f.endsWith(".js")) continue;
    const text = readFileSync(f, "utf8");
    if (text.includes("__API_BASE_URL__")) {
      writeFileSync(f, text.split("__API_BASE_URL__").join(JSON.stringify(apiBase)));
    }
  }

  // Sanity: every page in app.json must exist in dist.
  const appJson = JSON.parse(readFileSync(join(DIST, "app.json"), "utf8"));
  const missing = [];
  for (const p of [...(appJson.pages ?? []), ...((appJson.subpackages ?? []).flatMap((s) => (s.pages ?? []).map((x) => `${s.root}/${x}`)))]) {
    for (const ext of [".js", ".wxml", ".wxss", ".json"]) {
      if (!existsSync(join(DIST, p + ext))) missing.push(p + ext);
    }
  }
  if (missing.length) {
    console.error("[mp-build] MISSING dist files:\n  " + missing.join("\n  "));
    process.exit(1);
  }
  console.log(`[mp-build] done: ${rewritten} files rewritten, dist/ is complete.`);
}

main();
