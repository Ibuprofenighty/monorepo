# 2026-10-05 · 工具链单源与合并门禁

## 变更

- Node 的版本字符串只在 `.node-version`。CI 使用 `node-version-file: .node-version`。pnpm 的版本只在 `package.json` 的 `packageManager`，workflow 不再写 `version`。Python 的版本只在 `.python-version`，backend 镜像的 `ARG PYTHON_VERSION` 必须等于它。Flutter 的版本在 `.flutter-version`，CI 读该文件。Postgres 与 Redis 的镜像只在 `infra/compose/compose.yaml`，CI service 使用同一行。
- `make verify` 包含契约、生成物、静态检查、测试、Dart、客户端构建、端到端、镜像构建、Trivy 扫描和 SBOM。`verify-release` 与 `verify` 相同。`.github/workflows/ci.yaml` 只调用这些目标。`make check-gate` 在两边集合不一致时失败。
- 根目录 `LICENSE` 为 MIT。

## 已生成项目同步

本条目写入时不存在已生成项目。此后生成的项目包含本目录，按后续条目手工合并。

若有仓库是在本条目之前从母版复制的，对齐这些表面：

- `.node-version`、`.python-version`、`.flutter-version`、`package.json` 的 `packageManager` 与 `engines.node`
- `.github/workflows/ci.yaml`：`node-version-file`、`flutter-version-file`，以及与 `make verify` 相同的 `make` 目标
- `Makefile` 的 `verify` 目标
- `scripts/quality/check_toolchain.py`、`scripts/quality/check_gate.py`
- 根目录 `LICENSE`
