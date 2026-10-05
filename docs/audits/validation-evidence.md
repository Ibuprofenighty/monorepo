# Validation Evidence

每次 `make verify` / `make verify-release` / 发布后，在此留一条记录。
"测试执行成功"不是证明；要写清楚：在什么环境、跑了什么、结果、未验证项。

## 模板

```markdown
## YYYY-MM-DD · <范围：verify / verify-release / 发布>

- 环境：<OS / docker / 真机 / 开发者工具，版本号>
- 命令：<实际执行的命令>
- 结果：
  - <gate/套件>：PASS / FAIL / BLOCKED（原因）/ N/A（理由）
- 未验证项：<明确列出，不能省略>
- 残余风险：<一句话>
- 执行人：<who>
```

## 记录

（按时间倒序追加）

## 2026-10-05 · make verify（合并门禁）

- 环境：Windows 11（10.0.26200）；Python 3.12.12（uv 0.9.21）；Node v24.11.1；pnpm 9.7.0；
  Flutter 3.47.3（Dart 3.13.3）；Docker 29.2.1；Compose v5.1.0。PostgreSQL 16 容器提供
  `TEST_DATABASE_URL`，测完删除。
- 命令：`make verify`（已设置 `TEST_DATABASE_URL` 与 `DATABASE_URL`）
- 结果：exit 0
  - check-toolchain：ok（node 24.11.1，python 3.12，flutter 3.47.3，pnpm@9.7.0）
  - check-gate：ok（26 个目标）
  - check-contract：母版 Spectral 无 error；微信拼接后的 OpenAPI PASS
  - check-breaking：对照 HEAD 无破坏性变更
  - check-generated：clean
  - lint / typecheck / check-architecture / check-specs / check-counterexamples / check-docs：通过
    （check-traceability 10 spec ids；check-docs 37 files；反例 4/4 CAUGHT；mypy 63 files）
  - test-unit：pytest 17 passed；vitest api-client 10、web 1、miniprogram 2
  - test-integration：24 passed，0 skipped
  - test-contract：19 passed
  - test-migrations：3 passed，0 skipped
  - test-security：29 passed
  - build-clients：Vite、Next static export、小程序 dist
  - check-dart：api_client 6 passed；mobile analyze 无问题、2 passed
  - test-e2e：ALL E2E CHECKS PASSED
  - images / scan-images：backend 与 web `runtime-static` 构建完成；已有修复版本的 HIGH/CRITICAL 为 0
  - sbom：写出 backend 镜像的 SPDX 文件，不入库
  - check-generator：answers-miniprogram、answers-web-mobile、empty-capabilities 均 PASS
- 未验证项：该提交在 GitHub Actions 上的运行；`main` 分支保护
- 残余风险：基础镜像里尚无修复版本的系统包不会让扫描失败
- 执行人：agent

## 2026-10-05 · make verify

- 环境：Windows 11（10.0.26200，GBK 控制台）；Python 3.12.12（uv 0.9.21）；Node v24.11.1；pnpm 9.7.0；
  Docker 29.2.1；Compose v5.1.0。PostgreSQL 16 容器提供 `TEST_DATABASE_URL`，测完删除。
  仓库已有 `main` 提交，破坏性变更检查对照该 HEAD。
- 命令：`make verify`（已设置 `TEST_DATABASE_URL` 与 `DATABASE_URL`）
- 结果：exit 0
  - check-toolchain：ok（node 24.11.1）
  - check-contract：母版 Spectral 无 error；微信拼接后的 OpenAPI PASS
  - check-breaking：下载 oasdiff v1.33.0，校验记录的 sha256，对照 HEAD 无破坏性变更
  - check-generated：clean
  - lint / typecheck / check-architecture / check-specs / check-counterexamples / check-docs：通过
    （check-traceability 10 spec ids；check-docs 35 files；反例 CAUGHT）
  - test-unit：pytest 17 passed；vitest api-client 10、web 1、miniprogram 2
  - test-integration（`integration or api`）：24 passed，0 skipped
  - test-contract：19 passed
  - test-migrations：3 passed，0 skipped
  - test-security：29 passed
  - check-generator：answers-miniprogram、answers-web-mobile、empty-capabilities 均 PASS
- 未验证项：本条命令不含 `tests/e2e/run.sh`、不含 `runtime-server` 镜像、不含 Dart / Flutter 测试
- 残余风险：oasdiff 二进制缓存在本机 `.tools/`，不进入 git。
- 执行人：本会话

## 2026-10-05 · 生成器锁、契约、镜像、PostgreSQL、E2E

- 环境：Windows 11（10.0.26200，GBK 控制台）；Python 3.12.12（uv 0.9.21）；Node v24.11.1；pnpm 9.7.0；
  Docker 29.2.1；Compose v5.1.0；Git Bash 5.2.15；Flutter 3.47.3 / Dart 3.13.3（stable）。
  PostgreSQL 16 使用一次性 `postgres:16-bookworm` 容器，测完删除。Web 镜像测完删除。
- 命令与结果：
  - `pytest tests/scaffold/test_selection.py` → 5 passed
  - `pnpm exec spectral lint contracts/http/openapi.yaml` → 无 error
  - `scripts/quality/check_wechat_contract.py` → wechat 拼接后的 OpenAPI，PASS
  - `pnpm exec eslint .` → PASS
  - `pnpm -r exec tsc --noEmit` → PASS
  - `check_docs.py` → ok（35 files）；`check_toolchain.py` → ok（node 24.11.1）
  - `pytest -m "integration or migration"`，`TEST_DATABASE_URL=postgresql+asyncpg://...` → 11 passed，85 deselected
  - `scripts/quality/check_generator.py` → answers-miniprogram、answers-web-mobile、empty-capabilities 均 PASS
    （空能力画像的 pyproject 与 uv.lock 不含 redis / arq；两个 few-shot 保留这两项）
  - `docker build -f infra/docker/web.Dockerfile --target runtime-static` → PASS，随后删除该镜像
  - Git Bash 执行 `tests/e2e/run.sh` → `ALL E2E CHECKS PASSED`，exit 0
  - 两个 few-shot 在仓库外完整 `create_project`（含 pnpm install；web-mobile 含 `flutter create` 与 `flutter pub get`）→ 均完成。
    生成物的 OpenAPI 再跑 Spectral，无 error。微信项目含 session 路径；运营项目含 keycloak 设置与 android/ios。
    生成物的 Makefile 与 CI 不含母版专用的 `check-generator`。验证后删除这两个目录。
  - 母版 `uv.lock` 仍包含 `redis` 与 `arq`
- 未验证项：没有把 `make verify` 作为一条命令整段执行；没有构建 `runtime-server`；
  没有在已生成项目里再跑它们自己的 `make verify`、`flutter analyze` 或 `flutter test`；
  没有微信开发者工具、真机或真实 AppID
- 残余风险：空能力画像只由快速门禁覆盖，没有另存一份生成目录。
- 执行人：本会话

## 2026-10-04 · 工具链钉死、身份裁剪、Dart 子集、changelog 门禁

- 环境：Windows 11（10.0.26200，GBK 控制台）；Python 3.12.12（uv 0.9.21）；Node v24.11.1；pnpm 9.7.0；
  Docker 29.2.1；Flutter 3.47.3 / Dart 3.13.3（stable）。未启动 PostgreSQL，未构建 web 镜像。
- 命令与结果：
  - `docker buildx imagetools inspect node:24.11.1-bookworm-slim` → 索引摘要
    `sha256:48abc13a19400ca3985071e287bd405a1d99306770eb81d61202fb6b65cf0b57`
    （与浮动标签 `node:24-bookworm-slim` 的索引不同）
  - `uv lock` → 增加 `pyjwt[crypto]` 的 cryptography
  - ruff check + ruff format --check（`src`、`tests`、`scripts`）→ PASS
  - mypy `src` → 63 files，PASS
  - pytest `-m "unit or security or contract or architecture"` → 68 passed，27 deselected
  - `scripts/contracts/generate.py` 与 `--check --quiet` → PASS
  - `dart test`（`packages/dart/api_client`）→ 6 passed
  - `check_toolchain.py` → ok（node 24.11.1）
  - `check_docs.py` → ok（35 files）
  - `check_traceability.py` → ok（10 spec ids）
  - `check_counterexamples.py` → 4/4 CAUGHT，源文件已还原
  - `bootstrap.py` → node v24.11.1 与 `.node-version` 一致，PASS
  - 三个 answers 示例通过 `check_selection`
- 未验证项：完整 `make verify`（含 Spectral、eslint、tsc、真实 PostgreSQL 的 integration/migrations）；
  E2E；用新索引摘要实际 `docker build` web 镜像；对两个 few-shot 跑完整 `create-project`（含 pnpm install / flutter create）
- 残余风险：生成器裁剪有单元测试覆盖标记删除与 wechat 拼接；完整生成目录尚未在本轮落盘。未选 redis/worker 时锁文件仍保留 `redis` 与 `arq`。
- 执行人：本会话

## 2026-10-03 · verify-release + 生成器 few-shot + E2E（母版）

- 环境：Windows 11（10.0.26200，GBK 控制台，无 POSIX `sh`；GNU make 4.4.1 以 cmd 执行 recipes）；
  Python 3.12.12（uv 0.9.21 管理）、Node 24.11.1、pnpm 9.7.0、Docker 29.2.1 + Compose v5.1.0（Docker Desktop）、
  Flutter 3.47.3 / Dart 3.13.3（stable）、Git Bash 5.2.15。PostgreSQL 16 容器作为 `TEST_DATABASE_URL`。
  无 Android/iOS 真机或模拟器、无微信开发者工具、无真实小程序 AppID 与上传密钥。
- 命令与结果（均为真实执行）：
  - `make verify-release`（设置 `TEST_DATABASE_URL`；`POSTGRES_PASSWORD` / `JWT_SECRET` 与 CI 一样以非部署占位值注入，
    仅供 compose 配置渲染）→ PASS：
    check-generated clean；ruff check/format、eslint、`pnpm -r exec tsc --noEmit`、mypy（56 files）通过；
    architecture 4 passed；check-traceability ok（10 spec ids）；check-counterexamples 4/4 CAUGHT
    （remove-locked-invariant、verifier-accepts-everything、write-before-authorize、drop-idempotency-subject-scope），
    源文件按字节还原；check-docs ok；test-unit（pytest + vitest 10）、test-integration（真实 PG）、
    test-contract、test-migrations（真实 PG，含 `(subject, key)` 主键断言）、test-security 全部通过；
    `docker build -f infra/docker/backend.Dockerfile .` 与 `docker compose -f infra/compose/compose.yaml config -q` 通过。
  - `bash tests/e2e/run.sh`（Git Bash + Docker Desktop）→ ALL E2E CHECKS PASSED：随机生成 POSTGRES_PASSWORD /
    JWT_SECRET；单执行者 `alembic upgrade head` 后启动 api；401 AUTHN.REQUIRED / AUTHN.INVALID、
    403 AUTHZ.DENIED、422 VALIDATION.FAILED（problem+json）、404 NOT.FOUND；幂等创建 201、重放 201 同 id、
    同 key 异 body 422、他人重放同 key 403、列表恰好一条；删除 204 后 404；结束时 `down -v` 清理。
  - `make dev`（仓库根临时 `.env`，验证后删除）→ postgres、redis、api、worker、web 五个服务均 healthy；
    `:8080/` 200（nginx 静态 SPA）；`:8080/api/v1/health` 经 nginx 代理 200；`:8080/api/v1/resources`
    未认证 401 且保持 `application/problem+json`；worker 健康由 `arq --check` 判定；`make dev-down` 收尾。
  - Next.js SSR 镜像：以 `web_rendering: ssr` 临时答案生成项目，compose 渲染为 `target: runtime-server`、
    `INTERNAL_API_URL: http://api:8000`、端口 3000；`docker build --target runtime-server` 成功，容器启动后 `/` 200。
  - 客户端：`pnpm install --frozen-lockfile`；`pnpm --filter @project/web build`；
    `pnpm --filter @project/web-next build`（static export）；`node scripts/miniprogram/build.mjs` + 小程序 vitest 2 passed；
    `packages/dart/api_client`：`dart analyze` No issues、`dart test` 6 passed；
    `apps/mobile`：`flutter analyze` No issues、`flutter test` 2 passed → PASS。
  - `node scripts/miniprogram/preview.mjs`（伪造 AppID + 伪造密钥文件）→ 经 miniprogram-ci 2.1.31 Node API
    到达微信签名接口并被拒（`get project attr fail`），证明项目装配与环境校验路径；真实预览见未验证项。
  - `make bootstrap`、`make doctor` → 全部前置条件满足；doctor 的生成物漂移检查 clean。
  - 生成器（`uv run --project apps/backend --frozen --extra dev python scripts/scaffold/create_project.py`）
    把两个 few-shot 生成到母版之外的临时目录：
    - `examples/answers-miniprogram.yaml` → sheetshow-mp：生成成功；无母版名残留；git 首个 commit 后工作区干净；
      `pnpm install --frozen-lockfile` 通过；      新项目内 `make verify`（真实 PG）→ PASS；`docker compose -f infra/compose/compose.yaml config -q` 通过；
      小程序 dist 构建 + vitest 2 passed；CI 无 dart job。
    - `examples/answers-web-mobile.yaml` → sheetshow-ops：`flutter create --org com.sheetshow.ops` 生成
      android/（applicationId `com.sheetshow.ops.sheetshow_ops_mobile`）与 ios/
      （bundle id `com.sheetshow.ops.sheetshowOpsMobile`）；`pubspec.lock` 由 `flutter pub get` 解析；
      新项目内 `make verify`（真实 PG）→ PASS；compose 配置检查通过；web build、`dart analyze`/`dart test` 6 passed、
      `flutter analyze` No issues、`flutter test` 2 passed；构建与测试后 git 工作区仍干净。
- 结果：
  - 合并门禁、发布门禁（镜像构建 + compose 配置）、E2E、开发拓扑、Web / Next（static + SSR 镜像）/ 小程序构建、
    Dart / Flutter 静态检查与测试、生成器两个 few-shot：PASS
  - Android/iOS 原生构建（`flutter build apk` / `flutter build ipa`）与真机运行：BLOCKED（本机无 Android SDK
    构建链验证、无 macOS/Xcode、无设备）
  - 微信开发者工具导入、真实 `mp-preview` / `mp-upload`：BLOCKED（需真实 AppID、代码上传密钥与 IP 白名单）
  - GitHub Actions 工作流：未在 GitHub 上运行（本地仅校验 YAML 结构与其中命令的本机等价执行）
- 未验证项：Android/iOS 原生构建与真机；微信开发者工具与真实预览/上传；GitHub 托管 runner 上的 CI 实跑。
- 残余风险：CI 首次在托管 runner 上运行前，action 版本与 runner 镜像差异以实际运行结果为准；
  未匹配路由（404/405）仍返回框架默认 JSON 而非 Problem，需在契约中定义对应公开错误码后统一。
- 执行人：Agent（母版验收）
