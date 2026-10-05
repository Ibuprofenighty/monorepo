# Runbook · 故障处理

## 1. 定位

```bash
make doctor  # 工具、端口、依赖、生成物漂移（不输出 secret）
docker compose -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml logs --tail=200 api
```

## 2. 按 symptom 查

| 现象 | 先查 |
|---|---|
| 5xx + `trace_id` | api 日志按 trace_id 过滤；problem 的 `code` 定位模块 |
| 401/403 突增 | verifier 配置（issuer/audience/secret 来源），非代码 |
| 429 | 限流配置与上游行为，检查是否为误伤 |
| 迁移失败 | `migrate.py --sql` 输出 + 备份状态；不要反复重试不可逆迁移 |
| 小程序白屏 | `dist/` 是否由 `make mp-build` 最新构建；`__API_BASE_URL__` 注入值 |

## 3. 记录

每次故障处理完，在 `docs/audits/` 留一条：时间、现象、`trace_id`、根因、修复、预防。
没有记录的故障等于没处理完。
