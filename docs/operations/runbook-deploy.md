# Runbook · 发布

（blueprint 09 §9）

## 顺序

1. 冻结源与契约：`make check-generated` 干净
2. 从锁构建：`make build`
3. 质量门禁：`make verify`
4. 发布门禁：`make verify-release`
5. 测试环境真实运行 + smoke（`bash tests/e2e/run.sh`）
6. 审查数据迁移：`uv run --project apps/backend --frozen --extra dev python scripts/ops/migrate.py --env staging --sql` 先看 SQL
7. 单执行者迁移：`make migrate ENV=production`（需键入确认）
8. 部署 → 健康检查 → 关键业务 smoke → 观察 → 完成记录（`docs/audits/`）

## 运行配置

- `APP_ENV=staging|production`：`JWT_SECRET` 必须由 secret manager 注入且 ≥ 32 字节，
  缺失、过短或等于开发密钥时 api 与 worker 拒绝启动。
- 迁移在部署前由单执行者完成；api 容器启动不自动迁移。
- worker 必须随 api 一起部署：它每小时整点执行 `catalog_maintenance`，清理超过 24 小时的
  幂等记录（`catalog_idempotency_keys`）。

## 回滚

- 应用版本回滚 ≠ 数据回滚。迁移可能不可逆，回滚前确认备份与恢复演练状态。
- 小程序发版与后端可能不同步：部署窗口内保持旧错误码兼容，
  不为版本滞后保留整套旧业务实现。

## 禁止

- 不 `--env` 就迁移（脚本会拒绝）
- 在生产环境跑 seed
- 把 `.env` 或填好值的 `*.env` 提交进 git
