# 0001 · 手写 OpenAPI 为唯一契约源

状态：已接受
日期：2026-10-03
决策人：母版

## 背景

前后端需要一份双方都信任的接口契约。框架自动生成的 OpenAPI 随实现漂移，
不能作为跨团队协作的权威。

## 决策

`contracts/http/openapi.yaml` 手写，为唯一权威源。FastAPI 直接 serve 该文件，
不以 FastAPI 自动生成的 OpenAPI 为准。TS/Python/Dart 类型全部由生成器产出，
`generated/` 目录永不手改。

## 备选方案

- FastAPI 自动生成 OpenAPI：实现漂移时契约跟着错，否决。
- GraphQL/tRPC：与"手写 OpenAPI + 多客户端 SDK"目标冲突，否决。

## 后果

- 改接口 = 改 openapi.yaml + `make generate` + 提交生成物。
- `make check-generated` 在 CI 强制无漂移。

## 关联

- 契约/错误码/权限/数据影响：契约（全部）
- 相关 spec：—
