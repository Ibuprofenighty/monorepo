# 03 · Error Code、异常与错误响应

版本：2.0｜日期：2026-10-02｜本文件是公开错误治理的权威说明。

[返回总入口](../../README.md) · [契约与 SDK](02-CONTRACTS-SDK.md) · [安全](08-AUTH-SECURITY.md)

## 1. 归属结论

**公开 Error Code 放 `contracts/errors/`，唯一手工维护。内部异常放所属模块；HTTP 映射放 presentation；通用响应处理放 platform；提示文案放客户端。**

| 对象 | 位置 | 不应承担的职责 |
|---|---|---|
| 公开错误注册表 | `contracts/errors/common.yaml`、`<module>.yaml` | 不保存运行时错误事件 |
| Problem 基础结构 | `contracts/http/components/schemas/Problem.yaml` | 不复制完整错误目录 |
| 具体错误 schema | `Errors.generated.yaml` | 不手改 |
| 内部领域异常 | `modules/<module>/domain/errors.py` | 不依赖 HTTP 或客户端文案 |
| 用例异常 | `modules/<module>/application/errors.py`，按需 | 不替代领域不变量 |
| HTTP 映射 | `modules/<module>/presentation/http/error_mapping.py` | 不包含新的业务判定 |
| 全局 HTTP handler | `platform/http/exception_handlers.py` | 不随意 import 所有业务模块 |
| TS/Python 公共码定义 | 各自 `generated/` | 不手写第二份 enum |
| 客户端网络/解析错误 | SDK `runtime/` 或客户端 `shared/api/` | 不冒充服务端业务错误 |
| 特定提示与恢复操作 | 对应 feature/page | 不靠 detail 文案判断逻辑 |
| 错误事件与堆栈 | 受控日志、审计、Telemetry | 不作为错误码定义源 |

`kernel/errors.py` 只保留真正通用的异常协议，不能收集所有业务错误。

## 2. 命名与稳定性

本母版选择稳定字符串，例如 `AUTHN.REQUIRED`、`AUTHZ.DENIED`、`CATALOG.RESOURCE_LOCKED`。前缀表示职责，不编码文件路径、HTTP 数字或数据库细节。不要用 `ERROR_17`、`50001` 而没有命名语义与文档。

一个 code 表示一个稳定公共含义。同一含义不按 Vite/Next/小程序分别取名。已发布 code 不复用给新含义；改名是契约变更。技术堆栈变化不应迫使客户端改业务分支。

内部同一异常可因披露政策不同而映射到不同公开问题，例如未授权访问资源统一显示不存在。该选择属于已批准的接口披露规则，不是全局 handler 猜测。

## 3. 注册表格式

下面是团队自定义 YAML，不是 OpenAPI 原生文件格式。初始化时必须实现格式校验和生成器，并测试重复 code/type、非法状态码、冲突含义与失效引用。

```yaml
schema_version: 1
module: catalog
errors:
  - code: CATALOG.RESOURCE_LOCKED
    type: https://api.example.com/problems/catalog/resource-locked
    http_status: 409
    title: Resource is locked
    description: 已锁定资源不能执行当前修改操作。
    safe_detail: This resource cannot be modified while locked.
```

示例域名不能用于真实上线；使用项目控制的稳定 URI 命名空间。注册表不包含 traceback、SQL、内部路径、秘密、真实用户输入或可以绕过策略的诊断信息。

生成器把这份定义投影到 OpenAPI 错误 schema、TS/Python 定义与文档。不要再在 handler 中手写一份独立 `code → status → title` 字典。

## 4. HTTP 表示：RFC 9457

本方案采用 `application/problem+json`。RFC 9457 定义 `type`、`title`、`status`、`detail`、`instance` 等成员并允许扩展；`type` 标识问题类型。`code`、`trace_id` 是本项目扩展，不是 RFC 必须字段。[S12](SOURCES.md#s12)

```http
HTTP/1.1 409 Conflict
Content-Type: application/problem+json
```

```json
{
  "type": "https://api.example.com/problems/catalog/resource-locked",
  "title": "Resource is locked",
  "status": 409,
  "code": "CATALOG.RESOURCE_LOCKED",
  "detail": "This resource cannot be modified while locked.",
  "trace_id": "f27440e5d7284c879cf7b9b39e293c41"
}
```

本模板要求 type/code 固定一一对应，status 与实际 HTTP 状态一致；这是项目约束。trace_id 用于受控诊断关联，不授予日志读取权限，不含 PII。未知错误不能返回真实异常字符串。

`Problem.yaml` 定义基础字段与安全扩展规则；具体 code/type 配对由生成 schema 约束。避免基础 schema 错误地封死全部扩展、让具体错误无法组合。验证生成器对引用、组合和枚举的处理，而不只校验 YAML 语法。

## 5. 状态码与业务码的关系

| 示例类别 | 默认 HTTP 处理 | 注意 |
|---|---|---|
| 未认证或凭据无效 | 401 | 按认证方案保留需要的挑战头；不泄露验证细节 |
| 已认证但操作不允许 | 403 | 需隐藏存在性时遵循端点的 404 披露契约 |
| 资源不可见或不存在 | 404 | 不暗中区分到足以泄露跨租户信息 |
| 状态冲突，如锁定 | 409 | 不等于所有业务失败都用 409 |
| 约定的请求校验失败 | 本模板默认 422 | 解析层错误可为 400；接口需明确区分 |
| 频率限制 | 429 | 有界重试；按适用契约提供 Retry-After |
| 未预期内部异常 | 500 | 通用安全提示 + 受控日志 |
| 授权权威/必要依赖不可用 | 503，按已定契约 | 不伪装成用户无权限，不回退放行 |

表中是本模板的 API 约定示例，不要求给不适用的接口预建所有错误。避免把所有失败包在 HTTP 200，也不要把 2xx 空响应当作错误 JSON 解析。

## 6. Python 映射与组装

```text
domain 识别业务事实：ResourceLocked
  → application 中止当前用例
  → presentation 的模块映射选择 CATALOG.RESOURCE_LOCKED
  → 通用 handler 读取生成定义并序列化
```

每个模块通过 `wiring.py` 提供自己的映射，bootstrap 汇总注入全局 handler。这样 `platform` 不反向依赖业务模块。

FastAPI 支持自定义异常处理器，也允许覆盖请求校验异常处理；这提供了边界实现位置，不意味着所有异常都应暴露给客户端。[S13](SOURCES.md#s13)

实现必须区分：请求校验失败、响应模型错误、预期业务异常、未知异常、取消/断连、上游响应不合法。响应模型错误是服务器实现问题，不能作为“用户填错参数”返回。

基础设施将已识别且可安全解释的 DB 约束问题翻译为内部异常；其余进入通用未知异常路径。不要解析不稳定的数据库英文报错来确定公共 code，也不要在 public response 暴露表/列名。

## 7. 客户端失败协议

建议用带类别的内部结果区分以下事件：

```text
remote_problem：确实收到并通过校验的服务端 Problem
transport_failure：没有有效 HTTP 响应，如断网/超时
protocol_failure：拿到响应但不符合约定，如代理 HTML 页面
cancelled：调用方取消；不默认弹系统故障
```

`KnownErrorCode` 可以是生成 union；解析运行时必须接受并安全呈现未知公共 code。未知码不能使整个客户端崩溃，也不自动视作成功。已知 code 与 type/status 不匹配应视为协议异常并记录安全诊断。

Vite/Next 的网络异常、微信 `errno`、后端业务 `code` 是不同命名空间。适配器可以标准化内部类别，不可伪造“服务端返回了 CATALOG.X”。

## 8. 文案与恢复行为

默认由客户端翻译公开错误码。通用登录失效等放 shared 的小范围机制；特定功能的恢复动作放 feature/page。表单字段错误使用契约指定的安全字段标识，不能照搬内部模型路径。

未知错误显示通用提示和诊断 ID，不展示原始 response body。用户取消不用一律 toast。自动重试须同时满足安全重复条件、可恢复错误、次数和总期限，不能仅按 `retryable: true` 决定重复写入。

未知异常返回安全通用响应，诊断留在服务器，是 OWASP 的基础处理原则。[S18](SOURCES.md#s18) 本模板额外要求日志脱敏、体积限制和错误归属明确。

## 9. 必测清单

生成器：重复/冲突注册失败；删除错误清除派生文件；同输入同工具产物一致。

服务端：各已公开异常映射正确；响应与 Content-Type 一致；401 必要头未丢；未知异常无内部信息；拒绝不产生禁止的业务写入或消息；允许单独安全审计。

客户端：已知问题、未知 code、非法 JSON、非 JSON、缺字段、状态冲突、空 204、网络失败、取消；错误展示不依赖英文 detail。

跨端：同一 Problem 样例在浏览器、Next 服务端和微信适配器有一致语义；微信 success 回调收到 HTTP 错误时不走业务成功。

## 10. 不要做

不要把 Error Code 放数据库当字典权威；不要用 `common/errors.py` 收集全项目业务；不要前后端各写 enum；不要每层改写 code；不要返回堆栈；不要在 catch 后返回成功；不要用错误码替代审计事件模型。
