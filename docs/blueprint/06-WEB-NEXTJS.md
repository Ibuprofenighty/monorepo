# 06 · Web 框架：Next.js + 独立 Python 后端

版本：2.0｜日期：2026-10-02｜适用选项：`web-next`。

[返回总入口](../../README.md) · [项目选型](00-PROJECT-PROFILE.md) · [Vite 替代选项](05-WEB-VITE.md)

## 1. 选择与边界

采用 App Router。Next.js 负责页面、服务端/客户端渲染以及必要的 Web 适配；Python 继续负责业务规则、最终授权、事务与业务持久化。Next.js 支持 BFF，不要求把既有独立后端搬进 Route Handlers。[S07](SOURCES.md#s07)

Vite 不是这套 monorepo 的必选条件。选 Next.js 后删除该应用中不再使用的 Vite 入口，不保留两套构建配置以便“随时 fallback”。

## 2. 目录

```text
apps/web/
├── README.md
├── package.json
├── next.config.ts
├── next-env.d.ts                         # [框架生成]
├── tsconfig.json
├── eslint.config.mjs
├── vitest.config.ts                      # [选用] 适用的纯函数/组件测试
├── proxy.ts                              # [按需、按已选版本约定]
├── instrumentation.ts                   # [按需]
├── public/
├── app/                                  # Next 框架路由与框架约定文件
│   ├── layout.tsx
│   ├── page.tsx
│   ├── loading.tsx                       # [按需]
│   ├── error.tsx                         # [按需]
│   ├── not-found.tsx                      # [按需]
│   ├── resources/
│   │   └── [id]/page.tsx
│   └── api/                              # [仅真实需要的 BFF]
│       └── session/route.ts
├── src/
│   ├── _app/                             # FSD 应用组装
│   │   ├── providers/
│   │   ├── styles/
│   │   └── api-routes/                    # [按需] BFF 路由实现
│   ├── _pages/                           # FSD 页面实现
│   │   └── resource-detail/
│   │       ├── ui/ResourceDetailPage.tsx
│   │       ├── api/get-resource.server.ts
│   │       ├── index.ts                   # 仅安全的公共导出，按需
│   │       └── index.server.ts            # 仅服务端导出，按需
│   ├── widgets/
│   ├── features/
│   │   └── delete-resource/
│   │       ├── ui/DeleteResourceButton.tsx
│   │       ├── model/error-presentation.ts
│   │       ├── api/
│   │       │   └── delete-resource.ts
│   │       └── index.ts
│   ├── entities/
│   │   └── resource/
│   │       ├── model/resource-view.ts
│   │       ├── ui/ResourceCard.tsx
│   │       └── index.ts
│   └── shared/
│       ├── api/
│       │   ├── browser.ts
│       │   ├── server.ts                 # 标记 server-only
│       │   └── client-errors.ts
│       ├── config/
│       │   ├── public.ts
│       │   └── server.ts                 # 标记 server-only
│       ├── ui/
│       └── lib/
├── tests/
│   ├── unit/
│   └── integration/
├── .next/                                # [生成][忽略]
└── out/                                  # [仅静态导出][生成][忽略]
```

FSD 官方建议避免 `app/pages` 名称与 Next 路由冲突，将 FSD 层改为 `_app/_pages`。服务端专用导出可用 `index.server.ts` 隔离，避免污染客户端模块图。[S10](SOURCES.md#s10)

`proxy.ts` 只在确有需要时建立；Next 16 的约定从 middleware 改称 Proxy。初始化核对实际版本，不同时保留两个同义中间层，也不把 Proxy 当作业务授权权威。[S28](SOURCES.md#s28)

## 3. 路由入口不是第二份页面实现

`app/resources/[id]/page.tsx` 负责框架参数、metadata 和必要组装，再调用 `_pages/resource-detail`。核心页面不在两个位置重复实现。框架要求留在约定路径的代码可以保留，不为极端“薄”而制造毫无意义的间接层。

依赖仍是 `_app → _pages → widgets → features → entities → shared`，不是 Next 路由目录随意深导入所有 slice 内部。

## 4. Server 与 Client 的边界

需要浏览器事件和本地交互的组件进入客户端边界；服务端配置、后端访问凭据、服务端数据函数不得导出到可被客户端 import 的公共 barrel。

Client Component 接收的 props 必须是批准可公开的数据，并符合框架序列化要求。服务端获取了数据不意味着全量对象可以传给客户端。Next 官方说明了 Server/Client 组件边界以及数据安全要求。[S08](SOURCES.md#s08) [S29](SOURCES.md#s29)

UI 中“没有渲染”不等于数据没有发送；真实产物和网络流量都要检查。用户级 SDK/client 实例不应将一个请求的凭据保存在所有请求共享的可变全局。

## 5. 请求拓扑：先选择，不能叠加三遍

**默认服务端读取：** Server Component → Python API。不要让它先请求自己站点的 Route Handler，再由 Route Handler 请求 Python。官方 BFF 指南明确提醒这种额外跳转。[S07](SOURCES.md#s07)

**浏览器调用：** 根据会话方案选择直接同源代理到 Python，或者调用必要的 BFF。代理/BFF 的目标列表固定，不能做允许任意用户 URL 的开放转发器。

**Server Action：** 可以承担 Web 交互适配，但仍调用 Python 用例 API。每次操作都必须有真实身份与授权检查；不能因为某函数标记服务端就视为可信业务入口。

对浏览器公开的 `/api/session` 等 BFF 路径与 Python 业务路径要有唯一归属。反向代理不得让同一个 URL 随环境落到不同含义的实现。

## 6. 业务与权限不复制

Next 不直接修改业务 PostgreSQL 表，不重写 Python 的订单、资源、权限判定。BFF 的会话状态属于它自己的适配职责，不等于可以绕过 Python 业务权威。

必要的早期安全拒绝可减少无效流量，但 Python 中仍要执行最终业务授权。来自 BFF 的身份必须有可信传递协议，不只信任调用网络位置。

## 7. 渲染与缓存必须按数据分类

| 数据类型 | 本模板要求 |
|---|---|
| 完全公开且可共享 | 明确允许缓存、有效期和失效责任 |
| 用户/组织敏感 | 默认不共享缓存；需要缓存时明确定义身份与范围键 |
| 权限相关结果 | 定义撤销和政策变化后的失效，不只按 URL 缓存 |
| mutation 后页面 | 明确更新、刷新或 revalidation，避免旧状态 |

不依赖“Next 默认会怎样缓存”的模糊记忆。缓存默认和 API 会随版本变化；固定版本、显式设置，并用两个不同主体测试不会串数据。服务端 SDK 若不是框架 fetch 路径，不能假设自动获得全部框架缓存行为。

## 8. 错误处理

预期业务错误使用公开 Error Code 显示对应交互；边界错误页面用于未预期渲染失败等适用情况。不要为了显示锁定提示抛出含内部上下文的异常，再期待框架原样序列化。

BFF 保留经批准的 Problem 字段和必要响应头；认证、缓存、Set-Cookie 等分别按方案处理，不能机械转发所有上游头或秘密。未知异常只公开安全提示。

## 9. 两种生产部署只能选清楚

**服务端运行：** Web Dockerfile 构建 Next 应用并运行受支持服务端产物；Python 是独立服务。反向代理、TLS、健康检查、终止与日志由 Infra 分册管理。官方自托管指南提供部署边界参考。[S30](SOURCES.md#s30)

**静态导出：** 构建静态文件，由静态托管提供。只能使用静态模式支持的能力；不得同时要求请求时 cookie 读取、动态 Server Actions 等服务端行为却只部署静态文件。[S09](SOURCES.md#s09)

不把 Next 所有模式硬编码成“必须 Node 常驻”，也不把所有 Next 构建结果都当作可由 Nginx 直接提供的静态站点。

## 10. 验收

框架路由与 FSD 边界、server-only 泄漏检查、生产 build、真实 SSR/静态模式运行、跨用户缓存隔离、会话续期与撤销、Python 的最终拒绝、深链接、未知 Error Code 和完整用户故事。

纯组件单测不能证明异步服务端页面或部署缓存行为。能力不适合单元环境时在框架集成和 E2E 中验证，不写一个没有执行真实路径的 mock 测试掩盖缺口。
