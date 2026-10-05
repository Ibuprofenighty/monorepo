# 项目配置与架构选择

状态：已实例化（由生成器从项目选型表生成，见 README）
规范版本：Blueprint 2.0
项目名称：{{project_name}}
Python 包名：{{python_package}}
TypeScript scope：{{ts_scope}}
Dart 包名：{{dart_package}}
移动端组织标识（Android applicationId / iOS bundle id 前缀）：{{mobile_org}}

## 产品与客户端

产品目标：{{product_goal}}
启用客户端：{{clients}}（web-vite / web-next / wechat-native / mobile-flutter 中的实际选择）
实际应用目录：{{app_dirs}}
Web 渲染/小程序构建方式：{{rendering}}
明确不在本阶段实现的内容：{{out_of_scope}}

## 业务与数据

初始模块及负责人：{{modules}}
数据归属与隔离方式：{{data_ownership}}
数据库与迁移方式：PostgreSQL + Alembic（固定，见 README 选型表）
当前旧版本/存量数据：{{legacy_data}}

## 身份、权限和配置

身份权威与登录方式：{{identity}}
授权权威（唯一）：后端本地授权（local authority），前端不做最终裁决
会话、撤销和刷新：{{session}}
公共配置来源：应用 platform/config（后端）/ shared/config（客户端）
secret 注入方式：{{secrets}}；不写实际 secret

## 工程与部署

Node/Python/pnpm/uv/框架/生成器版本来源：`.node-version` / `.python-version` / `pnpm-lock.yaml` / `uv.lock` / `apps/mobile/pubspec.lock`；openapi-typescript 在根 `package.json`，datamodel-code-generator 在 `scripts/contracts/generate.py#CODEGEN_VERSIONS`
开发操作系统与平台工具执行位置：{{dev_env}}
实际部署拓扑与代理/TLS 归属：{{topology}}
SLO、容量、备份恢复与保留需求：{{slo}}

## 门禁与未决项

合并强制 gate：`make verify`（check-generated、lint、typecheck、architecture、specs、counterexamples、docs、全部测试层）
发布强制 gate：`make verify-release`（verify + 镜像构建 + compose 配置检查）
未决项、影响、责任人、阻塞范围：{{open_items}}

---
`{{...}}` 由 `create-project.sh` 从项目选型表填充。填充后删除本行及所有未填项的 `{{}}` 标记，
不保留"待填写"占位。
