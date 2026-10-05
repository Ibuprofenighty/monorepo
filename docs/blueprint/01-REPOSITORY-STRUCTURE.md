# 01 · Monorepo 总目录与模块边界

版本：2.0｜日期：2026-10-02｜本文件是目录职责的权威说明。

[返回总入口](../../README.md) · [项目选型](00-PROJECT-PROFILE.md) · [后端](04-BACKEND-PYTHON.md)

## 1. 固定原则

按业务能力组织代码，再在模块内部按职责分层。`apps` 是部署应用，`packages` 是可复用包，`contracts` 是机器接口契约，`specs` 是可测试行为，`infra` 是构建部署，`scripts` 是薄自动化，`tooling` 是工程工具。

`[可选]`：出现需求才建；`[生成]`：机器拥有，不手改；`[忽略]`：不提交 Git。树中是目标文件位置，不表示本 Markdown 包附带这些程序。

示例 `catalog`、`resource`、`project_backend` 必须替换为项目领域词。不要把全部项目抽象成万能 CRUD、`common` 或 `utils`。

## 2. 根目录

```text
project/
├── README.md                          # 项目入口，链接规范与已验证命令
├── AGENTS.md                          # Agent 入口，操作纪律
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE                            # 由项目选择实际授权
├── Makefile                           # 全仓命令入口；不放到 infra
├── package.json                       # private + packageManager + 仓库工具
├── pnpm-workspace.yaml
├── pnpm-lock.yaml                      # [生成] TS workspace 唯一锁
├── pyproject.toml                      # uv workspace + 仓库工具配置
├── uv.lock                             # [生成] Python workspace 唯一锁
├── .node-version
├── .python-version
├── .env.example                        # 无秘密的本地样例
├── .gitignore
├── .dockerignore                       # 配合仓库根 build context
├── .editorconfig
├── .gitattributes
├── .pre-commit-config.yaml             # [可选] 本地快速检查
├── .github/
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   └── workflows/
│       ├── ci.yml
│       ├── security.yml
│       └── release.yml
├── apps/
│   ├── backend/                        # Python 模块化单体
│   ├── web/                            # [选用] Vite 或 Next.js，二选一
│   ├── miniprogram/                    # [选用] 原生微信小程序
│   └── authorization/                  # [可选] 本仓库维护的独立授权服务
├── packages/
│   ├── ts/
│   │   ├── api-client/                 # 契约类型、操作与 transport 抽象
│   │   └── ui/                         # [可选] 真正多 Web 应用复用
│   └── python/                         # [可选] 多 Python 应用复用的明确库
├── contracts/
│   ├── README.md
│   ├── errors/                         # 公开错误注册表
│   ├── http/                           # HTTP 源契约
│   └── events/                         # [可选] 异步协议源契约
├── specs/
│   ├── README.md
│   ├── schema/                         # [按需] 团队自定义 spec 的校验格式
│   ├── invariants.yaml                 # 真正跨模块的不变量
│   └── features/
│       └── catalog/delete-resource.yaml
├── docs/
│   ├── README.md
│   ├── blueprint/                      # 本包规范；每个主题一个权威分册
│   ├── architecture/
│   │   ├── project-profile.md           # 项目事实，不复制母版
│   │   ├── system-context.md
│   │   ├── module-boundaries.md
│   │   ├── data-model.md                # 解释模型；不是第二份 DDL
│   │   └── threat-model.md
│   ├── adr/                            # 已批准选择与变更理由
│   ├── development/
│   │   ├── setup.md
│   │   └── commands.md
│   ├── operations/
│   │   ├── deployment.md
│   │   ├── rollback.md
│   │   ├── backup-restore.md
│   │   └── incident-response.md
│   ├── plans/                          # [可选] 当前工作项
│   └── audits/                         # [可选] 日期与 commit 绑定的历史证据
├── infra/                              # 详见 09 分册
├── scripts/                            # 详见 09 分册
├── tooling/
│   ├── typescript/                     # 共用 TS/ESLint 配置
│   ├── architecture/                   # 边界检查工具真实配置
│   ├── codegen/                        # 生成器版本、参数、模板
│   └── templates/                      # [可选] 已实现的脚手架模板
├── tests/
│   ├── e2e/
│   │   ├── web/                        # [选用] Playwright 等 Web E2E
│   │   └── miniprogram/                # [选用] 小程序专用 E2E
│   ├── system/                         # [可选] 跨进程、消息、任务
│   ├── performance/                    # [按 SLO]
│   └── repository/                     # 整仓文档、生成物与工程约束
└── .artifacts/                         # [生成][忽略] 有保留策略的执行证据
```

根目录不再保留一组平行的 `frontend/`、`backend/`、`common/` 或旧 `src/` 作为另一套生产入口。历史迁移、受控归档不是平行生产实现。

## 3. 两个 workspace 的配置边界

pnpm 要有 `pnpm-workspace.yaml`，内部包使用 `workspace:` 声明本地依赖；uv 的成员各有 `pyproject.toml`，workspace 共享锁文件。[S01](SOURCES.md#s01) [S02](SOURCES.md#s02)

以下为**结构片段**，不是完整可构建项目：

```yaml
# pnpm-workspace.yaml；只保留实际启用应用
packages:
  - apps/web
  - apps/miniprogram
  - packages/ts/*
```

```toml
# 根 pyproject.toml
[tool.uv.workspace]
members = ["apps/backend"]
```

```json
{
  "dependencies": {
    "@project/api-client": "workspace:*"
  }
}
```

运行依赖归应用或包自身；仓库级检查工具归根或明确的工具 workspace。不得通过隐式提升使未声明依赖侥幸可用。Python 成员构建并安装实际包，不修改 `sys.path` 掩盖包结构问题。

同一生态只维护一个本方案所需锁文件；确需给外部平台导出 `requirements.txt`，从锁文件生成，不双手维护。锁文件不代替容器基础镜像、外部二进制和代码生成器的版本控制。

## 4. 依赖与所有权矩阵

| 所在位置 | 可以依赖 | 禁止 |
|---|---|---|
| `apps/<client>` | 已声明内部包、公开 HTTP 契约 | 导入另一个应用的私有源码 |
| `packages/ts/api-client` | 平台无关运行逻辑、生成契约 | DOM、微信 UI、Next 路由、应用业务规则 |
| Python `domain` | 纯语言能力、明确纯领域类型 | Web 框架、数据库、配置、网络 SDK |
| Python `application` | 本模块 domain、ports、kernel | 具体 ORM、Redis、FastAPI、platform 客户端 |
| Python `infrastructure` | 内层类型和端口、技术客户端 | 第二套业务政策 |
| Python `presentation` | application、公开 DTO | 直接写业务表 |
| `platform` | kernel、技术库 | 导入业务模块形成环 |
| `bootstrap` | wiring、platform、模块组装 | 成为业务决策实现 |
| `scripts` | 工具与公开管理入口 | 抄写业务规则 |
| `infra` | 构建部署描述 | 被 runtime 导入作为业务模块 |

Python 依赖倒置细节见 [后端分册](04-BACKEND-PYTHON.md)；Web FSD 规则见所选客户端分册。不要把 HTTP 运行调用链误画成源码依赖链。

## 5. 共享与复用规则

两个真正消费者需要稳定能力时才抽包。前端 UI 可以在多个 Web 应用共享，但小程序 WXML 组件不能靠路径复用变成 React 组件。共享格式化等纯函数时须确认运行时兼容，而不是只确认 TypeScript 类型正确。

共享代码源只有一份，客户端构建产物可以包含相同编译代码。这是制品复制，不是手写业务双轨。生成 DTO、迁移历史、快照也不能仅因“有相似文字”而删除。

后台 worker 默认是 `apps/backend` 的另一个 entrypoint，复用相同用例和镜像。独立进程不自动意味着独立代码项目；只有明确的发布、依赖或所有权需求才拆服务。

## 6. 模块增删的完整边界

增加模块：定义职责与数据归属 → 确定公开 API → 注册 wiring/路由 → 迁移 → 契约与客户端 → 权限 → 测试 → 文档。

删除模块：确认消费者和存量数据 → 迁移数据/停用入口 → 清理应用注册、任务、契约、生成物、导航和依赖 → 验证不可达与不再被调用。已部署迁移不得随意删改；应添加前向迁移完成清理。

对已发布小程序或外部消费者，不能假设所有客户端和服务端能原子更新。优先在一套实现内保持仍受支持契约；若必须破坏兼容，先决定最低客户端版本、退役窗口和数据迁移。不得用“删旧建新”掩盖未经批准的线上中断，也不得悄悄建立长期兼容分叉。

## 7. 文档与代码冲突如何处理

没有“代码永远正确”或“旧文档永远正确”。确认业务事实、获批决策和实际行为，选定一个目标并同步变更。未消解冲突前不能把状态写成完成。

历史计划退出当前导航；审计保留日期、commit 与范围，不作为另一份新架构。不要建立 `FINAL-2`、`new-final`、`legacy-compatible` 等有效平行真源。

## 8. 验收

全仓扫描必须能发现：应用间私有导入、Python 越层、Web 越层、未声明依赖、生成物漂移和无效文档链接。检查工具应有“故意违规会失败”的测试；仅存在 `public.py`、`index.ts`、目录树并不能证明边界被执行。
