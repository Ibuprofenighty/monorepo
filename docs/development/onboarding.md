# Onboarding

## 1. 读什么（按顺序）

1. `README.md` — 项目选型表（本项目的答案）
2. `docs/architecture/project-profile.md` — 实例化后的架构选择
3. `docs/blueprint/00-PROJECT-PROFILE.md` — 母版规范总览（只读，不改）
4. `AGENTS.md` — Agent/协作者工作纪律
5. 相关模块的 `specs/` + ADR

## 2. 跑起来

前置工具：Python 3.12（由 uv 管理）、uv、Node 24.11.1（`.node-version`，其他版本 `make bootstrap` 失败）、pnpm ≥ 9、Docker（含 compose 插件）、
GNU make；有 `apps/mobile` 时还需 Flutter SDK（stable）。

```bash
pnpm install --frozen-lockfile   # JS 依赖（含 openapi-typescript）
make bootstrap                   # 检查工具链、锁文件与前置条件（不安装任何东西）
cp .env.example .env             # 填本地值（POSTGRES_PASSWORD、JWT_SECRET ≥ 32 字节），不提交
make dev                         # 启动开发拓扑
make verify                      # 全部门禁（第一次跑确认环境正常）
```

Python 依赖无需手动安装：所有 Python 命令经 `uv run --frozen` 执行，按 `uv.lock` 自动同步。

### Windows

- Makefile recipes 只用 POSIX sh 与 cmd 共有的语法，GNU make 在没有 `sh` 时用 cmd 执行，
  `make verify` 等门禁直接可用。
- 仓库脚本都是 Python / Node，可脱离 make 直接运行，例如
  `uv run --project apps/backend --frozen --extra dev python scripts/quality/check_docs.py`。
- `make test-e2e`（`tests/e2e/run.sh`）需要 bash 与 Docker，在 Git Bash 或 WSL 中运行。

### 配置

- `APP_ENV`：`dev` / `test` / `staging` / `production`。`staging`、`production` 下
  `JWT_SECRET` 必须显式提供且 ≥ 32 字节，否则应用拒绝启动；`dev` / `test` 可用内置开发密钥。
- `DATABASE_URL`、`REDIS_URL`：本地值见 `apps/backend/.env.example`。
- 小程序：`MP_API_BASE_URL`（构建时注入）；预览/上传另需 `MP_APPID`、`MP_PRIVATE_KEY`（见下）。

### 小程序（选了 wechat-native）

- `make mp-build`：TypeScript `src/` 编译到 `apps/miniprogram/dist/`，注入 `MP_API_BASE_URL`。
- 微信开发者工具导入 `apps/miniprogram` 目录：`project.config.json` 的 `miniprogramRoot` 指向
  `dist/`。个人本地设置写在 `project.private.config.json`（已 gitignore），不改共享配置。
- 预览/上传走 `miniprogram-ci`（`apps/miniprogram` 的锁定 devDependency）Node API：
  `make mp-preview`、`make mp-upload`。需要：
  - `MP_APPID`：小程序 AppID；
  - `MP_PRIVATE_KEY`：代码上传密钥文件路径（微信公众平台「开发管理 → 开发设置 → 小程序代码上传」
    生成并配置 IP 白名单）；密钥文件只放 CI secret 或本机，永不进 Git；
  - 可选 `MP_ROBOT`（1–30，默认 1）、`MP_VERSION_DESC`；上传另需 `MP_VERSION`（由 CI 提供）。

## 3. 改东西的流程（blueprint 11）

1. 先写/改 `specs/` 场景（ID 稳定）
2. 先写测试（Red），再实现（Green）
3. 改契约 → 改 `contracts/` → `make generate` → 提交生成物
4. 新增公开错误码 → 改 `contracts/errors/` → `make generate`
5. 跑 `make verify`，不跳过失败

## 4. 禁止事项

- 手改 `generated/` 目录
- 在前端做最终权限裁决
- 把 secret 写进 git、镜像、客户端包
- 用 `|| true` 让门禁静默通过
- 没有真实执行就写 PASS
