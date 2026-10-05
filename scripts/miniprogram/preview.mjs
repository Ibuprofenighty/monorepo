#!/usr/bin/env node
/**
 * Preview the built miniprogram via the miniprogram-ci Node API (blueprint 07 §6).
 * Prints the preview QR code in the terminal. Env: see ci-project.mjs.
 */
import { ci, createProject, robot } from "./ci-project.mjs";

const project = createProject();
const result = await ci.preview({
  project,
  desc: process.env.MP_VERSION_DESC ?? "preview build",
  setting: { useProjectConfig: true },
  qrcodeFormat: "terminal",
  robot: robot(),
  onProgressUpdate: (task) => console.log("[mp-preview]", typeof task === "string" ? task : task.message),
});
console.log("[mp-preview] done", JSON.stringify(result.subPackageInfo ?? []));
