#!/usr/bin/env node
/**
 * Upload the built miniprogram as a versioned artifact via the miniprogram-ci
 * Node API (blueprint 07 §6). Protected environments only; MP_VERSION comes
 * from CI, never hand-typed. Env: MP_VERSION, optional MP_VERSION_DESC, plus
 * ci-project.mjs.
 */
import { ci, createProject, requireEnv, robot } from "./ci-project.mjs";

requireEnv(["MP_VERSION"]);
const project = createProject();
const version = process.env.MP_VERSION;
const result = await ci.upload({
  project,
  version,
  desc: process.env.MP_VERSION_DESC ?? `release ${version}`,
  setting: { useProjectConfig: true },
  robot: robot(),
  onProgressUpdate: (task) => console.log("[mp-upload]", typeof task === "string" ? task : task.message),
});
console.log("[mp-upload] done", JSON.stringify(result.subPackageInfo ?? []));
