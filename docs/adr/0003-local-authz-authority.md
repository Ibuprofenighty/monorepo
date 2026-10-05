# 0003 · 后端本地授权权威

状态：已接受
日期：2026-10-03
决策人：母版

## 背景

多客户端需要统一的权限裁决，且"前端按钮隐藏"不能作为安全边界。

## 决策

- 授权权威唯一在后端：`kernel/authorization` + 各模块 `application/access.py` 的 `ensure_can`。
- 写用例顺序固定：authorize → 校验 → 写 → 提交。deny 发生在任何持久化之前
 （由 `test_deny_before_write_ordering` 及反例 harness 守护）。
- 前端按 code 做 UX 分支（如 403 提示），不做最终安全裁决。

## 备选方案

- 前端路由守卫作为安全边界：可被绕过，否决。

## 后果

- 新增写操作必须先 `ensure_can`，顺序由架构测试 + 反例检查守护。
- 换身份系统（Keycloak/微信）只换 verifier，use case 不动。

## 关联

- 契约/错误码/权限/数据影响：权限（全部写操作）
- 相关 spec：CATALOG.WRITE.DENY_BEFORE_WRITE
