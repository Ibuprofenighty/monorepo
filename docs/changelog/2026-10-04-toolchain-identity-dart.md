# 2026-10-04 · 工具链、身份裁剪、Dart 子集

## 变更

- Node 固定为 `.node-version` 里的 `24.11.1`。CI `node-version`、`package.json` 的 `engines.node`、`infra/docker/web.Dockerfile` 的 `ARG NODE_VERSION` 与该文件相同。镜像使用 `node:24.11.1-bookworm-slim` 的索引摘要 `sha256:48abc13a19400ca3985071e287bd405a1d99306770eb81d61202fb6b65cf0b57`。`make check-toolchain` 与 `make bootstrap` 核对这几处；门禁不访问镜像仓库。
- 身份在生成时选定一个 verifier：`local`、`wechat` 或 `keycloak`。`platform/authn/active.py` 是唯一导入点。`wechat-native` 要求 `identity: wechat`。`worker` 要求 `redis`。未勾选的能力从 compose、CI、readiness 和 worker 入口删除。`storage` 与 `llm` 没有 canonical 实现，勾选则生成失败。aws / gcp / azure / alibaba 还不是可选项。
- `wechat` 用 code2session 换 openid，再签发应用自己的 HS256 会话。`session_key` 与 app secret 不离开服务端。`keycloak` 用 realm JWKS 本地校验 RS256 access token（`typ: Bearer`），不签发 token。
- Dart 生成器接受 string enum（值必须是 Dart 标识符）和仅含 `additionalProperties` schema 的 map。`oneOf` / `anyOf` / `allOf`、`additionalProperties: true`、其它 `format`、以及会改变形态的未知关键字都会失败。`minLength` 等约束写进契约，Dart 模型不复查。
- 未勾选 redis 时，生成项目的 `pyproject.toml` 不含 `redis`；未勾选 worker 时不含 `arq`，也没有定时清理幂等记录的 worker。生成器随后在该项目执行 `uv lock`。母版仓库仍提交 `uv.lock`，供 `--frozen` 安装使用。

## 已生成项目同步

本条目写入时不存在已生成项目。此后生成的项目包含本目录，按后续条目手工合并。

若有仓库是在本条目之前从母版复制的，对齐这些表面：

- `.node-version`、`package.json` 的 `engines.node`、`.github/workflows/ci.yaml` 的 `node-version`、`infra/docker/web.Dockerfile` 的 `NODE_VERSION` 与 `NODE_DIGEST`
- `platform/authn/`：`active.py` 加 `verifiers/`，只保留选定身份；调用方改为导入 `active`
- 未勾选的 redis / worker：compose、CI service、readiness、`entrypoints/worker.py`，以及 `pyproject.toml` 里对应依赖和重新生成的 `uv.lock`
- `packages/dart/api_client/lib/src/generated/models.dart` 只通过 `make generate` 更新
- `docs/changelog/` 整目录
