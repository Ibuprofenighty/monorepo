/// <reference types="wechat-miniprogram" />
import { api } from "../../shared/api/client";
import { isOk } from "@project/api-client";

Page({
  data: { health: "…" },

  async onLoad() {
    const r = await api.getHealth();
    this.setData({ health: isOk(r) ? `ok (v${r.value.version})` : `error: ${r.kind}` });
  },

  goResources() {
    wx.navigateTo({ url: "/pages/resources/index" });
  },
});
