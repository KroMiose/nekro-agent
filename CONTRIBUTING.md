# NekroAgent 开发贡献指南

感谢您对 NekroAgent 项目的关注！本指南将帮助您快速开始开发。

## 🚀 快速开始

### 环境要求

- Python 3.10+ + Poetry
- Node.js 18+ (前端开发)
- Docker & Docker Compose

### 开发环境搭建流程

1. **克隆项目**

   ```bash
   git clone https://github.com/KroMiose/nekro-agent.git
   cd nekro-agent
   ```

2. **启动开发依赖服务编排**

   ```bash
   # 启动 PostgreSQL + Qdrant + NapCat (可选)
   docker-compose -f docker/docker-compose.dev.yml up -d
   ```

3. **安装 Python 依赖**

   ```bash
   poetry install
   ```

4. **配置环境变量**

   ```bash
   # 复制配置模板（已预配置连接开发服务）
   cp .env.example .env.dev

   # 根据需要修改配置
   vim .env.dev
   ```

5. **启动主应用**

   ```bash
   # 🎯 推荐的开发启动命令
   poetry run bot --docs --env dev --reload
   ```

6. **启动前端开发服务器**（可选）
   ```bash
   cd frontend
   pnpm install
   pnpm run dev
   ```

## 🐳 开发服务说明

### 服务端口映射

| 服务           | 端口 | 说明                                 |
| -------------- | ---- | ------------------------------------ |
| PostgreSQL     | 5433 | 数据库服务 (避免与默认 5432 冲突)    |
| Qdrant         | 6333 | 向量数据库                           |
| NapCat         | 6199 | QQ 机器人服务 (避免与默认 6099 冲突) |
| 主应用         | 8021 | NekroAgent 后端 + WebUI              |
| 前端开发服务器 | 5173 | Vite 开发服务器                      |

### 数据持久化

开发环境数据存储在项目目录下：

- `./data/dev_postgres_data/` - PostgreSQL 数据
- `./data/dev_qdrant_data/` - Qdrant 数据
- `./data/napcat_data/` - NapCat 配置和数据

## ⚙️ 配置说明

### 环境变量配置

`.env.example` 已预配置开发环境默认值，可根据实际需求调整

### 命令行参数

启动命令示例

```bash
poetry run bot --docs --env dev --reload
```

参数说明：

| 参数          | 说明          | 示例                             |
| ------------- | ------------- | -------------------------------- |
| `--env <ENV>` | 指定环境配置  | `--env dev` (使用 .env.dev 配置) |
| `--reload`    | 启用自动重载  | 代码变更时自动重启               |
| `--docs`      | 启用 API 文档 | 访问 `/api/docs` 和 `/api/redoc` |

## 🏗️ 开发工作流

### 热重载开发

启用 `--reload` 后，以下目录变更会触发自动重启：

- `nekro_agent/` - 核心应用代码
- `plugins/` - 插件代码

### 前端开发

```bash
cd frontend
pnpm install --frozen-lockfile  # 安装依赖
pnpm dev     # 启动开发服务器
pnpm build   # 构建生产版本
```

### API 文档

启用 `--docs` 参数后可访问：

- **Swagger UI**: http://localhost:8021/api/docs
- **ReDoc**: http://localhost:8021/api/redoc

## 🔧 常用命令

```bash
# 启动开发依赖服务编排
docker-compose -f docker/docker-compose.dev.yml up -d

# 停止开发依赖服务编排
docker-compose -f docker/docker-compose.dev.yml down

# 完整开发模式启动 NekroAgent
poetry run bot --docs --env dev --reload
```

## 🧪 测试

```bash
# 运行测试
pytest

# 带覆盖率测试
pytest --cov=nekro_agent

# 前端测试
cd frontend && pnpm test
```

## 🤝 贡献指南

- 保持代码整洁和可读性
- 编写必要的测试
- 更新相关文档
- 遵循项目的编码规范
- 详细描述 PR 的变更内容

## 📖 相关资源

- [部署指南](./docs/安装指南.md)
- [GitHub Issues](https://github.com/KroMiose/nekro-agent/issues)
- [GitHub Discussions](https://github.com/KroMiose/nekro-agent/discussions)

---

**祝您编码愉快！** 🎉

您的贡献让 NekroAgent 变得更好。
