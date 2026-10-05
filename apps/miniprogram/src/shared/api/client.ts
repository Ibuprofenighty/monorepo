/// <reference types="wechat-miniprogram" />
/**
 * App-wide ApiClient. Token storage: wx.getStorageSync("access_token").
 * wx.login → backend code2session exchange happens at login time;
 * this file only READS the stored token (blueprint 07 §5, 08 §4).
 */
import { ApiClient } from "@project/api-client";
import { WechatTransport } from "./wechat-transport";
import { apiBaseUrl } from "../config/env";

function loadToken(): string | undefined {
  try {
    return wx.getStorageSync("access_token") || undefined;
  } catch {
    return undefined;
  }
}

export const api = new ApiClient(new WechatTransport(), {
  baseUrl: apiBaseUrl,
  token: loadToken,
});
