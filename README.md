# Monorepo Template

<p align="center">
  <a href="https://github.com/Ibuprofenighty/monorepo/blob/main/.node-version"><img src="https://img.shields.io/badge/Node-24.11.1-339933?logo=nodedotjs&logoColor=white" alt="Node 24.11.1"></a>
  <a href="https://github.com/Ibuprofenighty/monorepo/blob/main/.python-version"><img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12"></a>
  <a href="https://github.com/Ibuprofenighty/monorepo/blob/main/package.json"><img src="https://img.shields.io/badge/pnpm-9.7.0-F69220?logo=pnpm&logoColor=white" alt="pnpm 9.7.0"></a>
  <a href="https://github.com/Ibuprofenighty/monorepo/blob/main/contracts/http/openapi.yaml"><img src="https://img.shields.io/badge/OpenAPI-3.1-6BA539?logo=openapiinitiative&logoColor=white" alt="OpenAPI 3.1"></a>
</p>

<p align="center">
  A contract-first monorepo <b>template</b>. Fill in the answers, generate a project, then build the product there.<br>
  这是工程<b>母版</b>，不是业务项目。填选型表，生成新仓库，再在新仓库里写产品。
</p>

<p align="center">
  <a href="#english">English</a> |
  <a href="#zh-cn">简体中文</a>
</p>

<a id="english"></a>

## 📖 Introduction

This repository holds the canonical source and the generator. It is not the place to add product features. A generated project is a separate directory, next to this template, containing only the clients and capabilities that were selected.

Installed trees such as `node_modules/`, `.venv/` and `.dart_tool/` are local tools. They are gitignored and are not copied into a new project. The template does commit lockfiles (`uv.lock`, `pnpm-lock.yaml`) so a frozen install resolves the same versions everywhere.

## ✨ What you get

- 📜 **One handwritten contract.** `contracts/http/openapi.yaml` is the only HTTP source. TypeScript, Python and Dart clients are generated from it. Do not edit `generated/`.
- 🧱 **A modular FastAPI monolith.** Business logic stays in `apps/backend`. Clients stay thin.
- 🎛️ **Generate-time selection.** Identity (`local`, `wechat`, `keycloak`) and capabilities (`redis`, `worker`) are copied in only when chosen. Unselected verifier files are deleted. There is no runtime feature flag for them.
- 📌 **Pinned Node.** `.node-version`, CI, `package.json` `engines` and the web image all say `24.11.1`. `make check-toolchain` checks that pin. It does not query a registry.
- 🧪 **A merge gate.** `make verify` lints the contract, regenerates clients into a temp tree and diffs them, runs unit and security tests, and (when `TEST_DATABASE_URL` is set) runs the PostgreSQL integration and migration suites.

## 🗺️ Layout

| Path | What it is | Copied into a new project |
| :--- | :--- | :--- |
| `apps/backend` | FastAPI modular monolith and the `catalog` example | Always |
| `apps/web` | Vite + React + TypeScript | When `web-vite` is selected |
| `apps/web-next` | Next.js | When `web-next` is selected |
| `apps/miniprogram` | WeChat native TypeScript | When `wechat-native` is selected |
| `apps/mobile` | Flutter app | When `mobile-flutter` is selected |
| `packages/ts/api-client` | TypeScript SDK | When any TypeScript client is selected |
| `packages/dart/api_client` | Dart SDK | When `mobile-flutter` is selected |
| `contracts/` | Handwritten OpenAPI and the error registry (RFC 9457) | Always |
| `docs/blueprint/` | The specification set. Authority stays here | Never |
| `docs/architecture/` | Profile template | Filled in from the answers |

Generator details: [scripts/scaffold/README.md](scripts/scaffold/README.md).

## ⚖️ Decisions

Read these before changing the contract or the generator. Full list: [docs/adr/README.md](docs/adr/README.md).

| ADR | Decision |
| :--- | :--- |
| [0001](docs/adr/0001-handwritten-openapi.md) | The OpenAPI file is handwritten. Generated clients are not a second source. |
| [0004](docs/adr/0004-template-upgrade-path.md) | No one-click upgrade. Generated projects follow [docs/changelog/](docs/changelog/README.md) by hand. |
| [0005](docs/adr/0005-dart-codegen-subset.md) | The Dart generator accepts a subset only. `oneOf` / `anyOf` / `allOf` and other shapes outside that subset fail the build. |
| [0006](docs/adr/0006-identity-capability-pruning.md) | Identity and capabilities are pruned at generate time. `wechat-native` requires `identity: wechat`. `worker` requires `redis`. `storage` and `llm` have no implementation yet and fail if selected. |
| [0007](docs/adr/0007-node-pinned.md) | Node is pinned to `24.11.1`. |

## 🚀 Quick start

Tools: `uv`, `pnpm` 9.7.0, Docker, and GNU make. Flutter stable is required only when the answers include `mobile-flutter`. Node must be exactly the version in [`.node-version`](.node-version).

```bash
cp project-answers.example.yaml my-answers.yaml
# edit my-answers.yaml — two filled examples live in examples/

./create-project.sh --answers my-answers.yaml
cd ../<project_name>
make bootstrap && make dev
```

On Windows, without a POSIX shell:

```powershell
uv run --project apps/backend --frozen --extra dev python scripts/scaffold/create_project.py --answers my-answers.yaml
```

The generator refuses to write inside this repository. The default destination is a sibling directory named after `project_name`.

Filled examples:

- [examples/answers-miniprogram.yaml](examples/answers-miniprogram.yaml) — WeChat mini program, `wechat` identity, redis and worker
- [examples/answers-web-mobile.yaml](examples/answers-web-mobile.yaml) — Vite admin plus Flutter, `keycloak` identity, redis and worker

## 📋 Answers

Copy the field names from [project-answers.example.yaml](project-answers.example.yaml). Rows marked 🔴 block generation when empty.

| # | Decision | Notes |
| :--- | :--- | :--- |
| 1 | Project name 🔴 | Lowercase, hyphens, starts with a letter. Becomes the directory name. |
| 2 | Python package 🔴 | Lowercase identifier, for example `sheetshow_backend`. |
| 3 | TypeScript scope 🔴 | For example `sheetshow` produces `@sheetshow/api-client`. |
| 4 | Dart package 🔴 | Required with `mobile-flutter`, for example `sheetshow_api_client`. |
| 5 | Mobile org 🔴 | Required with `mobile-flutter`. Reverse domain, for example `com.sheetshow`. |
| 6 | Product goal | One sentence. |
| 7 | Clients 🔴 | One or more of `web-vite`, `web-next`, `wechat-native`, `mobile-flutter`. |
| 8 | Web rendering | Only for `web-next`: `ssr` or `static-export`. |
| 9 | First modules | For example `catalog`. |
| 10 | Identity 🔴 | `local` (default), `wechat`, or `keycloak`. |
| 11 | Authorization 🔴 | `local` (default). |
| 12 | Database | PostgreSQL only. |
| 13 | OpenAPI version | `3.1.0`. |
| 14 | Problem namespace | HTTPS URL, replaced before production. |
| 15 | Dependency versions | Node, Python, pnpm and uv. Defaults come from this template. |
| 16 | Deploy target | `compose` (default). Kubernetes manifests are not in the template. |
| 17 | Capabilities | `redis` and `worker` are optional. `worker` needs `redis`. `storage` and `llm` fail generation. |
| 18 | git init | `true` or `false`. |
| 19 | Owner | Who is responsible for this generation. |

## 🧪 Verify the template

`make verify` is the merge gate. It does not modify source. Integration and migration tests talk to a real PostgreSQL and are skipped when `TEST_DATABASE_URL` is unset, so a green run without that variable is not a database proof.

```bash
docker run -d --name project-pg \
  -e POSTGRES_USER=project -e POSTGRES_PASSWORD=ci-pw -e POSTGRES_DB=project_test \
  -p 5432:5432 postgres:16-bookworm

export TEST_DATABASE_URL=postgresql+asyncpg://project:ci-pw@localhost:5432/project_test
export DATABASE_URL="$TEST_DATABASE_URL"
make verify
```

The breaking-change check compares `contracts/http/openapi.yaml` with `git HEAD`. On a tree that is not a git repository it skips. End-to-end HTTP checks are separate: `bash tests/e2e/run.sh` (Git Bash on Windows).

Records of what actually ran live in [docs/audits/validation-evidence.md](docs/audits/validation-evidence.md).

## 🛠️ Work on the template itself

```bash
git clone https://github.com/Ibuprofenighty/monorepo.git
cd monorepo
pnpm install --frozen-lockfile
uv sync --frozen --package project-backend --extra dev
make bootstrap
```

Day-to-day commands are in [docs/development/onboarding.md](docs/development/onboarding.md).

## ⚠️ Notes

- Do not promise that a template update rewrites existing projects. Sync from the changelog.
- Redis here is the readiness dependency and the broker for the arq worker (hourly idempotency purge). It is not a general message bus. Kafka is not a selectable capability.
- This repository does not ship a `LICENSE` file. Do not assume the license of any other project applies here.

<a id="zh-cn"></a>

## 📖 简介

这个仓库是母版：规范、canonical 实现和生成器。产品功能写在生成出来的项目里，不写在这里。生成目录默认与母版同级，只包含选型表里勾选的客户端和能力。

`node_modules/`、`.venv/`、`.dart_tool/` 是本机安装结果。它们在 `.gitignore` 里，生成器也不会把它们复制走。母版提交的是锁文件（`uv.lock`、`pnpm-lock.yaml`），用来让 `--frozen` 安装得到同一套版本。

## ✨ 母版提供什么

- 📜 **一份手写契约。** `contracts/http/openapi.yaml` 是唯一的 HTTP 来源。TypeScript、Python、Dart 客户端都从它生成。不要手改 `generated/`。
- 🧱 **一个 FastAPI 模块化单体。** 业务在 `apps/backend`。客户端保持薄。
- 🎛️ **生成时选型。** 身份（`local`、`wechat`、`keycloak`）和能力（`redis`、`worker`）只在勾选时进入新项目。没选中的 verifier 文件会被删除。没有运行时开关。
- 📌 **Node 钉死。** `.node-version`、CI、`package.json` 的 `engines` 和 web 镜像都是 `24.11.1`。`make check-toolchain` 核对这几处，不访问镜像仓库。
- 🧪 **合并门禁。** `make verify` 检查契约、在临时目录重新生成客户端并做 diff、跑单元测试和安全测试。设置了 `TEST_DATABASE_URL` 时，还会跑真实 PostgreSQL 的集成测试和迁移测试。

## 🗺️ 目录

| 路径 | 内容 | 新项目 |
| :--- | :--- | :--- |
| `apps/backend` | FastAPI 模块化单体，含 `catalog` 示例 | 总是复制 |
| `apps/web` | Vite + React + TypeScript | 勾选 `web-vite` |
| `apps/web-next` | Next.js | 勾选 `web-next` |
| `apps/miniprogram` | 微信原生 TypeScript | 勾选 `wechat-native` |
| `apps/mobile` | Flutter 应用 | 勾选 `mobile-flutter` |
| `packages/ts/api-client` | TypeScript SDK | 勾选了任一 TypeScript 客户端 |
| `packages/dart/api_client` | Dart SDK | 勾选 `mobile-flutter` |
| `contracts/` | 手写 OpenAPI 和错误码注册表（RFC 9457） | 总是复制 |
| `docs/blueprint/` | 规范全文，权威留在母版 | 不复制 |
| `docs/architecture/` | 项目画像模板 | 按答案填好 |

生成器说明见 [scripts/scaffold/README.md](scripts/scaffold/README.md)。

## ⚖️ 先读的决策

改契约或生成器之前先读这些。完整列表：[docs/adr/README.md](docs/adr/README.md)。

| ADR | 决策 |
| :--- | :--- |
| [0001](docs/adr/0001-handwritten-openapi.md) | OpenAPI 手写。生成的客户端不是第二份契约源。 |
| [0004](docs/adr/0004-template-upgrade-path.md) | 没有一键升级。已生成项目按 [docs/changelog/](docs/changelog/README.md) 手工同步。 |
| [0005](docs/adr/0005-dart-codegen-subset.md) | Dart 生成器只接受子集。`oneOf` / `anyOf` / `allOf` 以及子集外的形态会让生成失败。 |
| [0006](docs/adr/0006-identity-capability-pruning.md) | 身份和能力在生成时裁剪。`wechat-native` 必须配 `identity: wechat`。`worker` 必须配 `redis`。`storage` 和 `llm` 还没有实现，勾选则生成失败。 |
| [0007](docs/adr/0007-node-pinned.md) | Node 固定为 `24.11.1`。 |

## 🚀 生成一个项目

需要 `uv`、`pnpm` 9.7.0、Docker 和 GNU make。只有答案里选了 `mobile-flutter` 才需要 Flutter stable。Node 必须等于 [`.node-version`](.node-version) 里的版本。

```bash
cp project-answers.example.yaml my-answers.yaml
# 编辑 my-answers.yaml。examples/ 里有两份填好的例子。

./create-project.sh --answers my-answers.yaml
cd ../<project_name>
make bootstrap && make dev
```

Windows 上没有 POSIX shell 时：

```powershell
uv run --project apps/backend --frozen --extra dev python scripts/scaffold/create_project.py --answers my-answers.yaml
```

生成器拒绝把项目写进母版目录。默认目标是与母版同级、以 `project_name` 命名的目录。

填好的例子：

- [examples/answers-miniprogram.yaml](examples/answers-miniprogram.yaml) — 微信小程序，`wechat` 身份，redis 和 worker
- [examples/answers-web-mobile.yaml](examples/answers-web-mobile.yaml) — Vite 后台加 Flutter，`keycloak` 身份，redis 和 worker

## 📋 选型表

字段名以 [project-answers.example.yaml](project-answers.example.yaml) 为准。标 🔴 的空着就不能生成。

| # | 决策项 | 说明 |
| :--- | :--- | :--- |
| 1 | 项目名称 🔴 | 小写、短横线、以字母开头。用作目录名。 |
| 2 | Python 包名 🔴 | 小写标识符，例如 `sheetshow_backend`。 |
| 3 | TypeScript scope 🔴 | 例如 `sheetshow`，得到 `@sheetshow/api-client`。 |
| 4 | Dart 包名 🔴 | 选了 `mobile-flutter` 才必填，例如 `sheetshow_api_client`。 |
| 5 | Mobile 组织标识 🔴 | 选了 `mobile-flutter` 才必填。反向域名，例如 `com.sheetshow`。 |
| 6 | 产品目标 | 一句话。 |
| 7 | 客户端 🔴 | `web-vite`、`web-next`、`wechat-native`、`mobile-flutter`，至少一个。 |
| 8 | Web 渲染 | 仅 `web-next`：`ssr` 或 `static-export`。 |
| 9 | 首批业务模块 | 例如 `catalog`。 |
| 10 | 身份权威 🔴 | `local`（默认）、`wechat` 或 `keycloak`。 |
| 11 | 授权权威 🔴 | `local`（默认）。 |
| 12 | 数据库 | 只有 PostgreSQL。 |
| 13 | OpenAPI 版本 | `3.1.0`。 |
| 14 | 错误 type 命名空间 | HTTPS URL，上线前替换。 |
| 15 | 依赖版本 | Node、Python、pnpm、uv。默认取母版。 |
| 16 | 部署目标 | `compose`（默认）。母版不含 Kubernetes 清单。 |
| 17 | 可选能力 | `redis` 和 `worker` 可选。`worker` 依赖 `redis`。`storage` 和 `llm` 会让生成失败。 |
| 18 | git 初始化 | `true` 或 `false`。 |
| 19 | 负责人 | 谁对这次生成负责。 |

## 🧪 验收母版

`make verify` 是合并门禁，不改源码。集成测试和迁移测试需要真实 PostgreSQL。没设 `TEST_DATABASE_URL` 时它们会跳过，那种通过不能当作数据库证明。

```bash
docker run -d --name project-pg \
  -e POSTGRES_USER=project -e POSTGRES_PASSWORD=ci-pw -e POSTGRES_DB=project_test \
  -p 5432:5432 postgres:16-bookworm

export TEST_DATABASE_URL=postgresql+asyncpg://project:ci-pw@localhost:5432/project_test
export DATABASE_URL="$TEST_DATABASE_URL"
make verify
```

破坏性变更检查拿 `contracts/http/openapi.yaml` 和 `git HEAD` 比较。当前目录不是 git 仓库时，这一项会跳过。端到端 HTTP 检查是另一条命令：`bash tests/e2e/run.sh`（Windows 用 Git Bash）。

实际跑过的命令记在 [docs/audits/validation-evidence.md](docs/audits/validation-evidence.md)。

## 🛠️ 在母版上开发

```bash
git clone https://github.com/Ibuprofenighty/monorepo.git
cd monorepo
pnpm install --frozen-lockfile
uv sync --frozen --package project-backend --extra dev
make bootstrap
```

日常命令见 [docs/development/onboarding.md](docs/development/onboarding.md)。

## ⚠️ 注意

- 不要承诺母版更新会自动改写已生成项目。对齐方式是 changelog。
- 这里的 Redis 是 readiness 依赖，也是 arq worker 的队列（每小时清理过期幂等记录）。它不是通用消息总线。Kafka 不是可选项。
- 本仓库没有 `LICENSE` 文件。不要把其他项目的许可证套到这里。
