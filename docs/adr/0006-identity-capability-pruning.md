# 0006 · 身份与能力的生成时裁剪

状态：已接受
日期：2026-10-03
决策人：Mengshi（用户确认）

## 背景

选型表收集 `identity` 与 `capabilities`。生成器按答案安装代码：没选中的 verifier 和能力不留在项目里。

## 决策

**生成时裁剪，不做运行时 flag。**

1. **Identity**。`platform/authn/protocol.py` 约定每个 adapter 的导出。`verifiers/local.py`、`verifiers/wechat.py`、`verifiers/keycloak.py` 各是一个实现。`active.py` 是唯一导入点。生成器把该导入改成选中的模块，并删除其余 verifier 文件。
   - `local`：HS256，服务签发也校验。
   - `wechat`：`wx.login` 的 code 调 `jscode2session`，openid 成为 subject，再签发应用自己的 HS256 会话。`session_key` 与 app secret 不离开服务端。
   - `keycloak`：用 realm 的 JWKS（`{issuer}/protocol/openid-connect/certs`）本地校验 RS256。`iss` 是 realm URL，payload `typ` 必须是 `Bearer`，`realm_access.roles` 进入 Principal。不签发 token，`mint-token` 拒绝。
   - 以后的 cloud verifier（aws、gcp、azure、alibaba 等）是 `verifiers/` 下的新模块，加上生成器允许的身份名。现在不实现，答案里写这些名字会失败。

2. **Capabilities**。勾选才保留代码和配置。
   - `worker` 依赖 `redis`，缺了就失败。
   - `storage`、`llm` 没有 canonical 实现，勾选就失败。
   - 未勾选 redis 时删除 readiness 的 redis 检查、compose/CI 的 redis、`REDIS_URL`，并从生成项目的 `pyproject.toml` 删除 `redis`。未勾选 worker 时删除 `entrypoints/worker.py`、compose worker 和 `arq` 依赖，因此没有定时任务调用 `purge_expired_idempotency`；过期记录仍会在下次使用同一键时被替换。生成器在项目根目录执行 `uv lock`，使锁文件与重命名后的包名和选中的依赖一致。母版仓库保留 `uv.lock`：`pyproject` 写版本范围，`uv sync --frozen`、镜像和 CI 使用锁文件里的精确解析。母版包含 redis 和 worker，所以母版锁文件保留这两项。

3. **约束**。选了 `wechat-native` 则 `identity` 必须是 `wechat`，否则生成失败。当前是单身份。

母版仓库本身保留 local、redis、worker 全套，这样 `make verify` 有可运行的 canonical 实现。裁剪只发生在 `scripts/scaffold/create_project.py` 复制并完成 Python 包重命名之后。

## 备选方案

- **运行时 settings 切换**：没选中的代码仍在仓库里。否决。
- **模板只留 local，各项目手写**：每个项目重复同一件事。否决。

## 后果

- 新身份的成本是一个 verifier 模块、测试，以及生成器的身份白名单。
- `project-answers.example.yaml` 的 `identity` 与 `capabilities` 注释指向本 ADR。

## 关联

- 契约/错误码/权限/数据影响：权限（verifier 是唯一 Principal 铸造点）。`wechat` 项目的契约多 `POST /api/v1/session/wechat`。错误码仍是 `AUTHN.REQUIRED` / `AUTHN.INVALID`。
- 相关 spec：—
