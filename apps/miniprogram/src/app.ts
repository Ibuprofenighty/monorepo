/// <reference types="wechat-miniprogram" />
import { api } from "./shared/api/client";

App({
  globalData: { apiBaseUrl: "" },

  async onLaunch() {
    // Fail-fast connectivity check; real auth flow goes through wx.login
    // → backend session exchange (blueprint 07 §5), not embedded here.
    const r = await api.getHealth();
    console.log("[app] api health:", r.ok ? "ok" : r.kind);
  },
});
