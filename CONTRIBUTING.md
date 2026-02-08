# NekroAgent 开发贡献指南

感谢您对 NekroAgent 项目的关注！本指南将帮助您快速开始开发。

## 📚 完整开发文档

详细的开发环境搭建和配置说明，请访问官方文档站：

- 🐧 **[Linux 开发指南](https://doc.nekro.ai/docs/05_app_dev/dev_linux.html)**
- 🍎 **[macOS 开发指南](https://doc.nekro.ai/docs/05_app_dev/dev_macos.html)**
- 🪟 **[Windows 开发指南](https://doc.nekro.ai/docs/05_app_dev/dev_win.html)**

> 文档包含完整的环境配置、常见问题解决方案和最佳实践。

## 🚀 快速开始

### 最小化开发环境搭建

```bash
# 1. 克隆项目
git clone https://github.com/KroMiose/nekro-agent.git
cd nekro-agent

# 2. 安装 UV (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 启动开发依赖服务
docker compose -f docker/docker-compose.dev.yml up -d

# 4. 配置环境变量
cp .env.example .env.dev

# 5. 安装依赖并启动
uv sync --all-extras
uv run bot --docs --env dev --reload
```

### 环境要求

- Python 3.11+
- UV (Python 包管理器)
- Docker & Docker Compose
- Node.js 20+ (仅前端开发需要)

## 🐳 开发服务端口

| 服务           | 端口 | 说明                                      |
| -------------- | ---- | ----------------------------------------- |
| PostgreSQL     | 5433 | 数据库服务 (避免与默认 5432 冲突)         |
| Qdrant         | 6334 | 向量数据库 (避免与生产环境 6333 冲突)     |
| NapCat         | 6199 | QQ 机器人服务 (避免与默认 6099 冲突)      |
| 主应用         | 8021 | NekroAgent 后端 + WebUI                   |
| 前端开发服务器 | 5173 | Vite 开发服务器                           |

## 🔧 常用开发命令

```bash
# 启动完整开发环境（推荐）
uv run bot --docs --env dev --reload

# 启动开发依赖服务
docker compose -f docker/docker-compose.dev.yml up -d

# 停止开发依赖服务
docker-compose -f docker/docker-compose.dev.yml down

# 前端开发
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

### 启动参数说明

| 参数          | 说明                                     |
| ------------- | ---------------------------------------- |
| `--env dev`   | 使用 `.env.dev` 配置文件                 |
| `--reload`    | 代码变更时自动重启                       |
| `--docs`      | 启用 API 文档 (`/api/docs`, `/api/redoc`) |

## 📖 开发资源

### 官方文档

- 📘 [开发指南](https://doc.nekro.ai/docs/05_app_dev/dev_linux.html) - 完整的开发环境配置
- 🔌 [插件开发](https://doc.nekro.ai/docs/04_plugin_dev/00_introduction.html) - 如何开发自定义插件

### API 文档

启用 `--docs` 参数后可访问：

- **Swagger UI**: http://localhost:8021/api/docs
- **ReDoc**: http://localhost:8021/api/redoc

### 社区支持

- 💬 [GitHub Discussions](https://github.com/KroMiose/nekro-agent/discussions) - 提问和讨论
- 🐛 [GitHub Issues](https://github.com/KroMiose/nekro-agent/issues) - 报告问题和功能请求
- 📝 [更新日志](https://github.com/KroMiose/nekro-agent/releases) - 查看版本更新

## 🤝 贡献规范

### 代码规范

- ✅ 保持代码整洁和可读性
- ✅ 遵循项目的 `.cursor/rules/` 中的开发规范
- ✅ 使用类型注解，避免类型断言
- ✅ 处理所有 Linter 警告和错误
- ✅ 仔细审查所有由生成式 AI 生成的内容
- ✅ 提交前至少通过 `poe lint` 与 `poe typecheck`（或使用 `poe check`）

### 错误处理与响应规范

- ✅ 路由层禁止宽泛 `try/except`，仅捕获特定异常
- ✅ 业务错误必须使用 `AppError` 体系（`nekro_agent/schemas/errors.py`）
- ✅ 禁止使用旧的 `Ret` 返回结构
- ✅ 路由层禁止 `logger.exception`，由全局异常处理器统一记录堆栈
- ✅ API 返回使用标准 HTTP 状态码；错误响应支持 i18n（通过 `Accept-Language`）

### 提交 Pull Request

1. **Fork 项目** 并创建功能分支
2. **编写代码** 并确保通过所有测试
3. **更新文档** 如果涉及 API 或功能变更
4. **详细描述** PR 的变更内容和动机
5. **等待审核** 维护者会尽快回复

### 提交信息规范

```bash
# 功能添加
feat: 添加新的插件系统

# 问题修复
fix: 修复数据库连接超时问题

# 文档更新
docs: 更新开发环境配置说明

# 性能优化
perf: 优化向量检索性能

# 代码重构
refactor: 重构插件加载逻辑
```

---

**祝您编码愉快！** 🎉

您的每一个贡献都让 NekroAgent 变得更好。如有任何问题，欢迎在社区中交流讨论！
