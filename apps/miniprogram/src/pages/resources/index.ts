/// <reference types="wechat-miniprogram" />
import { fetchResources, deleteResource } from "../../features/resources/api";

interface ItemVM {
  id: string;
  name: string;
  locked: boolean;
}

Page({
  data: { items: [] as ItemVM[], error: "" as string, notice: "" as string },

  async onLoad() {
    await this.reload();
  },

  async reload() {
    const s = await fetchResources(1);
    this.setData({
      items: s.items,
      error: s.error ? `Error ${s.error.code}` : s.failure ?? "",
    });
  },

  async onDelete(e: WechatMiniprogram.TouchEvent) {
    const id = (e.currentTarget.dataset as { id: string }).id;
    const r = await deleteResource(id);
    if (r.ok) {
      await this.reload();
    } else {
      this.setData({
        notice: r.code === "CATALOG.RESOURCE_LOCKED" ? "资源已锁定，无法删除" : `错误 ${r.code}`,
      });
    }
  },
});
