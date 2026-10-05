# 12 · 可复制模板与交付清单

版本：2.0｜日期：2026-10-02｜本文件提供实例化模板，不是第二份规则权威。

[返回总入口](../../README.md) · [项目选型](00-PROJECT-PROFILE.md) · [测试](10-TESTING-HARNESS.md) · [流程](11-FEATURE-WORKFLOW.md)

## 1. 使用说明

按需要把对应模板内容复制到标注的目标文件，替换项目事实、示例业务名和待决项。复制出的文件是该项目的事实记录，规则仍引用各分册。

下面出现 `待确定`、`example` 表示模板尚未实例化，不能用于宣称验收已完成。YAML 结构是团队自定义格式；需在 `specs/schema/` 建立校验并实现相应工具。

## 2. Project Profile 模板

目标：`docs/architecture/project-profile.md`。

```markdown
# 项目配置与架构选择

状态：待批准
规范版本：Blueprint 2.0
项目名称：待填写
Python 包名：待填写
TypeScript scope：待填写

## 产品与客户端
产品目标：待填写
启用客户端：web-vite / web-next / wechat-native 中的实际选择
实际应用目录：待填写
Web 渲染/小程序构建方式：待填写
明确不在本阶段实现的内容：待填写

## 业务与数据
初始模块及负责人：待填写
数据归属与隔离方式：待填写
数据库与迁移方式：待填写
当前旧版本/存量数据：待填写

## 身份、权限和配置
身份权威与登录方式：待填写
授权权威（唯一）：待填写
会话、撤销和刷新：待填写
公共配置来源：待填写
secret 注入方式：待填写；不写实际 secret

## 工程与部署
Node/Python/pnpm/uv/框架/生成器版本来源：待填写
开发操作系统与平台工具执行位置：待填写
实际部署拓扑与代理/TLS 归属：待填写
SLO、容量、备份恢复与保留需求：待填写

## 门禁与未决项
合并强制 gate：待填写
发布强制 gate：待填写
未决项、影响、责任人、阻塞范围：待填写
已批准 ADR：待填写
```

## 3. Feature Spec 模板（有权删除资源示例）

目标：`specs/features/catalog/delete-resource.yaml`。示例采用资源可删除的业务假设；真实项目需替换，不能默认所有业务都物理删除。

```yaml
schema_version: 1
kind: feature_spec
id: CATALOG.DELETE_RESOURCE
status: example
owner: unassigned
summary: 有权主体可以删除未锁定且在授权范围内的资源。

contract:
  source: contracts/http/openapi.yaml
  operation_id: deleteResource
  method: DELETE
  path: /api/resources/{resource_id}
  success_response: 由源契约确定。
  public_errors:
    - AUTHN.REQUIRED
    - AUTHZ.DENIED
    - CATALOG.RESOURCE_LOCKED
  disclosure_policy: 需在实例化时决定无权限与不存在的披露规则。

authorization:
  action: resource.delete
  authority: required_project_decision
  principal_source: verified_identity_context
  resource_facts_source: trusted_backend_state
  failure_mode: fail_closed_with_controlled_error

invariants:
  - id: CATALOG.DELETE.DENY_NO_EFFECT
    statement: 拒绝时不得写入被禁止的资源状态、发布成功消息或执行外部删除；允许独立安全审计。
  - id: CATALOG.DELETE.LOCKED_NO_EFFECT
    statement: 锁定资源不能被当前操作删除。

scenarios:
  - id: CATALOG.DELETE.ALLOW
    category: positive
    given:
      authenticated: true
      authorization_decision: allow
      resource_locked: false
    when: 请求删除资源。
    then:
      - 返回契约规定成功响应。
      - 目标资源按已批准的删除语义变化。
      - 无关资源保持不变。

  - id: CATALOG.DELETE.UNAUTHENTICATED
    category: negative
    given:
      authenticated: false
    when: 请求删除资源。
    then:
      - 返回契约认证错误与所需响应头。
      - 未产生禁止的资源写入或成功消息。
    invariant_refs:
      - CATALOG.DELETE.DENY_NO_EFFECT

  - id: CATALOG.DELETE.DENY
    category: negative
    given:
      authenticated: true
      authorization_decision: deny
    when: 请求删除资源。
    then:
      - 返回符合披露策略的拒绝响应。
      - 目标资源状态不变。
      - 不发布成功消息，不触发外部删除。
    invariant_refs:
      - CATALOG.DELETE.DENY_NO_EFFECT

  - id: CATALOG.DELETE.LOCKED
    category: negative
    given:
      authenticated: true
      authorization_decision: allow
      resource_locked: true
    when: 请求删除资源。
    then:
      - 返回 CATALOG.RESOURCE_LOCKED。
      - 目标仍锁定且未删除。
    invariant_refs:
      - CATALOG.DELETE.LOCKED_NO_EFFECT

risk_dimensions:
  tenant_isolation: required_when_multitenant
  missing_resource_disclosure: must_decide
  concurrent_resource_or_policy_change: must_decide
  duplicate_and_idempotency: must_decide
  partial_failure: must_decide
  full_fail: must_decide_if_retry_or_dependency_failure_applies
  fail_then_pass: must_decide_if_retry_applies
  cancellation: must_decide_for_applicable_client_or_task

oracle:
  source: 审查过的行为规格、权限规则与源契约；不是当前实现输出。
  observations:
    - 用例或实际 HTTP 响应。
    - 隔离测试数据库中的目标与无关状态。
    - 消息或外部操作的真实边界证据。

counterexamples:
  - id: CATALOG.DELETE.MUTATION.SKIP_AUTHZ
    fault: 在隔离测试变体中跳过授权执行。
    expected_detecting_scenarios:
      - CATALOG.DELETE.DENY
  - id: CATALOG.DELETE.MUTATION.SKIP_LOCK_CHECK
    fault: 在隔离测试变体中移除锁定规则。
    expected_detecting_scenarios:
      - CATALOG.DELETE.LOCKED
  - id: CATALOG.DELETE.MUTATION.WRITE_BEFORE_DENY
    fault: 在隔离测试变体中先写业务状态再拒绝。
    expected_detecting_scenarios:
      - CATALOG.DELETE.DENY

completion:
  - 所有必需决策与风险维度已落实，或有批准的不适用理由。
  - 测试引用稳定场景 ID 且真实检验状态与副作用。
  - 指定关键反例因正确断言失败而被检出。
  - 契约、错误、生成物、权限、数据与客户端一致。
  - 真实执行证据和未验证事项已记录。
```

如果选择隐藏存在性，需同步修改 `public_errors` 和具体场景，不应原样保留上面所有错误。示例不授权 Agent 自动增加当前产品没有的租户、重试或消息能力。

## 4. 模块边界记录模板

目标：`docs/architecture/module-boundaries.md`。

```markdown
# 模块边界与数据所有权

## 模块清单
| 模块 | 业务职责 | 公开入口 | 所有表/对象 | 负责人 |
|---|---|---|---|---|
| 示例，需替换 | 待填写 | public.py / HTTP 契约 | 待填写 | 待填写 |

## 允许依赖
| 调用模块 | 被调用模块 | 公开能力 | 业务理由 |
|---|---|---|---|
| 待填写 | 待填写 | 待填写 | 待填写 |

## 严格例外
| 例外入口 | 允许访问 | 范围与理由 | 检查规则 |
|---|---|---|---|
| migrations/env.py | ORM metadata | 只汇总迁移 | 待填写 |
| bootstrap | wiring | 只组装依赖 | 待填写 |

## 禁止行为与验证
跨模块私有导入：必须被检查拒绝。
表归属违规：验证方式待填写。
依赖循环：必须被检查拒绝。
相关 ADR：待填写。
```

## 5. 实施计划模板

目标：`docs/plans/<work-item>.md`。

```markdown
# 工作项实施计划

状态：计划中 / 执行中 / 已完成 / 已撤销
需求与 spec ID：待填写
起始 commit：待填写
负责人：待填写

## 目标与非目标
目标：待填写
保留能力：待填写
明确不做：待填写

## 影响分析
契约与错误：待填写
身份/授权：待填写
数据与历史迁移：待填写
客户端与发布兼容：待填写
运行环境与成本：待填写

## 按顺序执行
| 步骤 | 文件/模块 | 修改或删除 | 依赖 | 可验证完成标准 |
|---|---|---|---|---|
| 1 | 待填写 | 待填写 | 待填写 | 待填写 |

## 测试与检出力
正向/反向/边界：待填写
full fail / fail then pass：适用性与理由
真实集成/E2E：待填写
关键反例：待填写

## 风险与恢复
阻塞：待填写
回滚/前向修复：待填写
存量数据保护：待填写

## 最终结果
实际执行与证据：待填写；未执行不得填 PASS。
退出当前计划入口的方式：待填写。
```

## 6. ADR 模板

目标：`docs/adr/<编号>-<决策主题>.md`。

```markdown
# ADR：决策标题

状态：Proposed / Accepted / Superseded / Rejected
日期：待填写
责任人：待填写
关联需求与受影响模块：待填写

## 问题与约束
待填写。区分事实、假设与未决项。

## 选择
唯一采用的方案：待填写。

## 被放弃的方案
选择理由和代价：待填写，不保留未使用生产实现。

## 影响
接口、错误、权限、数据、测试、部署、成本：待填写。

## 迁移与验收
迁移消费者、数据和配置的方法：待填写。
如何证明旧路径不再有效：待填写。
无法同步更新客户端时的支持范围：待填写。

## 替代关系
替代的旧 ADR：待填写或无。
当前权威文档更新位置：待填写。
```

## 7. 验收证据模板

目标：CI 制品中的报告；需要历史审计时保存脱敏摘要到 `docs/audits/`。

```markdown
# 验收记录

commit：待填写
制品/版本/digest：待填写
执行时间与时区：待填写
环境与平台版本：待填写
范围与 spec ID：待填写

| 检查 | 状态 | 实际命令/步骤 | 退出码/观察 | 证据位置 |
|---|---|---|---|---|
| 待填写 | NOT_RUN | 待填写 | 尚未执行 | 无 |

## 定向反例
基线：待填写
受控故障：待填写
检测测试：待填写
失败是否来自目标断言：待填写
临时变体已隔离和销毁：待填写

## 限制与风险
FAIL：待填写
BLOCKED：待填写
NOT_RUN：待填写
N/A 及理由：待填写
残余风险和批准人：待填写

## 结论
仅对实际范围下结论；不把静态检查称为运行验收。
```

## 8. 模块删除清单

执行前确认业务停用授权、消费者、数据保留和当前部署。清理路由、任务注册、权限 action、公开契约、生成物、UI 导航、模块依赖、配置和文档。旧 migration 不随意改写；用前向迁移处理表与数据。

最后用仓库搜索和运行测试证明旧生产路径不可达。保留经要求的审计或历史证据，不把“没有旧运行路径”错误理解为“删掉所有历史”。

## 9. 完成报告模板

```markdown
# 本次交付

实现范围：待填写。
主要变更与删除：待填写。
契约/错误/权限/数据变化：待填写。
实际执行：命令、结果与证据。
未执行或阻塞：待填写。
残余风险：待填写。
制品和运行方式：只列已存在并验证的入口。
文档同步：当前权威位置与退出的旧指导。
```

不要以“所有测试应该通过”“已达到生产级”“理论上没有问题”代替执行结果。
