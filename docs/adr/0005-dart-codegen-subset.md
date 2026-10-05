# 0005 · Dart 代码生成策略：自研子集 + 明确边界

状态：已接受
日期：2026-10-03
决策人：Mengshi（用户确认）

## 背景

三线 codegen 的工具选型不对称：

| 语言 | 工具 | OpenAPI 兼容性 |
|---|---|---|
| TypeScript | `openapi-typescript` 7.13.0 | 完整 |
| Python | `datamodel-code-generator` 0.83.0 | 完整 |
| Dart | 自研 `render_models`（`scripts/contracts/dart_subset.py`） | **子集** |

Dart 不用 OpenAPI Generator：其输出（built_value / json_serializable + build_runner + 自带 client）与本模板「transport-neutral 手写 client + 生成 model」冲突，并且引入 Java 工具链。

OpenAPI 3.1 的 Schema Object 是 JSON Schema 2020-12。`format` 是注解，不蕴含类型。`nullable` 不是 3.1 关键字。

## 决策

1. Dart 走自研生成器。遇到子集外的构造，生成器失败，不生成 `Object?` 之类的占位类型。
2. 某个项目的契约若超出子集，由该项目替换生成器或手写 model。模板不承诺完整 OpenAPI。

### 支持

- `type: object` + `properties` + `required`
- `additionalProperties: false` 与 `properties` 一起：闭合对象。Dart 模型不拒绝多余 JSON 键
- `string` / `integer` / `number` / `boolean`
- `string` + `format: date-time` → `DateTime`。`format` 必须配 `type: string`
- `string` + `enum`，每个值都是 Dart 标识符且不是保留字 → `enum {Schema}{Field}`，`fromJson` 用 `values.byName`，`toJson` 用 `.name`
- `array` + `items`（含 `$ref`）
- 属性上只有 `additionalProperties: <schema>`、没有 `properties` → `Map<String, V>`
- `$ref`
- 可选字段 → `?`
- 不改变 Dart 类型的约束：`minLength`、`maxLength`、`pattern`、`minimum`、`maximum`、`exclusiveMinimum`、`exclusiveMaximum`、`multipleOf`、`minItems`、`maxItems`、`uniqueItems`、`minProperties`、`maxProperties`。生成代码不复查这些约束
- 注解：`title`、`description`、`default`、`example`、`examples`、`deprecated`、`readOnly`、`writeOnly`、`xml`、`externalDocs`

`Problem` 不进入 Dart 生成，由 `problem.dart` 手写解析。

### 遇到即失败

- `oneOf` / `anyOf` / `allOf`、`not`、`if`/`then`/`else`、`discriminator`
- `additionalProperties: true`
- `properties` 与 `additionalProperties` schema 同时存在
- 具名 schema 本身是 map（没有 `properties`）
- 内联 object（用 `$ref`）
- `format` 除 `date-time` 以外
- `type` 数组（含 `["string", "null"]`）
- `nullable`
- 非字符串 enum，或值不是合法 Dart 标识符
- 上表以外、会改变形态的关键字

## 备选方案

- 换 OpenAPI Generator：架构冲突，并且多一套 Java 工具链。否决。
- 把自研生成器做成完整 OpenAPI：没有上界。否决。

## 后果

- 写契约时先查本表。
- `make check-generated` 对 `models.dart` 做 drift 检查。子集规则由 `apps/backend/tests/scaffold/test_dart_subset.py` 覆盖。

## 关联

- 契约/错误码/权限/数据影响：契约（Dart 侧表达能力边界）
- 相关 spec：—
