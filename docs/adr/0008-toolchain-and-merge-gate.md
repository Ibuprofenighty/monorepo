# 0008 · 工具链单源，`make verify` 是唯一合并门禁

状态：已接受
日期：2026-10-05
决策人：Mengshi（用户确认）

## 背景

库依赖由 `uv.lock` 和 `pnpm-lock.yaml` 锁定。工具链和镜像如果在 CI、Dockerfile 和本机各写一份，就可以各改各的。合并如果另有一套命令，绿的 CI 就不能代表 `make verify`。

## 决策

每个工具链只有一个权威文件。其余位置只许被核对，不许再写一套版本：

| 工具 | 权威 | 必须与权威相同的副本 |
|---|---|---|
| Node | `.node-version` | `package.json` 的 `engines.node`；web 镜像的 `ARG NODE_VERSION`。CI 使用 `node-version-file: .node-version` |
| pnpm | `package.json` 的 `packageManager` | CI 的 `pnpm/action-setup` 不写 `version` |
| Python | `.python-version` | backend 镜像的 `ARG PYTHON_VERSION`。镜像摘要只写在该 Dockerfile |
| Flutter | `.flutter-version` | CI 使用 `flutter-version-file: .flutter-version`，不写 channel。`pubspec.yaml` 的 `flutter:` 是兼容下限，钉死的版本必须不低于它 |
| Postgres / Redis | `infra/compose/compose.yaml` 的 `image:` | CI service 的同名镜像 |

Node 索引摘要仍记录在 `scripts/quality/check_toolchain.py`，因为门禁不访问镜像仓库。0007 的版本号来源不变；CI 里的版本字面量由本 ADR 取代。

同一个 GitHub Action 在 `.github/workflows/` 里出现多次时，SHA 必须相同。

`make verify` 是唯一合并集合。GitHub CI 的每个 `run` 只能是该集合里的目标，或锁文件安装（`pnpm install --frozen-lockfile`、`uv sync --frozen --package project-backend --extra dev`）。checkout、setup 和 SBOM 上传不是第二套测试。`scripts/quality/check_gate.py` 比较两边的集合，它自己也是 `verify` 的一项。`verify-release` 与 `verify` 是同一个目标。Trivy 只在 HIGH 或 CRITICAL 且已经有修复版本时让门禁失败。

本仓库使用根目录 `LICENSE` 的 MIT 许可证。

## 备选方案

- 在 workflow 里再写一遍 pnpm、Node 或 Flutter 版本：和权威文件可以不一致。否决。
- 保留一套只在 CI 里出现的测试命令：合并门禁和本机门禁不再是同一份。否决。

## 后果

- 升级工具链时改权威文件，并让 `make check-toolchain` 通过。
- 给 `verify` 增加或删除目标时，CI 的 `make` 参数必须一起改。
- Windows 上跑同一份 `make verify`。CI 不另设一套 Windows 命令。

## 关联

- 契约/错误码/权限/数据影响：无
- 相关 spec：—
- 取代 0007 中「CI 的每个 `node-version`」这一条接线
