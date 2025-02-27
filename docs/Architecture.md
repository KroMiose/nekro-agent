# NekroAgent 项目架构文档

## 技术栈概览

### 后端技术栈
- Python + FastAPI + NoneBot2
- PostgreSQL + Tortoise ORM
- Docker + Docker Compose
- Poetry 包管理

### 前端技术栈
- React + TypeScript + Vite
- Material-UI + TailwindCSS
- Zustand + React Query
- pnpm 包管理

## 目录结构

### 后端架构 (`nekro_agent/`)
```
nekro_agent/
├── api/          # API 相关实现
├── cli/          # 命令行工具
├── core/         # 核心功能模块
├── libs/         # 通用库
├── matchers/     # NoneBot2 消息匹配器
├── models/       # 数据模型定义
├── routers/      # FastAPI 路由
├── schemas/      # Pydantic 模型
├── services/     # 业务服务层
├── systems/      # 系统级功能
└── tools/        # 工具类
```

### 前端架构 (`frontend/`)
```
frontend/
└── src/
    ├── assets/      # 静态资源
    ├── components/  # 通用组件
    ├── config/      # 配置文件
    ├── hooks/       # React Hooks
    ├── layouts/     # 布局组件
    ├── pages/       # 页面组件
    ├── router/      # 路由配置
    ├── services/    # API 服务
    ├── stores/      # 状态管理
    ├── theme/       # 主题配置
    ├── types/       # TypeScript 类型
    └── utils/       # 工具函数
```

## 开发规范

### 通用规范
- 严格执行类型注解，避免使用类型断言
- 保持代码整洁，合理拆分功能模块
- 及时处理 Linter 警告/错误
- 最小化修改原则

### 后端开发规范
- 使用 Pydantic 模型处理外部数据
- 遵循 RUFF 代码规范
- 扩展开发参考 Extension_Development.md

### 前端开发规范
- 使用 Material-UI 组件与 TailwindCSS 进行原子化开发
- 主题相关配置统一在 theme/ 目录下管理
- 使用已实现的流式请求工具进行流式推送服务开发

## 项目依赖

### 后端依赖
- 详见 pyproject.toml 和 poetry.lock

### 前端依赖
- 详见 package.json 和 pnpm-lock.yaml

## 部署相关
- 使用 Docker 和 Docker Compose 进行容器化部署
- 配置文件：dockerfile 和 docker/ 目录
- 环境变量：.env 系列文件

## 核心模块说明

### 2.1 配置系统

- 系统配置: `nekro_agent/core/config.py`

使用示例:

```python
from nekro_agent.core.config import config

config.DATA_DIR
```

### 2.2 数据模型

位置: `nekro_agent/models/`

- `db_chat_channel.py`: 聊天频道模型
- `db_chat_message.py`: 聊天消息模型
- `db_user.py`: 用户模型

### 2.3 API 路由

位置: `nekro_agent/routers/`

- `chat.py`: 聊天相关接口
- `config.py`: 配置相关接口
- `extensions.py`: 扩展相关接口
- `users.py`: 用户相关接口
- `dashboard.py`: 仪表盘相关接口

### 2.4 扩展系统

位置: `nekro_agent/services/extension.py`

- 扩展加载器
- 方法收集器: `nekro_agent/tools/collector.py`
- 沙盒执行器: `nekro_agent/services/sandbox/`

### 2.5 前端架构

位置: `frontend/src/`

- 路由定义: `router/index.tsx`
- 状态管理: `stores/`
- API 服务: `services/api/`
- 组件库: `components/`
- 仪表盘: `pages/dashboard/`

## 开发指南

### 3.1 新增功能开发流程

1. **后端 API**

```python
# nekro_agent/routers/custom.py
from fastapi import APIRouter
from nekro_agent.schemas.message import Ret
from nekro_agent.systems.user.perm import Role, require_role
router = APIRouter(prefix="/api/custom", tags=["Custom"])

@router.get("/example", summary="示例接口")
@require_role(Role.User)
async def example() -> Ret[None]:
    return Ret[None].success(data=None)
```

2. **扩展模块**

示例扩展: `extensions/basic.py`

3. **前端开发**

组件位置: `frontend/src/components/custom/index.tsx`
页面位置: `frontend/src/pages/custom/index.tsx`
服务 API: `frontend/src/services/api/custom.ts`

### 3.2 关键注意事项

1. **后端开发**

- API 返回使用 `Ret[T]` 类封装
- 数据库操作使用异步接口
- 配置修改通过 `config` 对象 (from nekro_agent.core.config import config)
- 日志记录使用 `logger` 对象 (from nekro_agent.core.logger import logger)

2. **扩展开发**

- 必须定义 `__meta__` 属性
- 提示词工程严谨合理

3. **前端开发**

- 组件需要 TypeScript 类型
- API 调用统一封装

## 注意事项

- 注意严格类型注解
- 必要日志记录
- 非必要则进行最小化改动，保持前向兼容
- 对代码有困惑时请指出提问，不要猜测
