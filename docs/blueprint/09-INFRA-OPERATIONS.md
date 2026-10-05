# 09 · Infra、Config、Docker、Nginx、Scripts 与交付

版本：2.0｜日期：2026-10-02｜本文件拥有工程命令与部署职责定义。

[返回总入口](../../README.md) · [配置安全](08-AUTH-SECURITY.md) · [测试门禁](10-TESTING-HARNESS.md)

## 1. 配置不全部进入 infra

| 文件内容 | 正确归属 |
|---|---|
| 应用参数类型、默认与校验 | 应用 `platform/config` / 客户端 `shared/config` |
| 依赖、语言、编译、lint/test 设置 | 根/应用原生文件，或 `tooling` 共用配置 |
| 部署拓扑、镜像、网络、TLS/代理 | `infra` |
| 命令统一入口 | 根 `Makefile` |
| 需要编程的构建/运维编排 | `scripts` |
| 业务数据库迁移 | 后端 `migrations` |
| 小程序工程入口 | `apps/miniprogram/project.config.json` |

`infra/` 描述程序如何运行；模块 `infrastructure/` 实现外部依赖适配。两者不是重复命名，也不是两套业务基础设施代码。

## 2. Infra 总目录

```text
infra/
├── README.md
├── docker/
│   ├── backend.Dockerfile
│   └── web.Dockerfile                 # [有 Web 才建] 内容匹配 Vite/Next 选项
├── compose/
│   ├── compose.yaml                   # 唯一基础拓扑
│   ├── compose.dev.yaml               # 开发差异
│   ├── compose.test.yaml              # 隔离测试差异
│   └── compose.prod.yaml              # [确实采用 Compose 生产部署才建]
├── nginx/                             # [使用 Nginx 才建]
│   ├── nginx.conf
│   ├── conf.d/app.conf
│   └── snippets/
│       ├── proxy.conf
│       └── security-headers.conf
├── config/
│   ├── staging.env.example
│   └── production.env.example
├── observability/                     # [按实际选型]
│   ├── otel-collector.yaml
│   ├── alerts/
│   └── dashboards/
├── terraform/                         # [按需] 不放 state/秘密
│   ├── modules/
│   └── environments/
└── kubernetes/                        # [按需]
    ├── base/
    └── overlays/
```

默认基础拓扑只包含当前需要的组件。Redis、Kafka、MinIO、worker、Kubernetes 不因“企业级”三个字自动加入。也不要在同项目维护两套等价且无人验证的生产部署方式。

## 3. Docker build context 与镜像

统一以仓库根为 build context，Dockerfile 放 infra。Docker `COPY` 能访问什么由 context 决定。[S24](SOURCES.md#s24)

```bash
# 从仓库根执行；这是命令约定，前提是 Dockerfile 已实现。
docker build -f infra/docker/backend.Dockerfile .
```

根 `.dockerignore` 排除 `.git`、本地依赖、真实 `.env`、密钥、缓存和执行报告；保留构建需要的 workspace 文件、锁、内部包和源契约。不要把 `*.env.example` 与真实 secret 混为一谈，也不要为减包体积误删必要源码。

多阶段镜像中构建依赖与运行依赖分开。实际使用的 lock、内部 workspace 包和生成步骤要进入受控构建链；uv Docker 集成文档提供 workspace 构建方面的注意事项。[S36](SOURCES.md#s36)

运行阶段最小权限、明确工作目录和进程启动；健康检查、信号处理与资源限制要测试。镜像标记关联 commit，基础镜像与工具有版本策略。不要将 host 的虚拟环境或 node_modules 直接搬进不同 OS/架构镜像。

构建秘密使用受支持的 secret 机制，不放在 Docker ARG/ENV 或 COPY 后再删除；Docker 官方明确区分这类构建秘密输入。[S27](SOURCES.md#s27)

## 4. Compose：一份基础拓扑，差异用 overlay

配置文件位置决定相对路径的解析基准；多文件合并不是简单文本覆盖，端口等列表字段也不能想当然。必须检查 `docker compose config` 的最终结果。[S26](SOURCES.md#s26)

例如基础文件在 `infra/compose/compose.yaml`，仓库根 context 对应 `../..`；Dockerfile 路径按 context 指向 `infra/docker/backend.Dockerfile`。实现时对照实际命令解析验证。

```bash
# 检查合成配置；避免向公开日志输出解析后的秘密。
docker compose \
  -f infra/compose/compose.yaml \
  -f infra/compose/compose.dev.yaml \
  config
```

测试拓扑使用独立项目名、数据库与 volume，不能默认连接开发或生产数据。基础 compose 中的测试可覆盖配置必须真实可覆盖，不保留两套同义 service 伪装 overlay。

容器启动不等于服务就绪。需要 healthcheck 和合适的依赖条件；应用仍应处理依赖启动后重启或临时不可用，不能认为一次 depends_on 解决所有故障。[S35](SOURCES.md#s35)

## 5. 三类客户端的生产形态

| 客户端选项 | 部署形态 | 不能做 |
|---|---|---|
| Vite SPA | 静态产物 + 已选静态服务/代理 | 用开发代理充当生产代理 |
| Next 服务端 | Next runtime + Python 服务 | 把 .next 任意目录当静态站点 |
| Next 静态导出 | 静态产物，限定支持能力 | 同时要求请求时服务端功能 |
| 原生小程序 | 平台构建/预览/发布 + Python 服务 | 用 Nginx 发布 HTML 替代小程序 |

Vite 的默认 Nginx 可同时提供静态资源并代理 `/api`；Next 部署按选定网关与应用职责安排；只有小程序时不创建假的 Web 静态容器。TLS、请求限制、路由和真实 IP 信任只由明确的组件拥有。

## 6. Nginx 的具体责任

静态资源、API 代理、请求体限制、超时、受信代理头和必要安全头要明确；身份和业务授权仍在服务端用例。

`proxy_pass` 是否带 URI 会影响路径转发；buffering 会影响流式响应。采用 SSE、流式页面或大文件时单独测试相关路径，不对所有服务机械复制一份参数。官方指令说明见 [S34](SOURCES.md#s34)。

API 路径不得被 SPA fallback 改写成 index.html；上游 Problem 的状态码和 Content-Type 不应被统一错误页吞掉。测试深链接刷新、404、401 头、429/503、安全头以及选用的 streaming 行为。

不信任来自任意客户端的 forwarded 用户或 IP 字段；由受控边界清洗。避免全局缓存授权相关响应，不能把 proxy 缓存当作不需租户隔离的加速器。

## 7. Scripts 与 Tooling

```text
scripts/
├── dev/
│   ├── bootstrap.py
│   └── doctor.py
├── contracts/
│   ├── generate.py
│   └── check_generated.py
├── quality/
│   ├── check_docs.py
│   ├── check_traceability.py
│   └── check_counterexamples.py         # 定向反例编排，按已定检查实现
├── ops/
│   ├── migrate.py
│   ├── seed.py
│   ├── backup.py                         # [按需]
│   └── restore.py                        # [按需、破坏性保护]
└── miniprogram/                          # [选用]
    ├── build.mjs
    ├── preview.mjs
    └── upload.mjs

tooling/
├── typescript/
│   ├── tsconfig.base.json
│   └── eslint.base.mjs
├── architecture/
│   ├── frontend/                         # 实际选定检查器配置
│   └── backend.importlinter
├── codegen/
│   ├── typescript/
│   └── python/
└── templates/                            # [确有脚手架生成器时]
```

文件名定义位置与职责，脚本实现尚需在项目初始化完成。脚本薄到只转发一条命令且无额外价值时，可直接由 Make 调用对应工具，不制造多层 wrapper。

seed 通过受控应用能力或经过测试的专门数据导入实现，不复制业务规则。Demo 可用合成数据，但同一业务实现、同一契约，不自动回退到假后端。

## 8. 根 Makefile 命令契约

下面是要实现并验收的统一接口，不是本 Markdown 包中已经可执行的命令。

| 入口 | 责任 |
|---|---|
| `make bootstrap` | 检查平台、版本、锁安装、配置和生成 prerequisites |
| `make doctor` | 诊断选中客户端、工具、端口、外部依赖，不输出秘密 |
| `make dev` | 启动选定开发拓扑，明确客户端运行边界与退出处理 |
| `make generate` | 校验源，生成错误 schema、SDK、DTO |
| `make check-generated` | 临时干净生成，比较完整输出清单 |
| `make lint` | Python/TS/配置文件静态检查 |
| `make typecheck` | 所有已选应用与公共包类型检查 |
| `make test-unit` | 纯逻辑与隔离单元测试 |
| `make test-integration` | 真实 DB/适配器和组合验证 |
| `make test-contract` | 实际接口与错误响应契约 |
| `make test-migrations` | 迁移、数据与约束验证 |
| `make test-e2e` | 所有已选客户端的必需端到端套件 |
| `make check-architecture` | 导入方向、模块/分包与 workspace 边界 |
| `make check-specs` | spec 格式、ID、测试追踪及适用性 |
| `make check-counterexamples` | 关键规则的故障植入能被指定测试检出 |
| `make check-docs` | 当前文档链接、入口和变更关联 |
| `make verify` | 合并必需 gate 集合，不自动修改源码 |
| `make verify-release` | 合并 gate + 发布额外安全、恢复、目标环境检查 |
| `make build` | 用锁文件构建选定应用和受控制品 |
| `make migrate` | 对显式环境执行单次受控迁移 |
| `make clean` | 仅删除可再生产物，不删数据库或 secret |

性能、长时间 chaos、广泛 mutation 可以按风险和成本做发布或定期检查，但关键权限反例与目标功能 E2E 不能因为慢就默认不验收。选择范围须写入门禁矩阵。

某个已要求的套件无法执行时返回失败/阻塞，不用空测试或忽略错误让 verify 变绿。不适用套件只能根据已选 profile 明确标为 N/A 并说明理由，不能偷偷跳过。

## 9. 发布、迁移与恢复

发布顺序：冻结源与契约 → 从锁构建 → 质量/安全检查 → 测试环境真实运行 → 审查数据迁移 → 单执行者迁移 → 部署 → 健康与关键业务 smoke → 观察 → 完成记录。

先定义失效恢复策略。数据库变更可能不可逆，回滚应用版本不必然恢复数据。备份必须有恢复演练、权限与保留策略；不要只因为有 backup.py 文件就声称可恢复。

小程序上传、审核与发布可能与后端不同步；部署窗口明确旧客户端支持和错误码兼容，不用永远保留一套旧业务实现来解决版本滞后。

## 10. 可观测性与运行数据

日志是结构化事件，metrics 用于聚合，trace 关联调用，audit 记录重要安全/业务证据。每类都定义最小字段、脱敏、访问控制、保留与删除；不是把所有日志和全部请求永久写 MinIO。

若启用 Redis：记录它到底用于缓存、限流、队列还是预算运行状态，各自 key namespace、TTL、失效和故障策略。若启用对象存储：定义对象归属、授权、生命周期。PostgreSQL 保存业务和明确持久状态，不按工具名猜用途。

`make clean` 不删除真实 volume、上传文件、备份、Terraform state 或用户数据。reset、restore、destroy 是独立破坏性动作，必须显式目标、权限和确认。
