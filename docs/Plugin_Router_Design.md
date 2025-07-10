# Nekro Agent 插件路由系统设计文档

## 概述

本文档详细描述了为 Nekro Agent 插件系统新增的路由功能，该功能扩展了现有的 Webhook 机制，允许插件注册自定义的 FastAPI 路由，提供完整的 RESTful API 能力。

## 背景与需求

### 现有限制
- **Webhook 局限性**: 现有 Webhook 系统只支持 POST 请求到固定路径 `/webhook/{endpoint}`
- **缺乏 RESTful 支持**: 无法支持 GET、PUT、DELETE 等 HTTP 方法
- **路径结构固化**: 无法自定义复杂的路径结构和参数
- **功能受限**: 无法构建完整的 Web API 服务

### 设计目标
1. **保守扩展**: 最小侵入现有系统，保持向下兼容
2. **功能完整**: 提供完整的 FastAPI 路由功能
3. **热重载支持**: 支持插件路由的动态加载/卸载
4. **易于使用**: 提供简洁的 API 和清晰的使用示例

## 架构设计

### 核心组件

#### 1. NekroPlugin 扩展
```python
class NekroPlugin:
    # 新增属性
    _router_func: Optional[Callable[[], APIRouter]] = None
    _router: Optional[APIRouter] = None
    
    # 新增方法
    def mount_router(self) -> Callable
    def get_plugin_router(self) -> Optional[APIRouter]
```

#### 2. PluginCollector 扩展
```python
class PluginCollector:
    # 新增方法
    def load_plugins_api(self) -> APIRouter
    def get_plugins_with_router(self) -> List[NekroPlugin]
    def get_plugin_router_info(self) -> Dict[str, Dict[str, Any]]
```

#### 3. 路由挂载系统
```python
# 在 routers/__init__.py 中
def load_plugins_api() -> APIRouter
def mount_routers(app: FastAPI)  # 扩展现有函数
```

### 设计模式

本设计参考了现有的**适配器系统**的路由管理模式：

| 组件 | 适配器系统 | 插件系统 |
|------|------------|----------|
| 基类 | `BaseAdapter` | `NekroPlugin` |
| 路由方法 | `get_adapter_router()` | `get_plugin_router()` |
| 加载函数 | `load_adapters_api()` | `load_plugins_api()` |
| 挂载路径 | `/api/adapters/{key}` | `/plugins/{key}` |

## 实现方案

### 1. 插件路由注册

#### 基本用法
```python
from fastapi import APIRouter
from nekro_agent.services.plugin.base import NekroPlugin

plugin = NekroPlugin(...)

@plugin.mount_router()
def create_router() -> APIRouter:
    router = APIRouter()
    
    @router.get("/hello")
    async def hello():
        return {"message": "Hello from plugin!"}
    
    return router
```

#### 完整示例
```python
@plugin.mount_router()
def create_router() -> APIRouter:
    router = APIRouter()
    
    # RESTful API 端点
    @router.get("/items", response_model=List[Item])
    async def get_items():
        return items_db.values()
    
    @router.post("/items", response_model=Item)
    async def create_item(item: CreateItemRequest):
        # 业务逻辑
        return new_item
    
    @router.get("/items/{item_id}")
    async def get_item(item_id: int):
        if item_id not in items_db:
            raise HTTPException(404, "Item not found")
        return items_db[item_id]
    
    return router
```

### 2. 路由挂载机制

#### 挂载路径规则
- **基础路径**: `/plugins/{plugin_key}`
- **插件键格式**: `{author}.{module_name}`
- **完整路径示例**: `/plugins/nekro.example/hello`

#### 动态加载流程
1. 插件系统启动时调用 `load_plugins_api()`
2. 遍历所有启用的插件
3. 调用 `plugin.get_plugin_router()` 获取路由
4. 使用 `api.include_router()` 挂载到主路由

### 3. 热重载机制

#### 重载流程
1. 调用插件的 `cleanup_method()` 清理资源
2. 从 `loaded_plugins` 中移除插件
3. 卸载 Python 模块
4. 重新导入和初始化插件
5. **路由自动重载**: 新路由在下次 API 调用时自动生效

#### 路由缓存管理
```python
def get_plugin_router(self) -> Optional[APIRouter]:
    if self._router is not None:
        return self._router  # 返回缓存的路由
    
    if self._router_func:
        self._router = self._router_func()  # 生成新路由
        return self._router
    
    return None
```

### 4. 与现有系统的集成

#### 保持向下兼容
- **Webhook 功能保持不变**: 现有 webhook 机制继续工作
- **API 路径隔离**: 插件路由使用独立的路径前缀
- **配置系统兼容**: 继续使用现有的配置管理机制

#### 统一管理
- **插件详情API扩展**: 在插件详情中添加路由信息
- **路由信息查询**: 新增 `/api/plugins/router-info` 端点
- **文档集成**: 插件路由自动集成到 OpenAPI 文档

## API 接口

### 1. 获取插件路由信息
```http
GET /api/plugins/router-info
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_plugins": 5,
    "plugins_with_router": 2,
            "router_summary": [
          {
            "plugin_key": "nekro.example",
            "plugin_name": "示例插件",
            "mount_path": "/plugins/nekro.example",
            "enabled": true
          }
        ],
            "detailed_routes": {
          "nekro.example": {
            "plugin_name": "示例插件",
            "mount_path": "/plugins/nekro.example",
            "routes_count": 3,
        "routes": [
          {
            "path": "/hello",
            "methods": ["GET"],
            "name": "hello"
          }
        ]
      }
    }
  }
}
```

### 2. 插件详情扩展
```http
GET /api/plugins/detail/{plugin_id}
```

**新增字段**:
```json
{
  // ... 现有字段
  "router": {
    "mount_path": "/plugins/nekro.example",
    "routes_count": 3,
    "routes": [...]
  }
}
```

## 安全考虑

### 1. 权限控制
- **管理员权限**: 插件路由信息查询需要管理员权限
- **插件隔离**: 每个插件的路由在独立命名空间中
- **访问控制**: 插件可以在路由中实现自己的访问控制

### 2. 错误处理
- **异常隔离**: 插件路由异常不会影响主系统
- **优雅降级**: 路由加载失败时跳过该插件，不影响其他插件
- **日志记录**: 详细记录路由加载和错误信息

## 性能考虑

### 1. 路由缓存
- **懒加载**: 路由实例只在首次访问时创建
- **缓存复用**: 生成的路由实例被缓存，避免重复创建
- **内存管理**: 插件卸载时清理路由缓存

### 2. 加载优化
- **延迟导入**: 使用延迟导入避免循环依赖
- **错误恢复**: 单个插件路由失败不影响其他插件
- **批量加载**: 所有插件路由一次性挂载到主路由

## 使用指南

### 1. 基础使用

#### 步骤1: 创建插件文件
```python
# plugins/workdir/my_plugin.py
from nekro_agent.services.plugin.base import NekroPlugin
from fastapi import APIRouter

plugin = NekroPlugin(
    name="我的插件",
    module_name="my_plugin", 
    description="示例插件",
    version="1.0.0",
    author="your_name",
    url="",
)

@plugin.mount_router()
def create_router() -> APIRouter:
    router = APIRouter()
    
    @router.get("/test")
    async def test():
        return {"message": "Hello from my plugin!"}
    
    return router
```

#### 步骤2: 重载插件
```http
POST /api/plugins/reload?module_name=my_plugin
```

#### 步骤3: 访问插件API
```http
GET /plugins/your_name.my_plugin/test
```

### 2. 高级功能

#### 数据验证
```python
from pydantic import BaseModel

class CreateUserRequest(BaseModel):
    name: str
    email: str

@router.post("/users", response_model=User)
async def create_user(user_data: CreateUserRequest):
    # 自动验证请求数据
    return created_user
```

#### 依赖注入
```python
from fastapi import Depends

def get_current_user():
    # 用户认证逻辑
    return user

@router.get("/profile")
async def get_profile(user=Depends(get_current_user)):
    return user.profile
```

#### 错误处理
```python
from fastapi import HTTPException

@router.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(
            status_code=404, 
            detail="Item not found"
        )
    return items_db[item_id]
```

## 最佳实践

### 1. 路由设计
- **RESTful 原则**: 遵循 REST API 设计规范
- **版本控制**: 在路径中包含 API 版本信息
- **文档完整**: 为所有端点添加详细的文档字符串

### 2. 错误处理
- **统一错误格式**: 使用一致的错误响应格式
- **适当的状态码**: 返回合适的 HTTP 状态码
- **详细错误信息**: 提供有助于调试的错误信息

### 3. 性能优化
- **数据分页**: 为列表端点实现分页功能
- **缓存策略**: 对频繁访问的数据进行缓存
- **异步操作**: 使用异步函数处理 I/O 操作

### 4. 安全考虑
- **输入验证**: 严格验证所有输入数据
- **权限检查**: 在需要时实现访问控制
- **日志记录**: 记录重要操作和异常

## 故障排查

### 1. 常见问题

#### 路由不生效
- **检查插件状态**: 确认插件已启用
- **检查路由函数**: 确认 `mount_router` 装饰器正确使用
- **检查返回值**: 确认路由函数返回 `APIRouter` 实例

#### 404 错误
- **路径检查**: 确认访问路径正确
- **插件键确认**: 确认插件键格式为 `author.module_name`
- **路由注册**: 确认路由已正确注册

### 2. 调试方法

#### 查看插件路由信息
```http
GET /api/plugins/router-info
```

#### 查看插件详情
```http
GET /api/plugins/detail/{plugin_key}
```

#### 检查日志
```bash
# 查看插件加载日志
grep "插件.*路由" logs/nekro_agent.log
```

## 未来扩展

### 1. 计划功能
- **中间件支持**: 为插件路由添加中间件机制
- **认证集成**: 与主系统的认证机制集成
- **速率限制**: 为插件 API 添加速率限制功能
- **监控指标**: 为插件路由添加监控和统计功能

### 2. 性能优化
- **路由预编译**: 在启动时预编译所有路由
- **负载均衡**: 支持插件 API 的负载均衡
- **缓存层**: 为插件数据添加统一缓存层

## 总结

插件路由系统的设计采用了保守扩展的策略，在保持现有功能完整性的同时，为插件提供了强大的 Web API 能力。该系统具有以下特点：

1. **功能完整**: 支持完整的 FastAPI 功能
2. **易于使用**: 简洁的 API 设计和丰富的示例
3. **向下兼容**: 不影响现有 Webhook 功能
4. **动态管理**: 支持热重载和动态路由管理
5. **安全可靠**: 具备完善的错误处理和安全机制

通过这个扩展，Nekro Agent 的插件系统能够满足更复杂的 Web 服务需求，为插件开发者提供了更大的灵活性和更强的功能支持。 