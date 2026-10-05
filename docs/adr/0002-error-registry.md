# 0002 · 错误码注册表 + RFC 9457 problem

状态：已接受
日期：2026-10-03
决策人：母版

## 背景

多客户端（Web/小程序/Flutter）需要一致的错误语义，且错误码是公开 API 的一部分，
不能随实现随意增删。

## 决策

- `contracts/errors/*.yaml` 为错误码唯一手工来源（含 code、type、http_status、title）。
- HTTP 错误统一用 RFC 9457 `application/problem+json`，扩展 `code` + `trace_id`。
- 各语言生成常量：TS `ErrorCodes`、Python `ErrorCode`、Dart `ErrorCodes`。
- 客户端只按 code 分支，永不按文案分支；未知 code 向后兼容（按 INTERNAL 文案兜底）。

## 备选方案

- 各端硬编码错误码：增删无审计，否决。

## 后果

- 新增公开错误码 = 改 registry + `make generate` + 更新客户端文案映射。
- 未知 code 必须可容忍（已由 SDK 单测覆盖）。

## 关联

- 契约/错误码/权限/数据影响：错误码（全部）
- 相关 spec：CATALOG.DELETE.LOCKED_NO_EFFECT 等
