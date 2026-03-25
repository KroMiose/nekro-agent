# AI 开发指引入口

请先阅读并遵循以下规则文档，再开始修改代码：

- `.cursor/rules/global.mdc`
- `.cursor/rules/backend-rules.mdc`
- `.cursor/rules/frontend-rules.mdc`

如涉及插件或前端视觉规范，请额外阅读：

- `.cursor/rules/plugin-rules.mdc`
- `.cursor/rules/frontend-theme-guidelines.mdc`

## 通用原则

- 永远使用**中文**回答
- 除非必要，否则尽可能使用 Tool 而非终端命令（grep/find/etc.）来查阅代码

---

## 标准命令（必须使用，禁止使用 npm/npx/ruff/tsc 等原始命令）

> 所有命令在项目根目录 `/home/miose/Projects/nekro-agent` 下执行。

### 后端（Python）— 使用 `poe`

| 命令                     | 说明                                   |
| ------------------------ | -------------------------------------- |
| `poe lint`               | Ruff 代码检查（只检查，不修改）        |
| `poe lint-fix`           | Ruff 代码检查并自动修复                |
| `poe format`             | Ruff 代码格式化                        |
| `poe typecheck`          | basedpyright 类型检查                  |
| `poe check`              | 同时运行 lint + typecheck              |
| `poe dev`                | 启动后端开发服务器（热重载）           |
| `poe db-init`            | 初始化数据库迁移（首次部署）           |
| `poe db-revision <name>` | 生成数据库迁移文件                     |
| `poe db-migrate`         | 执行数据库迁移                         |
| `poe sync`               | 同步项目依赖（uv sync）                |
| `poe sync-dev`           | 同步含开发依赖（uv sync --all-extras） |

### 前端（TypeScript/React）— 使用 `poe frontend-*` 或 `pnpm`（在 `frontend/` 目录下）

| 命令                     | 说明                                                              |
| ------------------------ | ----------------------------------------------------------------- |
| `poe frontend-check`     | **全量检查**：typecheck + eslint（0 warnings）+ build，提交前必跑 |
| `poe frontend-typecheck` | TypeScript 类型检查（tsc --noEmit）                               |
| `poe frontend-lint`      | ESLint 检查（--max-warnings 0）                                   |
| `poe frontend-build`     | 构建前端生产包                                                    |
| `poe frontend-dev`       | 启动前端开发服务器                                                |
| `poe frontend-install`   | 安装前端依赖（pnpm install）                                      |
| `poe frontend-preview`   | 预览前端构建产物                                                  |

### 注意事项

- **禁止**直接使用 `npx eslint`、`npm run lint`、`npx tsc`、`ruff check`、`basedpyright` 等原始命令
- **禁止**用 `Bash` 工具读取文件（cat/head/tail/grep/find），一律使用 `Read`/`Grep`/`Glob` 工具
- 前端代码变更后**必须**用 `poe frontend-check` 通过后才算完成
- 后端代码变更后**必须**用 `poe lint` 通过后才算完成
- **禁止手动创建迁移文件**，必须使用 `poe db-revision <name>` 命令生成，确保 `MODELS_STATE` 字段正确写入
