# contracts/ — 接口契约唯一手工来源（blueprint 02）

```text
contracts/
├── README.md                 # 本文件
├── errors/
│   ├── common.yaml           # HAND-WRITTEN: 公开错误注册表（通用）
│   └── catalog.yaml          # HAND-WRITTEN: 公开错误注册表（catalog 域）
├── http/
│   ├── openapi.yaml          # HAND-WRITTEN: HTTP 源契约（单文件，自包含）
│   └── examples/
│       └── resource.json     # 有效样例
└── events/                   # [可选] AsyncAPI，按需
```

## 纪律

1. **手写源只有三处**：`errors/*.yaml`、`http/openapi.yaml`、`http/examples/*`。
   其他一切（TS/Python/Dart 类型、错误枚举、文档）都是生成的。
2. 生成产物提交 Git（便于 review），但**永不手改** — `make check-generated`
   会在干净临时目录重新生成并做全文件集合 diff，漂移即失败。
3. 错误码稳定字符串（`AUTHN.REQUIRED`），前缀表职责；已发布 code 永不复用。
4. HTTP 表示统一 `application/problem+json`（RFC 9457）+ `code` + `trace_id` 扩展。
5. 破坏性变更 → 新错误码 / 新 API 版本，不悄悄改含义。

## 生成链路

```text
contracts/errors/*.yaml
  → scripts/contracts/generate.py
  → packages/ts/api-client/src/generated/errors.ts
  → apps/backend/src/project_backend/generated/http/errors.py
  → packages/dart/api_client/lib/src/generated/errors.dart

contracts/http/openapi.yaml
  → openapi-typescript        → packages/ts/api-client/src/generated/schema.ts
  → datamodel-code-generator  → apps/backend/src/project_backend/generated/http/models.py
  → generate.py 内置 Dart 生成 → packages/dart/api_client/lib/src/generated/models.dart
```

生成器版本锁定：

| 工具 | 锁定位置 | 调用方式 |
|---|---|---|
| openapi-typescript | 根 `package.json` devDependencies + `pnpm-lock.yaml` | `pnpm exec openapi-typescript` |
| datamodel-code-generator | `scripts/contracts/generate.py` 的 `CODEGEN_VERSIONS` | `uvx --from datamodel-code-generator==<ver>` |
| Dart 模型 / 三端错误表 | `generate.py` 自身 | 无外部工具 |

先 `pnpm install`（装 openapi-typescript），再 `make generate`，最后 `make check-generated` 确认干净。
