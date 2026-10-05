# 02 · Contract、Schema 与跨客户端 SDK

版本：2.0｜日期：2026-10-02｜权威范围：接口来源、生成链路、客户端传输边界。

[返回总入口](../../README.md) · [错误码](03-ERROR-CODES.md) · [测试](10-TESTING-HARNESS.md)

## 1. 唯一来源

本母版选择 contract-first。人工维护 HTTP 源契约；从它生成 TS 类型/接口操作和 Python 边界 DTO。FastAPI 自动导出的 OpenAPI 可以参与检查，但不是第二个独立手工真源。

OpenAPI 提供语言无关的 HTTP 描述；具体版本须与生成器兼容。本文引用 3.1.1 说明规范，不声称它是最新版本。[S11](SOURCES.md#s11)

```text
contracts/
├── README.md
├── errors/
│   ├── common.yaml                      # 公开错误的人工定义
│   └── catalog.yaml
├── http/
│   ├── openapi.yaml                      # 人工入口，引用分文件
│   ├── paths/
│   │   └── resources.yaml
│   ├── components/
│   │   ├── schemas/
│   │   │   ├── Resource.yaml             # 人工业务 wire schema
│   │   │   ├── Problem.yaml              # 人工基础错误结构
│   │   │   └── Errors.generated.yaml      # [生成] 注册表派生的错误约束
│   │   ├── parameters.yaml
│   │   └── security-schemes.yaml
│   └── examples/
│       └── resource.json
└── events/                              # [可选]
    ├── asyncapi.yaml
    └── schemas/

packages/ts/api-client/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts                         # 小范围公共入口
│   ├── generated/
│   │   ├── models.ts
│   │   ├── operations.ts
│   │   └── errors.ts
│   └── runtime/
│       ├── transport.ts                 # 平台无关接口
│       ├── problem.ts                   # 公共错误解析，不重写错误枚举
│       └── result.ts                    # 本 SDK 的返回/失败协议
└── tests/
    ├── serialization.test.ts
    ├── problem.test.ts
    └── transport-contract.test.ts
```

Python 对应生成到 `apps/backend/src/project_backend/generated/http/`。`models.py` 与 `errors.py` 应引用共享生成定义，不产生两份独立维护枚举。

## 2. 生成流程必须无环

```text
人工 contracts/errors/*.yaml
  → Errors.generated.yaml

人工 OpenAPI（引用上面的派生文件）
  → 校验与 bundle
  → TS models / operations / errors
  → Python HTTP DTO / errors
  → 对外文档与测试输入
```

发布用 bundle、HTML、报告进 `.artifacts/` 或制品库。默认将 TS/Python 生成源码和被源契约引用的派生 schema 提交 Git，便于 review；所有生成产物必须标注来源和生成命令。

不能把生成输出重新作为下一次人工输入，也不能在生成目录夹带手写文件。工具配置、模板变更必须与生成输出一起 review。Pydantic 官方介绍了从 OpenAPI 等生成模型的工具，但工具可用不代表已经支持你选的全部 schema 特性。[S14](SOURCES.md#s14)

## 3. 契约需要描述什么

| 类型 | 最低内容 |
|---|---|
| 操作 | 稳定 operationId、方法、路径、主体/资源语义 |
| 输入 | required 与 nullable、枚举、范围、长度、格式、附加字段策略 |
| 参数 | path/query/header 的编码、数组和重复值规则 |
| 输出 | 成功状态、媒体类型、空响应、分页、排序稳定性 |
| 失败 | 可返回的公开错误、HTTP 状态、安全响应头 |
| 并发 | 乐观版本、冲突与重试前置条件，适用时 |
| 幂等 | key 范围、请求指纹、有效期、并发同 key 行为，适用时 |
| 身份 | 凭据方式；OpenAPI security 声明不代替业务授权 |
| 示例 | 来自规范的有效/无效样例，不复制真实秘密或生产 PII |

一项不适用可省略并说明，不把全表变成每个简单 GET 的繁重模板。

## 4. 模型分别承担不同语义

HTTP DTO 描述网络格式；domain 描述业务状态与不变量；ORM 描述持久化；view model 描述界面。它们不必逐字段一致，不允许把 ORM 直接对外公开。不同语义的映射不是应删除的重复。

前端不可手写另一套等价 HTTP 类型；展示模型可以引用生成类型后增加界面语义。TypeScript 编译期类型不会自动检查远端 JSON；边界运行时校验必须明确选择生成校验器或经过测试的解析方式。

服务端生成 DTO 不会自动实现 route、权限、事务、状态码或副作用规则。实际接口测试仍是必要门禁。

## 5. SDK 的 transport 设计

公共 SDK 不直接依赖 `window`、DOM `Response`、React、Next 路由、`wx`、浏览器存储或服务端 secret。每个客户端注入适配器。

| 消费方 | 适配位置 | 责任 |
|---|---|---|
| Vite | `apps/web/src/shared/api/browser-transport.ts` | 浏览器请求、会话传递 |
| Next 浏览器 | `apps/web/src/shared/api/browser.ts` | 只可使用公开配置和客户端凭据 |
| Next 服务端 | `apps/web/src/shared/api/server.ts` | 请求级上下文、可信后端地址、server-only |
| 微信 | `apps/miniprogram/src/shared/api/wechat-transport.ts` | wx.request、状态码、取消、超时与平台错误 |

推荐 transport 契约用纯数据：method、相对 path、headers、明确序列化后的 body、timeout；结果是 status、headers、body。取消可用项目自定义 handle/callback，不强制所有平台实现 DOM AbortSignal。具体接口要与已选生成器结合验证，不能写一个接口便声称所有生成器自动支持。

只有两个以上真实调用方需要相同 transport 实现时再抽内部包。适配层不允许改变 endpoint 业务语义，不为某个客户端另做一套含义不同的错误码。

## 6. 序列化与重试规则

业务操作定义路径参数编码、query 编码、JSON 空值、日期时区、金额与大整数表示。不要默认 JSON number 能无损表达任意精度值；精度敏感类型在契约里明确字符串或安全数值边界。

SDK 不全局对所有失败自动 retry。重试取决于操作是否可安全重复、失败是否已产生副作用、剩余期限与次数；429/503 也不是“无限重试”的许可。登录刷新有界，禁止多个拦截器相互递归刷新。

上传、流式响应、WebSocket、文件下载不能假装普通 JSON 请求。使用它们时建立专门契约和各平台能力矩阵，没有需求则不预建。

## 7. 接口演进与旧客户端

同一代码仓库不等于同一时刻发布：小程序安装版本、Web 缓存、第三方客户端可能滞后。新增可选字段通常比删除字段更容易保持兼容，但生成器是否封闭枚举、是否拒绝未知字段仍须实测。

公开错误要有未知码兜底。破坏性变更需明确客户端最低版本与退役计划；保留稳定契约不等于保留旧业务实现。不得在“所有旧客户端无法同时更新”时谎称一次提交即可无损替换。

## 8. 生成与契约验收

`make check-generated` 在干净临时目录生成，比较完整文件集合：新增、修改、删除都要检测。不能只用已跟踪文件的 diff 漏掉新文件。固定工具、模板、参数、编码和排序；禁止时间戳造成无意义漂移。

`make test-contract` 必须验证实际运行应用：方法/路径、参数、成功与错误状态、Content-Type、空响应、认证挑战和边界数据。导出 schema 的比较只是一项检查，不是运行行为证明。

删除 schema 必须删除失效生成输出和消费代码。测试生成器时设置一个故意改名/删字段/错状态码的样例，证明检查会失败。

## 9. 非目标

本分册不提供已经完成的 codegen runner，也不承诺特定生成器的跨平台 transport 可零修改使用。初始化时先完成“一个接口 + 一个公开错误 + 一个非 2xx 响应 + 一个小程序请求”的端到端生成实验，再推广到全项目。
