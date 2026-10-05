# Generator（scaffold）

母版的两个职责之一：按选型表生成新项目（另一个是持有 canonical 代码）。

## 输入

`project-answers.example.yaml`（根目录）+ `examples/` 里的两个 few-shot 示例。

## 前置工具

| 工具 | 何时需要 | 用途 |
|---|---|---|
| uv | 总是 | 运行生成器（锁定的后端环境提供 pyyaml）与 `uvx` 生成 Python DTO |
| pnpm ≥ 9 | 总是 | 为新项目的 JS workspace 重新解析 `pnpm-lock.yaml`，提供 openapi-typescript |
| Flutter SDK（stable） | 选了 `mobile-flutter` | `flutter create` 生成 `android/`、`ios/` 平台工程 |
| git | `git_init: true` | 初始化仓库并提交首个 commit |

## 运行

```bash
./create-project.sh --answers my-answers.yaml [--output-dir DIR]
```

Windows（无 POSIX shell）：

```powershell
uv run --project apps/backend --frozen --extra dev python scripts/scaffold/create_project.py --answers my-answers.yaml
```

## 行为

1. 解析 + 校验：🔴 门禁项缺一不可，命名格式强制；选了 `mobile-flutter` 时
   `dart_package` 与 `mobile_org`（反向域名，如 `com.example`）必填；所需工具不在 PATH 直接失败。
2. 目标 `../<project_name>`：必须不存在、必须在母版之外；任何失败都删除半成品。
3. 按客户端勾选复制：
   - 全量：`apps/backend`、`contracts/`、`scripts/`（除 scaffold）、`tooling/`、
     `infra/`、`tests/e2e/`、`specs/`、`docs/{architecture,adr,development,operations,audits}/`
   - `packages/ts/api-client`：任选 TS 客户端才复制
   - `packages/dart/api_client`：选 mobile-flutter 才复制（库包不带 `pubspec.lock`）
   - 不复制：`docs/blueprint/`、`examples/`、scaffold 自身、`create-project.sh`、构建产物与缓存
4. 重命名：
   - Python：`project_backend` → 答案包名（目录、全文、pyproject、uv.lock、Dockerfile、CI 的 `--package`）
   - TS：`@project/` → `@<scope>/`（package.json + 导入）
   - Dart：库包名（依赖键与 pubspec `name` 一致）、`package:` 前缀、mobile app 名 `<project>_mobile`
   - compose project、pnpm workspace（按勾选裁剪）、problem 命名空间
5. CI 按勾选裁剪：未选客户端的构建步骤与 dart job 移除。
6. 选了 `mobile-flutter`：在 `apps/mobile` 运行
   `flutter create --org <mobile_org> --project-name <project>_mobile --platforms=android,ios --no-pub .`，
   只保留新生成的 `android/`、`ios/`、`.metadata`、`.gitignore`；母版的 `lib/`、`test/`、
   `pubspec.yaml`、`analysis_options.yaml` 保持原样，flutter 附带的示例文件删除。
7. `pnpm install --no-frozen-lockfile`：按裁剪后的 workspace 重新解析锁文件（新项目随后用 frozen lockfile）。
8. 在新项目内重新运行契约生成（命名变化会改变生成物）。
9. 对改名后的 Python 源码运行新项目自己的 ruff（fix + format + check），确保生成即通过 `make lint`。
10. 生成 `docs/architecture/project-profile.md`（实例化）+ 项目 README；
    `docs/audits/validation-evidence.md` 只保留说明与记录模板，不带母版的验收记录。
11. 按答案 git init（默认 true）。

## 验证

两个 few-shot 示例必须真实生成，并在生成结果里通过门禁冒烟；记录见 `docs/audits/validation-evidence.md`。
