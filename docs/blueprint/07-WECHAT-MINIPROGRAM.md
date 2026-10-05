# 07 · 原生微信小程序：TypeScript + Python API

版本：2.0｜日期：2026-10-02｜适用选项：`wechat-native`。

[返回总入口](../../README.md) · [SDK](02-CONTRACTS-SDK.md) · [安全](08-AUTH-SECURITY.md)

## 1. 最终方案与非目标

默认原生 TypeScript + WXML + WXSS，Python 提供业务 API。保留 monorepo、contracts、错误码、模块化、权限、测试与文档；不照搬 React DOM、Next 路由或浏览器 HTTP 实现。

微信官方示例包含独立的项目配置、代码根与 TypeScript 编译设置；官方提供 API 类型定义。[S21](SOURCES.md#s21) [S23](SOURCES.md#s23) 本分册的 FSD-inspired 分层与构建流水线是项目工程选择，不宣称为微信官方统一模板。

无需为了这个方案创建 `apps/web`、云函数后端或 MQTT 服务。是否有设备通信、云开发或消息系统，由实际项目契约决定。

## 2. 单一构建路线

为了使 pnpm workspace SDK 的消费方式可控制，本模板选定：**人工源码在 `src/`，仓库构建器生成可运行 `dist/`，开发者工具读取 dist。**

不是“DevTools 自动编译 TS”与“仓库再编译 TS”同时启用。仓库拥有 TS 转换和模块打包，工具负责验证、预览与平台交付；平台必要的压缩/处理选项按所选版本明确配置。

这是对前面代码根示例的收敛：不再同时保留 `miniprogram/` 人工源码和 `src/` 人工源码。所有开发修改只在 src，dist 由 clean build 重建。

## 3. 完整应用目录

```text
apps/miniprogram/
├── README.md
├── package.json
├── tsconfig.json
├── eslint.config.mjs
├── project.config.json                 # miniprogramRoot 指向 dist/
├── project.private.config.json         # [本地][忽略]
├── src/
│   ├── app.ts
│   ├── app.json
│   ├── app.wxss
│   ├── sitemap.json
│   ├── typings/                        # 本应用额外类型，按需
│   ├── pages/                          # 主包实际入口页面
│   │   └── home/
│   │       ├── index.ts
│   │       ├── index.json
│   │       ├── index.wxml
│   │       └── index.wxss
│   ├── features/                       # 主包真正需要的交互
│   │   └── sign-in/
│   │       ├── model/
│   │       └── api/
│   ├── entities/                       # 主包所需业务表示，按需
│   ├── shared/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── wechat-transport.ts
│   │   │   └── client-errors.ts
│   │   ├── config/
│   │   ├── session/                    # 明确的客户端会话适配
│   │   ├── ui/                         # 原生自定义组件
│   │   └── lib/
│   └── subpackages/                    # [按实际规模]
│       └── catalog/
│           ├── pages/
│           │   └── resource-detail/
│           │       ├── index.ts
│           │       ├── index.json
│           │       ├── index.wxml
│           │       └── index.wxss
│           ├── features/
│           │   └── delete-resource/
│           │       ├── model/
│           │       └── api/
│           └── entities/
│               └── resource/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── build/                          # 输出结构和打包规则
└── dist/                               # [生成][忽略] 真正小程序代码根
```

根工程自动化目录：

```text
scripts/miniprogram/
├── build.mjs                           # 构建编排，需实现和测试
├── preview.mjs                         # 显式调用已选平台工具
└── upload.mjs                          # 环境保护、制品和版本标识

tests/e2e/miniprogram/                  # 小程序运行环境的关键用户故事
```

文件名是需要实现的入口，不代表本包附带可运行构建器。

项目配置核心片段如下；AppID、版本、设置必须按真实项目补齐，不能把片段当完整配置：

```json
{
  "compileType": "miniprogram",
  "miniprogramRoot": "dist/"
}
```

## 4. 构建器必须负责的事情

从 `src/app.json` 和组件配置读取页面/分包/组件入口；TS 转 JS；处理内部 workspace 依赖；复制 WXML/WXSS/JSON/静态资源；维护相对路径；校验最终引用存在。不能只执行 `tsc` 就宣称完成全部小程序打包。

目标模块格式、语言级别和运行时能力按所选基础库验证；保留 `App`、`Page`、`Component` 注册副作用，不能被 tree shaking 误删。WXS 及特殊资源按其平台规则处理，不假装全是普通 TS。

公共 SDK 使用构建器解析唯一 workspace 源并打入可运行制品；最终包不能依赖仓库外 symlink、Node 内建模块、浏览器全局或线上不存在的 npm 路径。

同一源码编译进多个隔离制品不等于手写双实现。禁止复制 SDK 源到小程序后人工维护第二份。

必须有构建集成样例：一个页面、一个组件、一个分包、一个共享 SDK 调用、一个公开错误、资源引用及删除文件后无旧产物残留。未通过这个样例，不推广整项目。

## 5. 分层与分包：两个约束同时满足

逻辑上采用页面编排 → feature → entity → shared。物理分包先满足发布和加载要求，不能为了模仿 Web 目录把所有业务代码提升到主包。

本模板默认禁止主包同步依赖分包、普通分包彼此同步深导入；分包专属业务放本分包。需要公共能力时评估是否真正适合主包承担。此处是保守的项目依赖规则，不声称平台没有任何高级异步分包机制。

默认不启用独立分包。确需启用必须单独验证独立启动、公共依赖、会话和产物自包含；不能照搬普通分包假设。官方分包页面本次未成功读取，相关平台限制和配置需在实施时复核，见 [来源范围说明](SOURCES.md#verification-limits)。

不写死长期不变的包体积限额或所有设备行为；在 project-profile 记录当前账户和基础库条件，构建时检查实际包体积及依赖图。

## 6. wx.request transport

微信请求回调返回 `statusCode`、`data`、`header` 等，客户端不能将 success 回调等同于 HTTP 2xx 或业务成功。[S23](SOURCES.md#s23)

适配器需要做到：可信 base URL + 契约 path 组合、参数编码、超时、取消、响应头标准化、成功响应解析、Problem 解析、非法响应处理、网络故障分类。未知公开错误必须有兜底。

`wx` 的平台错误与远端业务 code 分开。超时的写请求可能已在后端执行，不能自动重试直到成功；按操作幂等契约处理。需要上传、下载、流式或 socket 时使用其专用适配与测试，不强行套普通 JSON transport。

`api-client` 公共层不包含 DOM Response、window、localStorage 或微信专用 UI。浏览器 fetch 能运行不证明 wx.request 路径能运行。

## 7. 登录与用户关联

```text
wx.login 获取临时 code
  → Python 身份接入端点
  → 服务端调用 code2Session
  → 用经过验证的外部身份关联内部用户
  → 建立本系统的业务会话
  → 后续请求进入统一 AuthN/AuthZ 与业务用例
```

官方类型定义说明 code 用于服务器调用 code2Session。[S23](SOURCES.md#s23) AppSecret、session_key 等不得进入小程序包、普通日志或公开响应；不要把客户端提供的 openid 当作验证完成。

外部身份关联键必须包含相应提供方与应用范围；不要假设所有账户都会提供可跨应用统一的标识。与 Keycloak 等既有身份系统集成时，先明确账户关联和 token 颁发归属，禁止另造第二份互相不一致的用户权限库。

授权服务不因客户端变成微信而改变业务含义。系统内部用户是业务主体，微信身份是一个经过验证的登录来源。

## 8. 页面生命周期与数据

请求返回可能晚于页面退出；卸载时取消或忽略过期结果。会话变化、重新进入、下拉刷新与重复点击要有明确状态行为，不能只验证首次打开页面。

视图数据保持可序列化、最小化；不要将服务端密钥、完整用户隐私对象或大型 SDK 对象送入视图。原生组件不能按浏览器 DOM 事件和 CSS 特性想当然实现。

错误、加载、空数据、拒绝与离线状态都要有真实界面。模拟数据只存在测试/开发组合，不作为正式构建的默认回退。

## 9. 开发环境与发布

小程序开发者工具运行于其支持的桌面环境；后端可在 Docker/WSL/Linux 中。仓库命令必须明确哪个步骤在哪个系统执行，不把 Linux 上的纯 TS 构建描述为已运行微信 GUI。

Windows 与 WSL 不共享同一套安装出的跨平台二进制依赖，避免路径和 symlink 偶然可用。原生工具路径、CLI 开关、账户权限和设备访问由 doctor 检查并记录。

真机访问后端需真实可达地址；手机上的 localhost 不代表开发电脑。生产域名、HTTPS、网络能力、隐私声明和发布前置条件按当前账户规则复核。不得把开发环境关闭域名检查作为上线方案。

官方示例使用 `miniprogram-ci` 与 `miniprogram-automator` 相关依赖，说明这些是可调研的实际工具；不据此承诺任何 Linux CI 都能完成真机或 GUI 验收。[S22](SOURCES.md#s22)

上传/预览/发布为不同步骤。上传成功不代表审核完成、已发布或真实用户功能验收通过。签名/上传私钥只通过受控 secret 注入。

## 10. 最小真实验收

| 层 | 证据 |
|---|---|
| 纯逻辑 | TS 单元测试、状态和错误映射 |
| 构建 | clean build、SDK 可达、引用完整、无越界模块 |
| 请求 | HTTP 错误、网络失败、取消、会话过期 |
| 小程序运行 | 开发者工具加载实际 dist、页面和组件正常 |
| 真实后端 | 登录、读取、修改、拒绝和状态验证 |
| 平台特性 | 分包、页面重入、目标设备功能，按需 |
| 真机 | 关键完整用户故事，记录设备/版本与结果 |
| 交付 | 制品版本、审核发布责任、rollback/恢复策略 |

不能用 Playwright 的 Web 页面、React 截图、模拟设备协议或 Node 测试取代原生小程序运行证据。权限或设备缺失时标记 BLOCKED，记录已经验证和未验证的边界。
