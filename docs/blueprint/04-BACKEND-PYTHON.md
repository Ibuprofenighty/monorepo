# 04 · Python 后端：模块化单体

版本：2.0｜日期：2026-10-02｜默认实现：FastAPI + SQLAlchemy/Alembic + PostgreSQL。

[返回总入口](../../README.md) · [错误](03-ERROR-CODES.md) · [权限](08-AUTH-SECURITY.md)

## 1. 目录

```text
apps/backend/
├── README.md
├── pyproject.toml
├── alembic.ini
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_catalog_resources.py
├── src/
│   └── project_backend/
│       ├── __init__.py
│       ├── entrypoints/
│       │   ├── http.py
│       │   ├── worker.py                     # [可选]
│       │   └── cli.py                        # [可选]
│       ├── bootstrap/
│       │   ├── app.py                        # create_app/生命周期
│       │   └── container.py                  # 组合根
│       ├── kernel/
│       │   ├── identity.py                   # Principal
│       │   ├── authorization.py              # Authorizer/Decision
│       │   └── errors.py                     # 最小公共异常协议
│       ├── platform/
│       │   ├── config/settings.py
│       │   ├── http/
│       │   │   ├── middleware.py
│       │   │   └── exception_handlers.py
│       │   ├── authn/verifier.py
│       │   ├── authz/client.py               # [选择远端权威时]
│       │   ├── db/
│       │   │   ├── base.py
│       │   │   └── session.py
│       │   ├── observability/
│       │   │   ├── logging.py
│       │   │   └── tracing.py
│       │   ├── cache/                        # [按需]
│       │   ├── storage/                      # [按需]
│       │   └── messaging/                    # [按需]
│       ├── generated/http/
│       │   ├── models.py
│       │   └── errors.py
│       └── modules/
│           └── catalog/
│               ├── __init__.py
│               ├── public.py
│               ├── wiring.py
│               ├── domain/
│               │   ├── resource.py
│               │   ├── value_objects.py
│               │   ├── rules.py
│               │   └── errors.py
│               ├── application/
│               │   ├── commands/delete_resource.py
│               │   ├── queries/get_resource.py
│               │   ├── access.py
│               │   ├── errors.py             # [按需]
│               │   └── ports/
│               │       ├── repository.py
│               │       └── unit_of_work.py
│               ├── infrastructure/
│               │   ├── persistence/
│               │   │   ├── models.py
│               │   │   ├── repository.py
│               │   │   └── unit_of_work.py
│               │   ├── integrations/         # [按需]
│               │   └── cache/                # [按需]
│               └── presentation/
│                   ├── http/
│                   │   ├── router.py
│                   │   ├── mapping.py
│                   │   └── error_mapping.py
│                   └── consumers/            # [按需]
└── tests/
    ├── conftest.py
    ├── modules/catalog/
    │   ├── unit/
    │   ├── integration/
    │   └── api/
    ├── integration/                           # 后端模块间协作
    ├── contract/
    ├── security/
    ├── migrations/
    └── architecture/
```

为可读性省略重复 `__init__.py`；不要真的把缺失包声明归咎于布局。采用 src layout，安装并测试实际包；pytest 官方提供这类布局与 importlib 导入模式建议。[S15](SOURCES.md#s15)

## 2. 源码依赖

```text
presentation → application → domain
infrastructure → application.ports + domain
platform → kernel + 技术库
bootstrap → wiring + platform + 各具体实现
```

运行时 application 可以通过 repository 端口访问基础设施；源码不应直接导入 SQLAlchemy repository。这是依赖倒置，不是“application 什么外部能力都不能调用”。相关模式说明见作者原始资料 [S16](SOURCES.md#s16)。

domain 不知道 HTTP、数据库、环境变量或权限服务地址。application 组织事务、授权和业务操作；infrastructure 实现端口；presentation 做协议转换。简单功能不为层次整齐创建 pass-through 类。

## 3. 公开接口与模块隔离

跨模块通过 `public.py` 暴露用例/查询的稳定输入输出。调用方不能导入对方 ORM、repository 或内部 domain。`public.py` 不泄露内部 SQLAlchemy Session、ORM 对象或让调用方随意写表的接口。

在 `docs/architecture/module-boundaries.md` 记录允许依赖和表归属。跨模块依赖无环；若需要可替换的对方能力，调用方定义端口，适配器对接对方公开 API。

例外只包括明确的组合根、迁移 metadata 汇总、本模块自身测试等。技术检查可用 Import Linter，但配置与违规样例才使其成为有效门禁。[S25](SOURCES.md#s25)

## 4. 用例的职责和次序

一个受保护写用例通常需要：验证可信主体 → 加载最小资源事实 → 调用授权权威 → 检查业务状态 → 执行受控写入 → 提交事务 → 返回用例结果。

这不是对所有用例规定一次固定 I/O 顺序。对资源存在性披露、并发状态变化、远程授权耗时，应选择一致性策略；不要在等待长时间远程调用时无条件持有数据库锁。

HTTP router、worker、CLI 都进入同一受保护用例。系统任务必须有明确服务主体、授权范围或经过批准的特权用例，不能以“内部调用”为由自动跳过权限。

## 5. 事务、并发和幂等

application 定义事务边界，repository 不随意单独 commit。Session 按请求/工作单元使用，不作为跨请求共享可变全局。失败后回滚，退出释放资源。

关键唯一性和数据完整性落实数据库约束；并发更新可选择版本条件更新或合适的锁机制。选择依赖具体不变量，不将 Redis 分布式锁视为所有数据库竞争的万能保证。

幂等需要明确 key 作用域、请求指纹、结果状态、重复并发、有效期与崩溃恢复。仅在请求头中加一个 key 不等于幂等；仅重复操作成功也不能证明副作用只有一次。

需要数据库变更与事件可靠关联时，评估事务 outbox 等方案并写清消费者去重及顺序语义。未启用消息系统不提前建 outbox；不能对未知外部系统承诺端到端 exactly-once。

## 6. DB 模型与迁移

ORM 放所属模块；全库迁移历史放 `apps/backend/migrations`。数据库实例、网络、用户的基础设施归 infra，业务表的 DDL 演进不在 `infra/sql` 再维护一套。

Alembic 自动迁移只生成候选变更，需要人工 review；官方明确其自动识别有局限。[S17](SOURCES.md#s17) 对 rename、数据回填、非空新增、大表锁定、索引和约束变动安排专门检查。

最低测试：空库升级到 head、受支持旧版本升级、数据回填正确、约束生效、升级后应用能读写。回滚不等于无条件运行 downgrade；不可逆数据变更必须有备份恢复或前向修复方案。

发布迁移只有一个受控执行者，应用副本不竞相在启动时迁移。已发布 migration 不随意改写或删除。

## 7. 配置与技术底座

`settings.py` 负责解析和校验；bootstrap 注入，业务模块不遍地读取环境变量。数据库、Redis、对象存储 client 留在 platform；每个业务模块的 key、缓存失效和文件含义留在该模块。

不要同时写同步和异步两套同义数据访问。初始化选择一套适合运行环境的 I/O 方案；异步接口内部不能被未处理的阻塞 I/O 占住。需要同步集成时使用经过验证的隔离/调度方式。

日志、指标和 trace 关联到请求、用例、任务；不要把高基数 PII 或全部 prompt/request body 当作默认标签和日志。

## 8. 身份接入的业务模块

小程序登录的用户关联、账户创建、绑定与业务会话属于 `modules/identity/` 等明确身份模块。微信 code2Session 适配属于该模块的 infrastructure；路由属于 presentation。

`platform/authn/verifier.py` 验证后续请求凭据；不要将开户/账户绑定业务塞入通用 verifier。涉及 Keycloak 的项目明确身份映射与凭据颁发的唯一归属，不让小程序接入生成第二个独立用户系统。

## 9. 后台任务

需要 worker 时，`entrypoints/worker.py` 只负责进程与消费者注册；消息消费者转换输入后调用现有 use case。任务 timeout、重试次数、重试预算、幂等与 poison message 处理必须显式。

不可将 JWT、session_key 或原始请求秘密无期限复制进任务消息。任务在何时授权、是否重验、以谁的身份执行，要由安全设计规定。

## 10. 最低验收

模块边界检查、纯规则单元测试、真实 PostgreSQL 约束测试、实际 API 契约测试、所有入口权限拒绝测试、迁移测试、进程启动关闭与健康检查都要有真实结果。

数据库替身适合单元测试，不可用 SQLite 单测代替 PostgreSQL 的事务/锁/约束证据。业务规则失败时，断言状态和禁止副作用，而不只断言抛出异常。
