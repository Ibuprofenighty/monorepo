# 官方来源、事实边界与核验范围

文档版本：2.0｜核验日期：2026-10-02。

[返回总入口](../../README.md) · [本包检查报告](VALIDATION.md)

## 如何理解引用

本包的目录、默认工具、命令名称、自定义 YAML、分册与验收要求是工程设计建议。来源用于核实工具能力、标准字段和基础实践；不表示这些组织联合认可本母版，更不表示已经完成对某个真实应用的运行验收。

正文通过 S 编号引用相关第一方资料。下面地址放在代码标记中，便于复制；GitHub raw 文件属于对应官方项目的源文件。网页内容和工具版本会变化，初始化及升级时仍需复核，不应从网页显示的版本号推断本项目已经锁定该版本。

<a id="s01"></a>

## S01 · pnpm · Workspaces

来源：`https://pnpm.io/workspaces`

核验用途：workspace 文件、内部依赖 workspace: 协议。

<a id="s02"></a>

## S02 · uv · Using workspaces

来源：`https://docs.astral.sh/uv/concepts/projects/workspaces/`

核验用途：Python workspace 成员、各自 pyproject 和共享锁。

<a id="s03"></a>

## S03 · Feature-Sliced Design · Layers

来源：`https://feature-sliced.design/docs/reference/layers`

核验用途：分层及向下依赖、不强制使用全部层。

<a id="s04"></a>

## S04 · Feature-Sliced Design · Public API

来源：`https://feature-sliced.design/docs/reference/public-api`

核验用途：公共入口、barrel 边界和架构检查。

<a id="s05"></a>

## S05 · Vite · Getting Started

来源：`https://vite.dev/guide/`

核验用途：开发服务器与生产构建工具的定位。

<a id="s06"></a>

## S06 · Vite · Env Variables and Modes

来源：`https://vite.dev/guide/env-and-mode`

核验用途：公开环境变量与构建时替换。

<a id="s07"></a>

## S07 · Next.js · Backend for Frontend

来源：`https://nextjs.org/docs/app/guides/backend-for-frontend`

核验用途：BFF 的能力与边界，服务端组件避免额外请求本地 Route Handler。

<a id="s08"></a>

## S08 · Next.js · Data Security

来源：`https://nextjs.org/docs/app/guides/data-security`

核验用途：服务端数据、公开边界和安全传递。

<a id="s09"></a>

## S09 · Next.js · Static Exports

来源：`https://nextjs.org/docs/app/guides/static-exports`

核验用途：静态导出能力与不支持的动态服务端功能。

<a id="s10"></a>

## S10 · Feature-Sliced Design · Usage with Next.js

来源：`https://feature-sliced.design/docs/guides/tech/with-nextjs`

核验用途：_app/_pages 命名与服务端专用公共入口。

<a id="s11"></a>

## S11 · OpenAPI Specification · 3.1.1

来源：`https://spec.openapis.org/oas/v3.1.1.html`

核验用途：语言无关 HTTP 接口描述；仅引用具体规范，不称为最新版本。

<a id="s12"></a>

## S12 · IETF RFC 9457 · Problem Details for HTTP APIs

来源：`https://www.rfc-editor.org/rfc/rfc9457.html`

核验用途：Problem 媒体类型、标准成员、类型标识和扩展成员。

<a id="s13"></a>

## S13 · FastAPI · Handling Errors

来源：`https://fastapi.tiangolo.com/tutorial/handling-errors/`

核验用途：自定义异常处理与请求校验错误处理。

<a id="s14"></a>

## S14 · Pydantic · Code Generation

来源：`https://pydantic.dev/docs/validation/latest/integrations/dev-tools/datamodel_code_generator/`

核验用途：datamodel-code-generator 集成；工具是否满足项目 schema 须另验证。

<a id="s15"></a>

## S15 · pytest · Good Integration Practices

来源：`https://docs.pytest.org/en/stable/explanation/goodpractices.html`

核验用途：src layout、安装包与测试导入方式。

<a id="s16"></a>

## S16 · Architecture Patterns with Python · Repository Pattern

来源：`https://www.cosmicpython.com/book/chapter_02_repository`

核验用途：作者原始在线说明：repository 和依赖倒置。

<a id="s17"></a>

## S17 · Alembic · Auto Generating Migrations

来源：`https://alembic.sqlalchemy.org/en/latest/autogenerate.html`

核验用途：自动迁移的能力与限制、人工审查要求。

<a id="s18"></a>

## S18 · OWASP · Error Handling Cheat Sheet

来源：`https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html`

核验用途：对外安全错误与服务器诊断分离。

<a id="s19"></a>

## S19 · OWASP · Authorization Cheat Sheet

来源：`https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html`

核验用途：身份/授权区分、默认拒绝、最小权限与正确执行位置。

<a id="s20"></a>

## S20 · OWASP · Session Management Cheat Sheet

来源：`https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html`

核验用途：会话凭据、生命周期和保护措施。

<a id="s21"></a>

## S21 · 微信官方示例 · project.config.json

来源：`https://raw.githubusercontent.com/wechat-miniprogram/miniprogram-demo/master/project.config.json`

核验用途：小程序代码根、工程编译类型与 TypeScript 编译配置示例；不沿用示例版本或 AppID。

<a id="s22"></a>

## S22 · 微信官方示例 · package.json

来源：`https://raw.githubusercontent.com/wechat-miniprogram/miniprogram-demo/master/package.json`

核验用途：官方示例使用的工程依赖，含 miniprogram-ci 和 miniprogram-automator。

<a id="s23"></a>

## S23 · 微信官方 API typings

来源：`https://raw.githubusercontent.com/wechat-miniprogram/api-typings/master/types/wx/lib.wx.api.d.ts`

核验用途：wx.request 返回结构，以及 wx.login code 在服务器用于 code2Session。

<a id="s24"></a>

## S24 · Docker · Build context

来源：`https://docs.docker.com/build/concepts/context/`

核验用途：构建上下文与 COPY 可见范围。

<a id="s25"></a>

## S25 · Import Linter · Documentation

来源：`https://import-linter.readthedocs.io/en/stable/`

核验用途：导入约束检查工具；仍需项目实际配置。

<a id="s26"></a>

## S26 · Docker Compose · Merge files

来源：`https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/`

核验用途：多文件合并和路径基准。

<a id="s27"></a>

## S27 · Docker · Build secrets

来源：`https://docs.docker.com/build/building/secrets/`

核验用途：构建秘密传入与不应使用普通 ARG/ENV 保存秘密。

<a id="s28"></a>

## S28 · Next.js · proxy.js convention

来源：`https://nextjs.org/docs/app/api-reference/file-conventions/proxy`

核验用途：Proxy 文件约定与版本迁移信息。

<a id="s29"></a>

## S29 · Next.js · Server and Client Components

来源：`https://nextjs.org/docs/app/getting-started/server-and-client-components`

核验用途：服务端/客户端组件、交互与数据边界。

<a id="s30"></a>

## S30 · Next.js · Self-Hosting

来源：`https://nextjs.org/docs/app/guides/self-hosting`

核验用途：自托管部署与运行时考虑。

<a id="s31"></a>

## S31 · Hypothesis · Documentation

来源：`https://hypothesis.readthedocs.io/en/latest/`

核验用途：属性测试与自动生成输入。

<a id="s32"></a>

## S32 · Playwright · Best Practices

来源：`https://playwright.dev/docs/best-practices`

核验用途：用户可见行为与测试隔离。

<a id="s33"></a>

## S33 · NIST · Secure Software Development Framework

来源：`https://csrc.nist.gov/projects/ssdf`

核验用途：SSDF 的安全开发框架定位；未把它解释成单一目录或固定编码顺序。

<a id="s34"></a>

## S34 · Nginx · ngx_http_proxy_module

来源：`https://nginx.org/en/docs/http/ngx_http_proxy_module.html`

核验用途：proxy_pass 的 URI 行为与响应缓冲。

<a id="s35"></a>

## S35 · Docker Compose · Startup order

来源：`https://docs.docker.com/compose/how-tos/startup-order/`

核验用途：启动顺序、健康条件与就绪差异。

<a id="s36"></a>

## S36 · uv · Using uv in Docker

来源：`https://docs.astral.sh/uv/guides/integration/docker/`

核验用途：uv 的容器构建及 workspace 相关注意事项。

<a id="verification-limits"></a>

## 本次核验限制

微信开发者站部分页面本次未能直接读取，包括普通分包、独立分包、网络能力和 CI 指南。已直接核验官方 GitHub 示例配置、工程依赖及 API 类型定义；没有用无法读取的网页声称已核验全部平台限制。

未成功读取的官方入口如下，实施时需要再核对：

```text
https://developers.weixin.qq.com/miniprogram/dev/framework/subpackages/basic.html
https://developers.weixin.qq.com/miniprogram/dev/framework/subpackages/independent.html
https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html
https://developers.weixin.qq.com/miniprogram/dev/devtools/ci.html
```

因此本包不固定小程序当前包体积限额，不保证特定 Linux CI 可以启动 GUI/真机，也不把账户审核、域名、隐私要求或发布状态当作已验证事实。小程序使用保守依赖规则，所选构建路线须由真实项目完成集成实验。

本次没有对任何目标项目安装依赖、运行 Docker、编译 Next/Vite 或打开微信开发者工具。所交付是规范与模板。实际完成的文件检查见独立检查报告。

## 与旧文件的关系

本包基于本对话提供的 `MONOREPO_BLUEPRINT.zh-CN.md` 1.0、旧 ZIP 内的 AGENTS/spec 模板，以及后续关于 Error Code、Next.js 和微信小程序的修正整理。旧文件是输入材料，不是本版同时有效的另一组执行规则。

## 版本维护

更新本包时改动所属权威分册，必要时升级文档版本，检查引用和跨端约定。项目真实依赖由锁文件和版本策略维护，不在所有说明文档重复手填“最新版本”。
