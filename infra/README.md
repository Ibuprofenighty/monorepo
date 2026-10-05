# infra/

程序如何运行（blueprint 09）。业务基础设施适配在后端 `infrastructure/`，
两者不是一套东西。

- `docker/` — 镜像。统一以仓库根为 build context（09 §3）。
- `compose/` — 一份基础拓扑 + 环境 overlay（09 §4）。
  - `compose.yaml`：postgres、redis、api、worker、web
  - `compose.dev.yaml`：源码挂载、reload、调试端口
  - `compose.test.yaml`：独立库与 volume，不碰开发/生产数据
- `nginx/` — 网关配置，** baked 进 web 镜像**（`web.Dockerfile` 的
  runtime-static 阶段）：静态 SPA + `/api` 代理到 `api:8000`。API 路径永不
  fallback 到 index.html；上游 Problem 的状态码与 Content-Type 不被吞掉（09 §6）。
  拓扑里只有一层 nginx——web 容器即边缘网关，没有独立的 nginx 服务。
  Next.js SSR（`WEB_OUTPUT=server`）时 web 容器跑 node 直服 3000，
  前端走 server-side `INTERNAL_API_URL` 调 API，不经过 nginx。
- `config/` — 环境变量示例。填好值的文件永不进 git。

`compose.yaml` 对 `POSTGRES_PASSWORD`、`JWT_SECRET` 使用 `${VAR:?}`：缺值即失败，不提供默认密码。
本地值放在仓库根 `.env`（由 `.env.example` 复制）；Compose 默认只在第一个 `-f` 文件所在目录找 `.env`，
所以开发命令显式传 `--env-file .env`（`make dev` 已包含）。部署与 CI 从环境变量 / secret manager 注入。

常用命令（仓库根）：

```bash
docker compose --env-file .env -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml config  # 检查合成配置
docker compose --env-file .env -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml up --build
docker build -f infra/docker/backend.Dockerfile .
```
