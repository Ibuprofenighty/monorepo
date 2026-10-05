/// <reference types="wechat-miniprogram" />
/**
 * Subpackage example: catalog/resource-detail (blueprint 07 §3).
 * Demonstrates independentSubpackage-ready structure; keep subpackages
 * dependency-free from main-package pages.
 */
import { api } from "../../../../shared/api/client";
import { isOk } from "@project/api-client";

Page({
  data: { name: "…", error: "" },

  async onLoad(query: Record<string, string>) {
    const id = query.id ?? "";
    const r = await api.getResource(id);
    if (isOk(r)) {
      this.setData({ name: r.value.name });
    } else {
      this.setData({ error: r.kind === "remote_problem" ? r.problem.code : r.kind });
    }
  },
});
