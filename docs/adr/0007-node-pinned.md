# 0007 · Node 24.11.1 锁定，零漂移

状态：已接受
日期：2026-10-03
决策人：Mengshi（用户确认）

## 背景

Node 20 已于 2026-04-30 结束维护。版本号如果在 CI、镜像和本地各写一份，就会漂。

## 决策

Node 固定为 **24.11.1**。`.node-version` 是版本字符串的唯一来源，其余位置必须等于它：

- `.github/workflows/ci.yaml` 的每个 `node-version`
- `package.json` 的 `engines.node`
- `infra/docker/web.Dockerfile` 的 `ARG NODE_VERSION`（完整版本，不是 `24`）

Web 镜像两处 `FROM` 都是：

```dockerfile
FROM node:${NODE_VERSION}-bookworm-slim@${NODE_DIGEST}
```

`NODE_DIGEST` 是 `node:24.11.1-bookworm-slim` 的**索引**摘要，不是某一平台的 manifest，也不是浮动标签 `node:24-bookworm-slim`：

`sha256:48abc13a19400ca3985071e287bd405a1d99306770eb81d61202fb6b65cf0b57`

`scripts/quality/check_toolchain.py` 核对上述接线。它不访问镜像仓库。升级 Node 时同时改 `.node-version` 和该脚本里的索引摘要，再跑 `make check-toolchain`。`make bootstrap` 要求 `node --version` 等于 `v` 加 `.node-version`。

## 备选方案

- 用 `24.x` 或 `node:24` 浮动标签：两次构建可以不是同一份镜像。否决。

## 后果

- Node 升级要改版本文件和记录在门禁里的索引摘要，否则 CI 红。
- 本地用 `nvm` / `fnm` 读取 `.node-version`。

## 关联

- 契约/错误码/权限/数据影响：无（工具链）
- 相关 spec：—
