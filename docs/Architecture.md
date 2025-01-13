# Nekro Agent 项目架构说明知识手册 🌟

## 1. 项目概述 📝

Nekro Agent 是一个高度可扩展的 AI 代理执行系统，主要特点包括：

- 基于 Docker 的安全沙盒执行环境
- 支持多种 LLM 模型接入
- 提供完整的 WebUI 管理界面
- 支持多种协议端接入（如 OneBot V11）
- 高度可扩展的插件系统

## 2. 技术栈 🛠️

### 2.1 后端技术栈

- **主框架**: Python + FastAPI + NoneBot2
- **数据库**: PostgreSQL + Tortoise ORM
- **容器化**: Docker + Docker Compose
- **API 文档**: OpenAPI/Swagger
- **配置管理**: YAML/JSON

### 2.2 前端技术栈

- **包管理**: pnpm
- **框架**: React + TypeScript
- **UI 库**: Material-UI (MUI)
- **样式**: TailwindCSS
- **状态管理**: Zustand
- **请求处理**: React Query + Axios
- **构建工具**: Vite
- **路由**: React Router

## 3. 后端开发指南 💻

### 3.1 环境配置

系统环境变量通过 `nekro_agent/core/os_env.py` 统一管理，主要包括：

```python
# 数据目录相关
DATA_DIR: str              # 数据根目录
USER_UPLOAD_DIR: str      # 用户上传目录
SANDBOX_SHARED_HOST_DIR: str  # 沙盒共享目录
PROMPT_LOG_DIR: str       # 提示词日志目录
APP_LOG_DIR: str          # 应用日志目录

# 数据库配置
POSTGRES_HOST: str        # 数据库主机
POSTGRES_PORT: int        # 数据库端口
POSTGRES_USER: str        # 数据库用户名
POSTGRES_PASSWORD: str    # 数据库密码
POSTGRES_DATABASE: str    # 数据库名称

# 服务配置
EXPOSE_PORT: int         # 服务暴露端口
STATIC_DIR: str         # 静态资源目录
```

使用示例：

```python
from nekro_agent.core.os_env import OsEnv

# 获取数据目录
data_dir = OsEnv.DATA_DIR
# 获取数据库配置
db_host = OsEnv.POSTGRES_HOST
```

### 3.2 配置系统使用

项目配置分为两类：

1. 系统配置：位于 `${NEKRO_DATA_DIR}/configs/nekro-agent.yaml`
2. 运行时配置：通过 WebUI 或命令动态修改

配置的使用方式：

```python
from nekro_agent.core.config import config

# 读取配置
model_name = config.CHAT_MODEL
api_key = config.API_KEY

# 动态修改配置
config.DEBUG_IN_CHAT = True

# 保存配置
from nekro_agent.core.config import save_config
save_config()
```

### 3.3 数据库操作

项目使用 Tortoise ORM 进行数据库操作，模型定义位于 `nekro_agent/models/` 目录。

使用示例：

```python
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType

# 查询
channel = await DBChatChannel.get_channel(chat_key="group_123456")

# 创建/更新
await DBChatChannel.create(
    chat_key="group_123456",
    chat_type=ChatType.GROUP,
    is_active=True
)

# 删除
await channel.delete()
```

### 3.4 API 开发

新增 API 路由步骤：

1. 在 `nekro_agent/routers/` 下创建新的路由模块
2. 使用 FastAPI 装饰器定义路由
3. 在 `nekro_agent/routers/__init__.py` 中注册路由

示例：

```python
from fastapi import APIRouter
from nekro_agent.schemas.message import Ret

router = APIRouter(prefix="/api/custom", tags=["Custom"])

@router.get("/hello")
async def hello() -> Ret:
    return Ret.success(msg="Hello World!")
```

### 3.5 命令系统

系统命令定义在 `nekro_agent/matchers/command.py` 中，基于 NoneBot2 的命令系统。

添加新命令示例：

```python
from nonebot import on_command
from nonebot.matcher import Matcher
from nonebot.adapters import Bot
from nonebot.params import CommandArg

@on_command("hello", priority=5, block=True).handle()
async def _(matcher: Matcher, bot: Bot, arg: CommandArg()):
    await matcher.finish("Hello World!")
```

### 3.6 扩展开发

扩展模块位于 `extensions/` 目录，每个扩展需要：

1. 实现必要的接口
2. 在配置中启用扩展
3. 提供扩展元数据

扩展示例：

```python
from nekro_agent.schemas.extension import ExtensionMetaData

# 扩展元数据
ext_meta = ExtensionMetaData(
    name="my_extension",
    version="1.0.0",
    description="My Extension"
)

# 扩展初始化
def init():
    # 初始化代码
    pass

# 消息处理
async def on_message(message: str):
    # 消息处理代码
    pass
```

## 4. 前端开发指南 🎨

### 4.1 路由系统

路由配置位于 `frontend/src/router/index.tsx`：

- 基于 `react-router-dom` 的哈希路由
- 集中式路由配置
- 支持路由鉴权

```typescript
const router = createHashRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <MainLayout />,
    children: [
      // ... 子路由配置
    ],
  },
]);
```

### 4.2 状态管理

状态管理相关文件位于 `frontend/src/stores/`：

- 使用 Zustand 进行状态管理
- React Query 处理服务端状态
- 支持持久化存储

### 4.3 主题系统

主题配置位于 `frontend/src/theme/`：

- 支持亮色/暗色主题切换
- Material-UI 主题定制
- 响应式设计

## 5. Docker 部署架构 🐳

### 5.1 主要服务组件

Docker 配置文件位于 `docker/docker-compose.yml` 和 `docker/docker-compose-x-napcat.yml`：

- `nekro_agent`: 核心服务容器
- `nekro_postgres`: 数据库服务
- `napcat`: 协议端服务（可选）

### 5.2 网络配置

Docker 网络配置示例：

```yaml
services:
  nekro_agent:
    image: kromiose/nekro-agent:latest
    environment:
      - NEKRO_DATA_DIR=${NEKRO_DATA_DIR}
      - NEKRO_EXPOSE_PORT=${NEKRO_EXPOSE_PORT:-8021}
      # ... 其他环境变量
```

## 6. 目录结构说明 📁

### 6.1 数据目录结构

```
${NEKRO_DATA_DIR}/
├── configs/                # 配置文件目录
│   └── nekro-agent.yaml   # 主配置文件
├── logs/                   # 日志目录
│   ├── app/               # 应用日志
│   └── prompts/           # 提示词日志
├── uploads/               # 用户上传文件
└── sandboxes/             # 沙盒共享目录
```

### 6.2 代码目录结构

```
nekro-agent/
├── nekro_agent/           # 后端核心
│   ├── core/             # 核心功能
│   │   ├── bot.py       # Bot 实例管理
│   │   ├── config.py    # 配置管理
│   │   ├── database.py  # 数据库管理
│   │   ├── logger.py    # 日志管理
│   │   └── os_env.py    # 环境变量
│   ├── models/          # 数据模型
│   │   ├── db_chat_channel.py    # 聊天频道模型
│   │   ├── db_chat_message.py    # 聊天消息模型
│   │   └── db_user.py           # 用户模型
│   ├── routers/         # API路由
│   │   ├── chat.py     # 聊天相关接口
│   │   ├── config.py   # 配置相关接口
│   │   ├── extensions.py # 扩展相关接口
│   │   └── users.py    # 用户相关接口
│   ├── schemas/         # 数据结构
│   │   ├── agent_ctx.py    # 代理上下文
│   │   ├── agent_message.py # 代理消息
│   │   ├── chat_message.py  # 聊天消息
│   │   └── message.py      # 基础消息
│   ├── services/        # 业务服务
│   │   ├── agents/     # 代理服务
│   │   │   ├── chat_agent.py   # 聊天代理
│   │   │   └── components/     # 代理组件
│   │   ├── chat.py     # 聊天服务
│   │   ├── extension.py # 扩展服务
│   │   └── sandbox/    # 沙盒服务
│   │       ├── executor.py     # 执行器
│   │       └── ext_caller_code.py # 扩展调用
│   ├── systems/         # 系统功能
│   │   ├── message/    # 消息系统
│   │   └── user/       # 用户系统
│   └── tools/          # 工具集
│       ├── collector.py # 方法收集器
│       └── common_util.py # 通用工具
├── frontend/           # 前端项目
│   ├── src/           # 源代码
│   │   ├── components/ # 组件
│   │   │   ├── common/   # 通用组件
│   │   │   ├── layout/   # 布局组件
│   │   │   └── widgets/  # 小部件
│   │   ├── config/    # 配置
│   │   │   ├── env.ts    # 环境配置
│   │   │   └── theme.ts  # 主题配置
│   │   ├── pages/     # 页面
│   │   │   ├── chat/     # 聊天页面
│   │   │   ├── extensions/ # 扩展页面
│   │   │   └── settings/  # 设置页面
│   │   ├── services/  # 服务
│   │   │   └── api/      # API 服务
│   │   ├── stores/    # 状态管理
│   │   │   ├── chat.ts   # 聊天状态
│   │   │   └── user.ts   # 用户状态
│   │   └── utils/     # 工具函数
│   └── public/        # 静态资源
├── extensions/        # 扩展模块
│   ├── basic.py      # 基础工具扩展
│   ├── dice.py       # 骰子扩展
│   └── group_honor.py # 群荣誉扩展
├── docker/           # Docker配置
│   ├── docker-compose.yml      # 基础服务编排
│   └── docker-compose-x-napcat.yml # 协议端服务编排
└── docs/            # 文档
    ├── Architecture.md # 架构文档
    └── README_Extensions.md # 扩展说明
```

这个目录结构展示了项目的主要组件和文件：

1. **后端核心 (`nekro_agent/`)**:
   - `core/`: 核心功能实现，包括配置、数据库、日志等
   - `models/`: 数据库模型定义
   - `routers/`: API 路由和接口定义
   - `schemas/`: 数据结构和验证模型
   - `services/`: 业务逻辑服务
   - `systems/`: 系统级功能
   - `tools/`: 通用工具和辅助函数

2. **前端项目 (`frontend/`)**:
   - `components/`: React 组件库
   - `config/`: 前端配置文件
   - `pages/`: 页面组件
   - `services/`: API 服务封装
   - `stores/`: 状态管理
   - `utils/`: 工具函数

3. **扩展模块 (`extensions/`)**:
   - 包含各种功能扩展的实现
   - 每个文件对应一个独立的扩展模块

4. **Docker 配置 (`docker/`)**:
   - 包含 Docker 服务编排配置
   - 支持基础服务和协议端服务

5. **文档 (`docs/`)**:
   - 项目文档和说明文件
   - 包括架构文档和扩展使用说明

## 7. 开发最佳实践 ✨

1. 配置管理

   - 使用 `config` 对象访问配置
   - 敏感信息使用环境变量
   - 配置修改后及时保存

2. 数据库操作

   - 使用 Tortoise ORM 的异步接口
   - 复杂查询使用原生 SQL
   - 注意事务和并发处理

3. API 开发

   - 使用统一的响应格式
   - 添加适当的权限验证
   - 编写 API 文档注释

4. 扩展开发

   - 遵循扩展接口规范
   - 提供完整的配置说明
   - 做好异常处理

5. 日志记录
   - 使用 `logger` 记录关键信息
   - 区分不同级别的日志
   - 避免敏感信息泄露

## 扩展系统架构

### 扩展系统概述

Nekro Agent 采用了灵活的扩展系统架构，允许通过编写扩展模块来扩展 AI 的功能。扩展系统的主要组件包括：

1. **扩展元数据定义**

   - 每个扩展模块都需要定义 `__meta__` 属性，包含扩展的基本信息
   - 元数据包括：name、version、description、author、url 等信息

2. **扩展方法类型**

   - `tool`: 工具类方法，用于执行具体操作
   - `behavior`: 行为类方法，用于定义 AI 的行为模式
   - `agent`: 代理类方法，用于处理复杂的交互逻辑

3. **扩展加载机制**
   - 通过 `config.EXTENSION_MODULES` 配置启用需要的扩展模块
   - 系统启动时自动加载已配置的扩展模块
   - 扩展模块的方法通过装饰器注册到系统中

### 核心扩展示例

1. **basic - 基础交互工具集**

   ```python
   __meta__ = ExtMetaData(
       name="basic",
       description="[NA] 基础交互工具集",
       version="0.1.0",
       author="KroMiose"
   )
   ```

   - 提供核心的消息处理能力
   - 包含文本消息、图片/文件发送等基础功能

2. **group_honor - 群荣誉扩展**
   ```python
   @agent_collector.mount_method(MethodType.TOOL)
   async def set_user_special_title(chat_key: str, user_qq: str, special_title: str, days: int):
       """赋予用户头衔称号"""
   ```
   - 提供群成员头衔管理功能
   - 支持设置特殊头衔和有效期

### 扩展开发指南

1. **扩展结构**

   ```python
   # 1. 导入必要的模块
   from nekro_agent.services.extension import ExtMetaData
   from nekro_agent.tools.collector import MethodType, agent_collector

   # 2. 定义扩展元数据
   __meta__ = ExtMetaData(
       name="your_extension",
       description="Your extension description",
       version="0.1.0",
       author="Your Name"
   )

   # 3. 实现扩展方法
   @agent_collector.mount_method(MethodType.TOOL)
   async def your_method(param1: str, param2: int, _ctx: AgentCtx):
       """方法说明文档"""
       pass
   ```

2. **注意事项**
   - 所有注解会被 AI 引用，请准确填写
   - `_ctx: AgentCtx` 参数务必放在最后
   - 不要在注解中体现 `_ctx` 的存在
   - 示例代码使用同步调用方式

### 沙盒执行环境

1. **代码执行机制**

   - 扩展方法通过 RPC 在主服务中执行
   - 使用 `ext_caller_code.py` 提供代理执行器
   - 支持安全的方法调用和参数传递

2. **配置项**
   ```python
   SANDBOX_CHAT_API_URL: str = "http://host.docker.internal:{PORT}/api"
   SANDBOX_ONEBOT_SERVER_MOUNT_DIR: str = "/app/nekro_agent_data"
   ```

### 前端扩展管理

1. **扩展列表页面**

   - 显示所有已加载的扩展信息
   - 包含扩展名称、版本、描述、作者等信息
   - 支持查看扩展提供的方法列表

2. **方法类型展示**
   ```typescript
   const METHOD_TYPE_COLORS = {
     tool: "primary",
     behavior: "success",
     agent: "warning",
   };
   ```

## 工具使用指南

### 1. 配置系统

配置系统提供了统一的配置管理机制：

1. **配置文件位置**

   - 主配置文件：`${NEKRO_DATA_DIR}/configs/nekro-agent.yaml`
   - 环境变量配置：`nekro_agent/core/os_env.py`

2. **关键配置项**
   ```python
   class PluginConfig:
       # 扩展配置
       EXTENSION_MODULES: List[str]  # 启用的扩展模块列表

       # 数据库配置
       POSTGRES_HOST: str
       POSTGRES_PORT: int
       POSTGRES_USER: str
       POSTGRES_PASSWORD: str
       POSTGRES_DATABASE: str

       # API 配置
       STABLE_DIFFUSION_API: str  # SD API 地址
   ```

### 2. 消息处理系统

消息处理系统负责处理和发送各类消息：

1. **消息类型**

   - 文本消息
   - 图片消息
   - 文件消息
   - At 消息

2. **消息发送示例**
   ```python
   await chat_service.send_agent_message(
       chat_key=chat_key,
       messages=messages,
       ctx=ctx,
       file_mode=False,
       record=True
   )
   ```

### 3. 代理执行系统

代理执行系统处理 AI 的响应和代码执行：

1. **执行流程**

   - 解析 AI 响应
   - 执行代码或发送消息
   - 处理执行结果
   - 错误重试机制

2. **重试机制**
   ```python
   if retry_depth < config.AI_SCRIPT_MAX_RETRY_TIMES:
       await agent_run(chat_message, addition_prompt_message, retry_depth + 1)
   ```

### 4. 文件处理系统

文件系统管理上传和共享文件：

1. **文件路径**

   - 上传文件：`uploads/`
   - 共享文件：`shared/`
   - 配置文件：`configs/`

2. **路径转换**
   - 容器内路径
   - 主机路径
   - 访问路径

## 开发最佳实践

1. **扩展开发**

   - 遵循扩展开发规范
   - 提供清晰的文档注释
   - 实现必要的错误处理

2. **消息处理**

   - 使用适当的消息类型
   - 处理文件路径转换
   - 实现消息记录功能

3. **配置管理**

   - 使用配置系统管理参数
   - 遵循配置命名规范
   - 提供默认值和说明

4. **错误处理**
   - 实现适当的错误重试
   - 提供清晰的错误信息
   - 记录关键日志信息

### 前端项目结构

```
frontend/src/
├── App.tsx                # 应用根组件
├── assets/               # 静态资源
│   ├── fonts/           # 字体文件
│   └── react.svg        # Logo
├── components/          # 公共组件
│   └── common/         # 通用组件
│       └── ConnectionAlert.tsx  # 连接状态提示
├── config/             # 配置文件
│   └── env.ts         # 环境配置
├── hooks/             # 自定义 Hooks
├── layouts/           # 布局组件
│   └── MainLayout.tsx # 主布局
├── pages/             # 页面组件
│   ├── dashboard/     # 仪表盘
│   ├── extensions/    # 扩展管理
│   ├── login/        # 登录页面
│   ├── logs/         # 日志查看
│   ├── model-groups/ # 模型组管理
│   ├── profile/      # 个人资料
│   ├── protocols/    # 协议管理
│   │   └── napcat/   # NapCat协议
│   ├── sandbox/      # 沙盒管理
│   └── settings/     # 设置页面
├── router/           # 路由配置
│   └── index.tsx    # 路由定义
├── services/         # API服务
│   └── api/         # API封装
│       ├── auth.ts      # 认证相关
│       ├── axios.ts     # Axios配置
│       ├── config.ts    # 配置相关
│       ├── extensions.ts # 扩展相关
│       ├── health.ts    # 健康检查
│       ├── logs.ts      # 日志相关
│       ├── napcat.ts    # NapCat协议
│       └── sandbox.ts   # 沙盒相关
├── stores/           # 状态管理
│   ├── app.ts       # 应用状态
│   ├── auth.ts      # 认证状态
│   └── theme.ts     # 主题状态
├── theme/           # 主题配置
│   └── index.tsx   # 主题定义
├── types/          # 类型定义
└── utils/          # 工具函数
```

### 关键文件说明

1. **路由配置 (`router/index.tsx`)**
   ```typescript
   const router = createHashRouter([
     {
       path: '/login',
       element: <LoginPage />,
     },
     {
       path: '/',
       element: <MainLayout />,
       errorElement: <Navigate to="/login" />,
       children: [
         { path: 'logs', element: <LogsPage /> },
         { path: 'extensions', element: <ExtensionsPage /> },
         { path: 'sandbox-logs', element: <SandboxPage /> },
         // ... 其他路由
       ],
     },
   ])
   ```
   - 使用 `createHashRouter` 创建哈希路由
   - 支持嵌套路由和路由守卫
   - 统一的错误处理和重定向

2. **主布局组件 (`layouts/MainLayout.tsx`)**
   ```typescript
   const menuItems = [
     { text: '系统日志', icon: <TerminalIcon />, path: '/logs' },
     { text: '扩展管理', icon: <ExtensionIcon />, path: '/extensions' },
     // ... 其他菜单项
   ]
   ```
   - 响应式侧边栏设计
   - 动态菜单配置
   - 主题切换支持
   - GitHub Star 数显示
   - 版本信息展示

3. **主题配置 (`theme/index.tsx`)**
   ```typescript
   const theme = createTheme({
     palette: {
       mode,
       primary: {
         main: PRIMARY_COLOR,
         contrastText: '#fff',
       },
     },
     typography: {
       fontFamily: globalFonts.sans,
       // ... 字体配置
     },
     components: {
       // ... 组件样式覆盖
     },
   })
   ```
   - 支持亮色/暗色主题
   - 自定义字体配置
   - 全局滚动条样式
   - Material-UI 组件样式覆盖

4. **页面组件示例**

   a. **日志页面 (`pages/logs/index.tsx`)**
   ```typescript
   const LOG_LEVEL_COLORS = {
     ERROR: 'error',
     WARNING: 'warning',
     SUCCESS: 'success',
     INFO: 'info',
     DEBUG: 'secondary',
   }
   ```
   - 实时日志显示
   - 日志级别过滤
   - 自动滚动功能
   - 高级模式支持

   b. **设置页面 (`pages/settings/index.tsx`)**
   ```typescript
   const { data: configs } = useQuery({
     queryKey: ['configs'],
     queryFn: () => configApi.getConfigs(),
   })
   ```
   - 配置项管理
   - 实时保存
   - 敏感信息保护
   - 分组显示

5. **状态管理示例**

   a. **认证状态 (`stores/auth.ts`)**
   ```typescript
   export const useAuthStore = create<AuthStore>((set) => ({
     userInfo: null,
     setUserInfo: (userInfo) => set({ userInfo }),
     logout: () => set({ userInfo: null }),
   }))
   ```

   b. **主题状态 (`stores/theme.ts`)**
   ```typescript
   export const useColorMode = create<ColorModeStore>((set) => ({
     mode: 'light',
     toggleColorMode: () =>
       set((state) => ({
         mode: state.mode === 'light' ? 'dark' : 'light',
       })),
   }))
   ```

6. **API 服务封装**

   a. **基础配置 (`services/api/axios.ts`)**
   ```typescript
   const axiosInstance = axios.create({
     baseURL: '/api',
     timeout: 10000,
     headers: {
       'Content-Type': 'application/json',
     },
   })
   ```
   - 统一的请求配置
   - 响应拦截器
   - 错误处理

   b. **API 模块 (`services/api/*.ts`)**
   ```typescript
   export const configApi = {
     getConfigs: async () => {
       const response = await axios.get<ConfigResponse>('/configs')
       return response.data
     },
     // ... 其他方法
   }
   ```
   - 模块化 API 管理
   - TypeScript 类型支持
   - 统一的响应格式

7. **工具函数 (`utils/`)**
   - 日期格式化
   - 数据转换
   - 验证函数
   - 通用工具方法

### 前端开发规范

1. **组件开发**
   - 使用函数式组件
   - 遵循 React Hooks 规范
   - 组件职责单一
   - Props 类型定义完整

2. **状态管理**
   - 使用 Zustand 管理全局状态
   - React Query 处理服务端状态
   - 避免状态冗余
   - 合理使用缓存

3. **样式管理**
   - Material-UI 主题系统
   - 统一的样式命名
   - 响应式设计
   - 避免内联样式

4. **API 调用**
   - 统一的错误处理
   - 请求缓存策略
   - 类型安全
   - 优雅降级
