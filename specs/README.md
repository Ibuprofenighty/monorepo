# Specs

需求先明确（blueprint 10 §1-§3）。每个 spec 是一个 YAML，描述验收场景；
`scripts/quality/check_traceability.py` 校验：

- 每个 scenario 有唯一 `id`
- `tests:` 列出的目标真实存在
- 测试代码里的 `# spec: <ID>` 注释指向已知的 spec id

字段（最小集，blueprint 10 §3）：

```yaml
area: catalog            # 业务域
source: docs/blueprint/04-BACKEND-PYTHON.md  # 需求来源
scenarios:
  - id: CATALOG.DELETE.LOCKED_NO_EFFECT
    title: 锁定资源不可删除
    preconditions: ["存在 locked=true 的资源 res_1"]
    steps: ["DELETE /api/v1/resources/res_1"]
    expect:
      status: 409
      problem_code: CATALOG.RESOURCE_LOCKED
      state: "res_1 仍存在且仍锁定"
      no_side_effects: ["res_1 未被删除", "无其他资源变化"]
    tests:
      - apps/backend/tests/modules/catalog/unit/test_domain.py::test_locked_resource_is_not_deletable
      - apps/backend/tests/modules/catalog/api/test_http.py::test_delete_locked_is_conflict
    counterexample: remove-locked-invariant  # check_counterexamples.py 中的 mutation 名
```

`counterexample` 可选；有则表示该场景被定向反例 harness 覆盖。
