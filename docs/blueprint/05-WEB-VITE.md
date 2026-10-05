# 05 · Web SPA：React + Vite

版本：2.0｜日期：2026-10-02｜适用选项：`web-vite`。

[返回总入口](../../README.md) · [项目选型](00-PROJECT-PROFILE.md) · [Next.js 替代选项](06-WEB-NEXTJS.md)

## 1. 使用边界

本选项面向以浏览器交互为主、不需要应用框架服务端页面能力的 Web 应用。Vite 官方将其定位为开发与构建工具；不是完整业务后端，也不是架构中的必选组件。[S05](SOURCES.md#s05)

Python 仍拥有业务规则、权限、数据库写入。不要把开发代理误认为生产部署，也不以 Vite 的预览服务器承担已批准生产部署方案之外的职责。

## 2. 完整前端目录

```text
apps/web/
├── README.md
├── package.json
├── index.html
├── vite.config.ts
├── vitest.config.ts
├── tsconfig.json
├── eslint.config.mjs
├── public/                              # 公开静态资源，无用户秘密
├── src/
│   ├── main.tsx
│   ├── vite-env.d.ts
│   ├── app/
│   │   ├── providers/
│   │   ├── router/
│   │   ├── styles/
│   │   └── error-boundary/
│   ├── pages/
│   │   ├── resource-list/
│   │   │   ├── ui/ResourceListPage.tsx
│   │   │   ├── api/                      # 页面专属数据适配，按需
│   │   │   └── index.ts
│   │   └── resource-detail/
│   │       ├── ui/ResourceDetailPage.tsx
│   │       └── index.ts
│   ├── widgets/                          # [可选] 大型独立复用 UI 块
│   │   └── resource-browser/
│   │       ├── ui/ResourceBrowser.tsx
│   │       └── index.ts
│   ├── features/
│   │   └── delete-resource/
│   │       ├── ui/
│   │       │   ├── DeleteResourceButton.tsx
│   │       │   └── DeleteResourceButton.test.tsx
│   │       ├── model/
│   │       │   ├── use-delete-resource.ts
│   │       │   ├── use-delete-resource.test.ts
│   │       │   └── error-presentation.ts
│   │       ├── api/delete-resource.ts
│   │       └── index.ts
│   ├── entities/
│   │   └── resource/
│   │       ├── model/resource-view.ts
│   │       ├── api/resource-queries.ts
│   │       ├── ui/ResourceCard.tsx
│   │       └── index.ts
│   └── shared/
│       ├── api/
│       │   ├── client.ts
│       │   ├── browser-transport.ts
│       │   └── client-errors.ts
│       ├── config/env.ts
│       ├── ui/
│       │   └── button/
│       │       ├── Button.tsx
│       │       ├── Button.test.tsx
│       │       └── index.ts
│       ├── lib/date-format/
│       └── i18n/                        # [按需]
├── tests/
│   ├── setup.ts
│   ├── integration/
│   └── mocks/
└── dist/                                # [生成][忽略]
```

跨应用 E2E 放根 `tests/e2e/web/`，不在应用目录再复制一套同义端到端流程。

## 3. FSD 依赖纪律

允许向下依赖：`app → pages → widgets → features → entities → shared`。不要求经过每层。同层业务 slice 默认不能互相导入；需要编排由上层完成。FSD 官方也明确不是每个项目都需要全部层。[S03](SOURCES.md#s03)

跨 slice 只访问明确公共入口；slice 内用相对导入，不反向经过自己的 barrel。Shared 按用途提供小入口，不建立导出所有模块的大 index。公共 API 本身不能强制边界，需要 lint 规则验证。[S04](SOURCES.md#s04)

本模板默认不启用跨 entity 的特殊引用机制。确有关系模型需求，通过 ADR 说明最小例外并在检查器中限制，不能让 Agent 自由绕过同层边界。

## 4. 状态、请求和副作用放在哪里

组件局部展示状态留组件；功能交互状态留 feature；实体展示和查询语义留 entity；页面编排留 page；全应用 provider 和路由在 app。

`shared/api/client.ts` 配置生成 SDK，`feature/api` 可以负责 mutation、query key 和缓存失效，但不能手写同一 endpoint 的另一套 DTO 和序列化。

请求身份变化、退出登录或切换组织时，处理请求取消和缓存隔离。禁止多个用户共享不含身份/范围的敏感结果缓存。服务端授权始终最终生效；前端权限只改善体验。

## 5. 错误与表单

公开错误类型从 api-client 生成定义导入。特定功能对已知错误提供可恢复操作；公共层仅负责通用网络/会话故障。不用英文 detail 作为程序判断条件，不把未知服务器响应原样弹出。

表单约束引用契约或同源生成的边界校验；客户端校验改善输入体验，服务端仍完整验证。异步请求区分 idle/loading/success/empty/error 等适用状态；重复点击的界面禁用不是后端幂等保证。

## 6. 配置与部署

本选项默认同源 `/api` 访问 Python API。路由前缀只拥有一次，避免 base URL 与 OpenAPI path 重复叠加 `/api`。开发代理配置在 Vite，生产代理配置在已选 Nginx/边缘网关。

`VITE_*` 是公开构建配置，通常在构建时替换；改变运行中的 Nginx 环境变量不会自动重写已有 JavaScript。[S06](SOURCES.md#s06)

需要跨环境提升同一镜像时，优先同源相对地址；仍需要差异公开配置才设计一个运行时配置文件，由部署生成并校验，不同时维护两套互相冲突的配置。

生产构建输出静态产物。默认 Web 镜像由构建阶段产生 dist、Nginx 阶段提供资源并代理 API；部署细节由 [Infra 分册](09-INFRA-OPERATIONS.md) 统一拥有。

## 7. 用户界面验收

关键路径测试至少覆盖输入、加载、空数据、成功、业务拒绝、网络失败、会话失效。键盘访问、焦点、表单标签、必要提示、布局与目标设备适配应按产品范围验收。

API mock 只用于独立组件或前端集成测试，必须符合源契约。最终关键 E2E 使用真实后端和隔离数据。不能把静态 HTML 演示当成真实 React 应用已经接通后端。

## 8. 工程门禁

typecheck、lint、组件单测、契约生成无漂移、FSD 边界、生产 build、深链接刷新、API 错误处理、前后端真实 E2E。产物检查不含服务端凭据、开发 mock 或错误的内部地址。

选用本方案就不保留 `next.config.ts`、Next app router 或旧 SSR 服务作为平行生产入口。保留 Next 规范分册作为未选参考，不意味着创建 Next 应用代码。
