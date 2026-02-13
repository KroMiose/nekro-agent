# NekroAgent 国际化与技术债务清理改造方案

> 版本: 1.2  
> 创建时间: 2024-12  
> 更新时间: 2024-12-20  
> 核心目标: 实现系统全面国际化，清理核心系统技术债务，提高代码质量与规范性  
> **改造范围**: 核心前后端系统，适配器层暂不改造

---

## 一、项目背景与目标

### 1.1 改造背景

当前 NekroAgent 系统存在以下技术债务：

1. **国际化缺失**: 后端所有消息、配置描述、错误提示均为硬编码中文
2. **响应结构不规范**: 使用自定义 `code` 字段而非标准 HTTP 状态码
3. **错误处理碎片化**: 各路由独立 try-catch，错误类型不统一
4. **前后端耦合**: 前端需要特殊处理后端非标准响应格式
5. **动态信息硬编码**: 配置项、插件、资源分类等动态内容无法国际化
6. **类型约束不严格**: 存在大量 `Dict` 类型硬编码结构，类型推导不准确

### 1.2 改造目标

| 目标             | 说明                                             |
| ---------------- | ------------------------------------------------ |
| **全面国际化**   | 支持 zh-CN/en-US，所有用户可见文本均可本地化     |
| **规范化响应**   | 使用标准 HTTP 状态码，简化响应结构               |
| **统一错误处理** | 建立错误类型体系，全局异常处理                   |
| **降低复杂度**   | 移除冗余代码，统一处理模式                       |
| **提高代码质量** | 完善类型注解，增强可维护性，禁止硬编码字符串字典 |

### 1.3 改造范围

| 范围           | 状态         | 说明                                               |
| -------------- | ------------ | -------------------------------------------------- |
| 核心路由层     | ✅ 本次改造  | `nekro_agent/routers/` 下所有 API 路由             |
| 前端 API 服务  | ✅ 本次改造  | `frontend/src/services/api/` 响应格式统一          |
| 前端页面       | ✅ 本次改造  | `frontend/src/pages/` 错误处理与 console 清理      |
| 配置系统       | ✅ 本次改造  | 配置项描述国际化                                   |
| 插件系统       | ✅ 本次改造  | 插件元信息国际化                                   |
| **适配器层**   | ⏸️ 暂不改造 | `nekro_agent/adapters/` 涉及外部接口，风险较大     |
| 类型优化       | 🔜 后续处理  | `Any` 类型和 `# type: ignore` 清理                 |

### 1.4 核心原则

- **一次到位**: 不留兼容层，兼容本身就是技术债务
- **全局处理**: 错误由全局异常处理器统一处理，路由中禁止宽泛 try-catch
- **聚焦处理**: 只捕获需要特殊处理的异常，其他让全局兜底
- **最小侵入**: 优先复用现有架构，避免过度设计
- **类型安全**: 所有路由必须返回明确的 Pydantic 模型，禁止返回无约束字典（如 `Dict[str, Any]`）
- **渐进稳定**: 适配器层暂不改造，优先确保核心系统稳定

### 1.5 ⚠️ 关键编码原则（必读）

> **禁止宽泛的错误处理！**
>
> 不要给每个路由都套一层无用的 try-catch，而是通过全局拦截器的方式自动化处理这些错误。
> 只做必要的、聚焦的错误处理。

```python
# ❌ 绝对禁止
@router.post("/action")
async def action():
    try:
        result = await service.do()
        return result
    except Exception as e:  # 宽泛捕获
        logger.exception(f"失败: {e}")  # 路由中记录日志
        raise SomeError(detail=str(e))

# ✅ 正确做法
@router.post("/action")
async def action():
    return await service.do()  # 直接调用，让全局处理器兜底
```

**全局异常处理器负责**:

1. 捕获所有异常
2. 记录日志（包括 `logger.exception` 记录堆栈）
3. 返回标准化的错误响应
4. 根据 Accept-Language 返回本地化消息

---

## 二、现状分析与技术债务清单

### 2.1 技术债务统计概览

| 类别                            | 数量    | 涉及文件数     | 严重程度 | 本次改造 |
| ------------------------------- | ------- | -------------- | -------- | -------- |
| `return Ret.` 调用              | 277 处  | 19 个路由文件  | 🔴 高    | ✅ 改造  |
| `except Exception` 宽泛捕获     | 80 处   | 18 个路由文件  | 🔴 高    | ✅ 改造  |
| 路由中 `logger.exception/error` | 65 处   | 14 个路由文件  | 🟡 中    | ✅ 改造  |
| `raise HTTPException`           | 28 处   | 10 个文件      | 🟡 中    | ⚠️ 部分  |
| 前端 `.data.data` 模式          | 64 处   | 16 个 API 文件 | 🔴 高    | ✅ 改造  |
| 前端 `console.log/error/warn`   | 90 处   | 15 个页面文件  | 🟡 中    | ✅ 改造  |
| `# type: ignore/noqa`           | 50 处   | 29 个文件      | 🟡 中    | 🔜 后续  |
| `Any` 类型使用                  | 208 处  | 47 个文件      | 🟡 中    | 🔜 后续  |
| 空的 `except: pass`             | 10+ 处  | 多个文件       | 🔴 高    | ⚠️ 部分  |
| `TODO/FIXME` 注释               | 11 处   | 7 个文件       | 🟢 低    | 🔜 后续  |

> **改造范围说明**：
> - ✅ 改造：本次重点处理
> - ⚠️ 部分：仅处理核心路由，适配器层暂不处理
> - 🔜 后续：作为独立任务后续处理

### 2.2 改造范围界定

#### ✅ 本次改造范围

1. **核心路由层** (`nekro_agent/routers/`)：所有 API 路由的响应格式和错误处理
2. **前端 API 服务** (`frontend/src/services/api/`)：移除 `.data.data` 模式
3. **前端页面** (`frontend/src/pages/`)：清理 console 调用，使用通知系统
4. **基础设施**：国际化类型、错误体系、全局异常处理器
5. **配置系统**：配置项描述的 i18n
6. **插件系统**：插件元信息的 i18n

#### ⏸️ 暂不改造范围

1. **适配器层** (`nekro_agent/adapters/`)：涉及大量外部接口对接，改造风险较大
   - `email/` - 邮箱适配器
   - `onebot_v11/` - QQ OneBot 适配器
   - `sse/` - SSE 适配器
   - `telegram/` - Telegram 适配器
   - `discord/` - Discord 适配器
   - `wechatpad/` - 微信适配器
   - `minecraft/` - Minecraft 适配器

2. **类型优化**：`Any` 类型使用和 `# type: ignore` 清理作为独立任务

3. **TODO/FIXME 清理**：作为独立代码质量任务

### 2.2 当前响应结构 (问题)

**文件**: `nekro_agent/schemas/message.py`

```python
class Ret(BaseModel):
    code: int    # 200=成功, 400=失败, 500=错误 (业务码，非HTTP状态码)
    msg: str     # 硬编码中文消息
    data: Any    # 实际数据
```

**问题**:

- 所有请求都返回 HTTP 200，通过 `code` 区分状态
- 前端需要 `response.data.data` 获取实际数据
- 与 RESTful 规范不符
- `msg` 无法国际化

### 2.3 当前错误处理 (问题)

**典型路由代码**:

```python
@router.post("/scan/start")
async def start_scan(...) -> Ret:
    try:
        scan_id = await scanner_service.start_scan()
        return Ret.success(msg="扫描任务已启动", data={"scan_id": scan_id})
    except Exception as e:
        return Ret.error(msg=f"启动扫描失败: {e}")
```

**问题**:

- 每个路由都有独立 try-catch
- 错误消息硬编码中文
- 错误类型不统一，前端无法精确处理
- 代码重复率高

### 2.4 现有全局异常处理器 (问题)

**文件**: `nekro_agent/routers/__init__.py`

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.exception(f"服务器错误: {exc}")
    return JSONResponse(
        status_code=500,
        content=Ret.error(msg=str(exc)).model_dump(),
    )
```

**问题**:

- 返回旧的 `Ret.error()` 格式
- 只处理通用 Exception
- 消息硬编码中文
- 不支持 i18n

### 2.5 预定义 HTTPException (问题)

**文件**: `nekro_agent/schemas/http_exception.py`

```python
credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
login_expired_exception = HTTPException(status_code=401, detail="Login expired. Please re-login.")
# ... 更多预定义异常
```

**问题**:

- 消息硬编码（英文）
- 不支持参数化
- 不支持 i18n
- 与 AppError 体系不统一

### 2.6 前端 Axios 拦截器 (问题)

**文件**: `frontend/src/services/api/axios.ts`

```typescript
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    console.error("Response error:", error); // console.error
    if (error.response?.status === 401) {
      return Promise.reject(new Error("用户名或密码错误")); // 硬编码中文
    }
    return Promise.reject(new Error("登录已过期，请重新登录")); // 硬编码中文
  }
);
```

**问题**:

- 使用 `console.error` 而非统一日志
- 硬编码中文错误消息
- 没有发送 `Accept-Language` 头
- 没有使用 `ApiError` 类

### 2.7 前端 API 调用模式 (问题)

```typescript
// 典型的 API 调用 (plugins_market.ts)
try {
  const response = await axios.get<{ data: CloudPlugin[] }>(
    "/cloud/plugins-market/list"
  );
  return response.data.data; // .data.data 模式
} catch (error) {
  console.error("获取云端插件列表失败:", error); // console.error + 硬编码中文
  throw error;
}
```

**问题**:

- 需要 `.data.data` 获取实际数据
- catch 中 console.error 后 throw（重复处理）
- 硬编码中文错误消息

### 2.8 空的异常处理 (问题)

```python
# 多处存在吞掉异常的代码
try:
    # 某些操作
except Exception:
    pass  # 吞掉异常，掩盖问题
```

**涉及文件**:

- `nekro_agent/adapters/email/adapter.py` (4 处)
- `nekro_agent/adapters/email/config.py` (1 处)
- `nekro_agent/services/config_service.py` (1 处)
- `nekro_agent/routers/config.py` (1 处)
- 等等

### 2.9 需要清理的 TODO/FIXME

共 23 处分布在 14 个文件中，需要在改造过程中一并处理：

- `nekro_agent/core/config.py` (2 处)
- `nekro_agent/adapters/wechatpad/realtime_processor.py` (4 处)
- `nekro_agent/adapters/wechatpad/adapter.py` (3 处)
- 等等

### 2.3 动态信息硬编码 (问题)

**配置系统** (`nekro_agent/core/config.py`):

```python
APP_LOG_LEVEL = Field(
    default="INFO",
    title="应用日志级别",           # 硬编码中文
    description="需要重启应用后生效",  # 硬编码中文
)
```

**空间清理** (`nekro_agent/services/space_cleanup/scanner.py`):

```python
ResourceCategory(
    display_name="聊天上传资源",      # 硬编码中文
    description="聊天中接收到的文件",  # 硬编码中文
    risk_message="清理后AI无法访问",  # 硬编码中文
)
```

**插件系统** (`plugins/builtin/basic.py`):

```python
plugin = NekroPlugin(
    name="基础交互插件",           # 硬编码中文
    description="提供基础功能",     # 硬编码中文
)
```

### 2.4 前端问题

**axios 拦截器** (`frontend/src/services/api/axios.ts`):

```typescript
if (error.response?.status === 401) {
  return Promise.reject(new Error("用户名或密码错误")); // 硬编码中文
}
```

---

## 三、设计方案

### 3.1 语言枚举与 i18n 基础类型

**新建文件**: `nekro_agent/schemas/i18n.py`

```python
"""国际化基础类型定义

核心设计原则:
1. 使用显式关键字参数，每个语言都有清晰的键名
2. 函数名 `i18n_text` 具有标志性，便于全局搜索
3. 添加新语言时：修改函数签名 → 所有调用点报类型错误 → 逐个补充翻译
"""

from enum import Enum
from typing import Dict, Optional


class SupportedLang(str, Enum):
    """支持的语言枚举

    与前端 i18next 配置保持一致。
    语言代码遵循 BCP 47 标准。
    
    添加新语言时:
    1. 在此枚举添加新值
    2. 更新 i18n_text() 函数签名
    3. 更新 from_accept_language() 解析逻辑
    """
    ZH_CN = "zh-CN"
    EN_US = "en-US"


# i18n 字典类型：使用字符串键确保 JSON 序列化兼容性
# 键为语言代码字符串（如 "zh-CN"、"en-US"），与前端 i18next 一致
I18nDict = Dict[str, str]


def get_text(
    i18n_dict: Optional[I18nDict],
    default: str,
    lang: SupportedLang = SupportedLang.ZH_CN
) -> str:
    """获取国际化文本

    Args:
        i18n_dict: 国际化字典，可为 None
        default: 默认文本（向后兼容）
        lang: 目标语言

    Returns:
        本地化文本，如果无对应翻译则返回默认值
    """
    if not i18n_dict:
        return default
    return i18n_dict.get(lang, default)


def i18n_text(
    *,
    zh_CN: str,
    en_US: str,
) -> I18nDict:
    """创建国际化文本字典

    使用显式关键字参数，确保每个语言都清晰可见。
    函数名具有标志性，便于全局搜索 "i18n_text(" 找到所有使用点。

    添加新语言时:
    1. 在此函数添加新的关键字参数（如 ja_JP: str）
    2. 在返回字典中添加对应映射
    3. 所有调用点会因缺少必需参数而报类型错误
    4. 逐个为调用点补充新语言翻译

    Args:
        zh_CN: 简体中文文本
        en_US: 美式英文文本

    Returns:
        I18nDict 字典，键为语言代码字符串

    Example:
        >>> i18n_text(zh_CN="你好", en_US="Hello")
        {"zh-CN": "你好", "en-US": "Hello"}
    """
    return {
        SupportedLang.ZH_CN.value: zh_CN,
        SupportedLang.EN_US.value: en_US,
    }
```

### 3.2 统一错误类型系统

**新建文件**: `nekro_agent/schemas/errors.py`

```python
"""统一错误类型系统

设计原则:
1. 通过继承定义具体错误类型，类名即错误标识
2. 每个错误类自包含国际化消息模板
3. 支持参数化消息，如 "配置项 '{key}' 不存在"
4. HTTP 状态码由错误类决定，非路由决定

使用示例:
    # 定义错误
    class ConfigNotFoundError(AppError):
        http_status = 404
        i18n_message = i18n_text(
            zh_CN="配置项 '{key}' 不存在",
            en_US="Configuration '{key}' not found",
        )
        def __init__(self, key: str, **kwargs):
            super().__init__(key=key, **kwargs)

    # 抛出错误
    raise ConfigNotFoundError(key="USE_MODEL_GROUP")
"""

from typing import Any, ClassVar, Optional

from .i18n import I18nDict, SupportedLang, i18n_text


class AppError(Exception):
    """应用基础异常类

    所有业务错误都应继承此类，并定义:
    - http_status: HTTP 状态码
    - i18n_message: 国际化消息模板（支持 {param} 插值）

    Attributes:
        detail: 技术细节，用于日志和调试，不暴露给用户
        data: 附加数据，可选返回给前端
        params: 消息模板插值参数
    """

    http_status: ClassVar[int] = 500
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="服务器内部错误",
        en_US="Internal server error",
    )

    def __init__(
        self,
        detail: Optional[str] = None,
        data: Any = None,
        **params
    ):
        self.detail = detail
        self.data = data
        self.params = params
        super().__init__(self.get_message(SupportedLang.ZH_CN))

    @classmethod
    def get_error_name(cls) -> str:
        """获取错误名称（类名）"""
        return cls.__name__

    def get_message(self, lang: SupportedLang) -> str:
        """获取本地化错误消息"""
        template = self.i18n_message.get(lang) or self.i18n_message.get(
            SupportedLang.ZH_CN, "Unknown error"
        )
        try:
            return template.format(**self.params) if self.params else template
        except KeyError:
            return template

    def to_response(self, lang: SupportedLang) -> dict:
        """转换为 API 响应格式"""
        return {
            "error": self.get_error_name(),
            "message": self.get_message(lang),
            "detail": self.detail,
            "data": self.data,
        }


# ============================================================
# 通用错误
# ============================================================

class ValidationError(AppError):
    """请求参数验证失败"""
    http_status = 400
    i18n_message = i18n_text(
        zh_CN="请求参数无效: {reason}",
        en_US="Invalid request parameters: {reason}",
    )

    def __init__(self, reason: str, **kwargs):
        super().__init__(reason=reason, **kwargs)


class NotFoundError(AppError):
    """资源不存在"""
    http_status = 404
    i18n_message = i18n_text(
        zh_CN="{resource}不存在",
        en_US="{resource} not found",
    )

    def __init__(self, resource: str, **kwargs):
        super().__init__(resource=resource, **kwargs)


class ConflictError(AppError):
    """资源冲突"""
    http_status = 409
    i18n_message = i18n_text(
        zh_CN="{resource}已存在",
        en_US="{resource} already exists",
    )

    def __init__(self, resource: str, **kwargs):
        super().__init__(resource=resource, **kwargs)


class OperationFailedError(AppError):
    """操作失败（通用）"""
    http_status = 500
    i18n_message = i18n_text(
        zh_CN="{operation}失败",
        en_US="{operation} failed",
    )

    def __init__(self, operation: str, **kwargs):
        super().__init__(operation=operation, **kwargs)


# ============================================================
# 认证授权错误
# ============================================================

class UnauthorizedError(AppError):
    """未授权访问"""
    http_status = 401
    i18n_message = i18n_text(
        zh_CN="未授权访问",
        en_US="Unauthorized access",
    )


class TokenExpiredError(AppError):
    """Token 已过期"""
    http_status = 401
    i18n_message = i18n_text(
        zh_CN="登录已过期，请重新登录",
        en_US="Login expired, please login again",
    )


class PermissionDeniedError(AppError):
    """权限不足"""
    http_status = 403
    i18n_message = i18n_text(
        zh_CN="无权限执行此操作",
        en_US="Permission denied",
    )


class InvalidCredentialsError(AppError):
    """凭证无效"""
    http_status = 401
    i18n_message = i18n_text(
        zh_CN="用户名或密码错误",
        en_US="Invalid username or password",
    )


class TooManyAttemptsError(AppError):
    """尝试次数过多"""
    http_status = 429
    i18n_message = i18n_text(
        zh_CN="尝试次数过多，账户已被临时锁定",
        en_US="Too many attempts, account is temporarily locked",
    )


# ============================================================
# 配置相关错误
# ============================================================

class ConfigNotFoundError(AppError):
    """配置不存在"""
    http_status = 404
    i18n_message = i18n_text(
        zh_CN="配置项 '{key}' 不存在",
        en_US="Configuration '{key}' not found",
    )

    def __init__(self, key: str, **kwargs):
        super().__init__(key=key, **kwargs)


class ConfigInvalidError(AppError):
    """配置值无效"""
    http_status = 400
    i18n_message = i18n_text(
        zh_CN="配置项 '{key}' 的值无效: {reason}",
        en_US="Invalid value for configuration '{key}': {reason}",
    )

    def __init__(self, key: str, reason: str, **kwargs):
        super().__init__(key=key, reason=reason, **kwargs)


class ModelGroupNotFoundError(AppError):
    """模型组不存在"""
    http_status = 404
    i18n_message = i18n_text(
        zh_CN="模型组 '{name}' 不存在，请确认配置正确",
        en_US="Model group '{name}' not found, please check configuration",
    )

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)


class DefaultModelGroupDeleteError(AppError):
    """默认模型组不能删除"""
    http_status = 400
    i18n_message = i18n_text(
        zh_CN="默认模型组不能删除",
        en_US="Default model group cannot be deleted",
    )


# ============================================================
# 插件相关错误
# ============================================================

class PluginNotFoundError(AppError):
    """插件不存在"""
    http_status = 404
    i18n_message = i18n_text(
        zh_CN="插件 '{plugin_id}' 不存在",
        en_US="Plugin '{plugin_id}' not found",
    )

    def __init__(self, plugin_id: str, **kwargs):
        super().__init__(plugin_id=plugin_id, **kwargs)


class PluginLoadError(AppError):
    """插件加载失败"""
    http_status = 500
    i18n_message = i18n_text(
        zh_CN="插件 '{plugin_id}' 加载失败",
        en_US="Failed to load plugin '{plugin_id}'",
    )

    def __init__(self, plugin_id: str, **kwargs):
        super().__init__(plugin_id=plugin_id, **kwargs)


class PluginConfigError(AppError):
    """插件配置错误"""
    http_status = 400
    i18n_message = i18n_text(
        zh_CN="插件 '{plugin_id}' 配置错误: {reason}",
        en_US="Plugin '{plugin_id}' configuration error: {reason}",
    )

    def __init__(self, plugin_id: str, reason: str, **kwargs):
        super().__init__(plugin_id=plugin_id, reason=reason, **kwargs)


# ============================================================
# 空间清理相关错误
# ============================================================

class ScanNotStartedError(AppError):
    """扫描未启动"""
    http_status = 400
    i18n_message = i18n_text(
        zh_CN="暂无扫描结果，请先启动扫描",
        en_US="No scan result available, please start a scan first",
    )


class ScanFailedError(AppError):
    """扫描失败"""
    http_status = 500
    i18n_message = i18n_text(
        zh_CN="扫描失败",
        en_US="Scan failed",
    )


class CleanupTaskNotFoundError(AppError):
    """清理任务不存在"""
    http_status = 404
    i18n_message = i18n_text(
        zh_CN="清理任务不存在或未完成",
        en_US="Cleanup task not found or not completed",
    )


class CleanupFailedError(AppError):
    """清理失败"""
    http_status = 500
    i18n_message = i18n_text(
        zh_CN="清理失败",
        en_US="Cleanup failed",
    )


# ============================================================
# 聊天频道相关错误
# ============================================================

class ChannelNotFoundError(AppError):
    """聊天频道不存在"""
    http_status = 404
    i18n_message = i18n_text(
        zh_CN="聊天频道 '{chat_key}' 不存在",
        en_US="Chat channel '{chat_key}' not found",
    )

    def __init__(self, chat_key: str, **kwargs):
        super().__init__(chat_key=chat_key, **kwargs)


# ============================================================
# 文件操作相关错误
# ============================================================

class FileNotFoundError(AppError):
    """文件不存在"""
    http_status = 404
    i18n_message = i18n_text(
        zh_CN="文件 '{filename}' 不存在",
        en_US="File '{filename}' not found",
    )

    def __init__(self, filename: str, **kwargs):
        super().__init__(filename=filename, **kwargs)


class FileTooLargeError(AppError):
    """文件过大"""
    http_status = 413
    i18n_message = i18n_text(
        zh_CN="文件大小超过限制 ({limit}MB)",
        en_US="File size exceeds limit ({limit}MB)",
    )

    def __init__(self, limit: int, **kwargs):
        super().__init__(limit=limit, **kwargs)


class InvalidFileTypeError(AppError):
    """文件类型无效"""
    http_status = 400
    i18n_message = i18n_text(
        zh_CN="不支持的文件类型: {file_type}",
        en_US="Unsupported file type: {file_type}",
    )

    def __init__(self, file_type: str, **kwargs):
        super().__init__(file_type=file_type, **kwargs)


# ============================================================
# 高级功能错误
# ============================================================

class AdvancedCommandDisabledError(AppError):
    """高级命令未启用"""
    http_status = 403
    i18n_message = i18n_text(
        zh_CN="高级管理命令未启用，请在配置文件中启用",
        en_US="Advanced commands are disabled, please enable in configuration",
    )
```

### 3.3 全局异常处理器

**新建文件**: `nekro_agent/core/exception_handlers.py`

```python
"""全局异常处理器

核心职责:
1. 将所有异常统一转换为标准 HTTP 响应
2. 统一记录异常日志（路由中不需要 logger.exception）
3. 根据 Accept-Language 返回本地化消息
4. 提取请求上下文用于日志追踪
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from nekro_agent.schemas.errors import AppError, ValidationError
from nekro_agent.schemas.i18n import SupportedLang
from nekro_agent.core.logger import logger


def get_request_lang(request: Request) -> SupportedLang:
    """从请求头获取语言偏好"""
    accept_lang = request.headers.get("Accept-Language", "zh-CN")
    if accept_lang.lower().startswith("en"):
        return SupportedLang.EN_US
    return SupportedLang.ZH_CN


def get_request_context(request: Request) -> str:
    """提取请求上下文用于日志"""
    method = request.method
    path = request.url.path
    client = request.client.host if request.client else "unknown"
    return f"{method} {path} from {client}"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """处理应用自定义业务错误

    业务错误是预期内的，根据严重程度记录不同级别日志
    """
    lang = get_request_lang(request)
    ctx = get_request_context(request)

    if exc.http_status >= 500:
        # 500 级别：服务端错误，记录完整堆栈
        logger.exception(
            f"[{exc.get_error_name()}] {ctx} - {exc.detail or exc.get_message(lang)}"
        )
    elif exc.http_status >= 400:
        # 400 级别：客户端错误，只记录警告
        logger.warning(
            f"[{exc.get_error_name()}] {ctx} - {exc.get_message(lang)}"
        )

    return JSONResponse(
        status_code=exc.http_status,
        content=exc.to_response(lang),
    )


async def pydantic_validation_error_handler(
    request: Request,
    exc: PydanticValidationError
) -> JSONResponse:
    """处理 Pydantic 验证错误"""
    lang = get_request_lang(request)
    ctx = get_request_context(request)

    # 提取所有错误信息
    errors = exc.errors()
    error_details = []
    for err in errors:
        field = ".".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        error_details.append(f"{field}: {msg}" if field else msg)

    reason = "; ".join(error_details) if error_details else "Validation error"

    logger.warning(f"[ValidationError] {ctx} - {reason}")

    error = ValidationError(reason=reason)
    return JSONResponse(
        status_code=error.http_status,
        content=error.to_response(lang),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """处理 FastAPI/Starlette 原生 HTTPException

    兼容已有的 HTTPException 用法，逐步迁移到 AppError
    """
    lang = get_request_lang(request)
    ctx = get_request_context(request)

    logger.warning(f"[HTTPException] {ctx} - {exc.status_code}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "message": str(exc.detail),
            "detail": None,
            "data": None,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常

    这是最后的兜底，所有未被捕获的异常都会到这里
    必须记录完整堆栈，便于排查问题
    """
    lang = get_request_lang(request)
    ctx = get_request_context(request)

    # 记录完整异常堆栈 - 这是唯一需要 logger.exception 的地方
    logger.exception(f"[UnhandledException] {ctx} - {type(exc).__name__}: {exc}")

    error = AppError(detail=str(exc) if __debug__ else None)
    return JSONResponse(
        status_code=500,
        content=error.to_response(lang),
    )


def register_exception_handlers(app):
    """注册异常处理器到 FastAPI 应用

    处理器注册顺序很重要：
    1. 具体异常类型优先匹配
    2. Exception 作为最后兜底
    """
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
```

### 3.4 ExtraField i18n 扩展

**修改文件**: `nekro_agent/core/core_utils.py`

在 `ExtraField` 类中添加 i18n 字段：

```python
from nekro_agent.schemas.i18n import I18nDict

class ExtraField(BaseModel):
    """配置字段扩展元数据

    用于定义配置项在 WebUI 中的展示和行为
    """

    # === 原有字段保持不变 ===
    is_hidden: bool = Field(default=False, ...)
    is_secret: bool = Field(default=False, ...)
    placeholder: str = Field(default="", ...)
    is_textarea: bool = Field(default=False, ...)
    ref_model_groups: bool = Field(default=False, ...)
    model_type: Literal["chat", "embedding", "draw"] = Field(default="chat", ...)
    required: bool = Field(default=False, ...)
    overridable: bool = Field(default=False, ...)
    sub_item_name: str = Field(default="项目", ...)
    # ... 其他原有字段 ...

    # === 新增 i18n 字段 ===
    i18n_title: Optional[I18nDict] = Field(
        default=None,
        title="标题国际化",
        description="字段标题的多语言翻译，格式: {'zh-CN': '中文', 'en-US': 'English'}"
    )
    i18n_description: Optional[I18nDict] = Field(
        default=None,
        title="描述国际化",
        description="字段描述的多语言翻译"
    )
    i18n_placeholder: Optional[I18nDict] = Field(
        default=None,
        title="占位符国际化",
        description="占位符文本的多语言翻译"
    )
    i18n_sub_item_name: Optional[I18nDict] = Field(
        default=None,
        title="子项名称国际化",
        description="列表子项名称的多语言翻译"
    )
```

**配置项使用示例** (`nekro_agent/core/config.py`):

```python
from nekro_agent.schemas.i18n import i18n_text

class CoreConfig(ConfigBase):
    APP_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        title="应用日志级别",  # 默认值（向后兼容）
        description="应用日志级别，需要重启应用后生效",
        json_schema_extra=ExtraField(
            i18n_title=i18n_text(
                zh_CN="应用日志级别",
                en_US="Application Log Level",
            ),
            i18n_description=i18n_text(
                zh_CN="应用日志级别，需要重启应用后生效",
                en_US="Application log level, restart required to take effect",
            ),
        ).model_dump(),
    )
```

### 3.5 空间清理 ResourceCategory i18n 扩展

**修改文件**: `nekro_agent/schemas/space_cleanup.py`

```python
from nekro_agent.schemas.i18n import I18nDict

class ResourceCategory(BaseModel):
    """资源分类"""

    resource_type: ResourceType
    display_name: str  # 默认显示名（向后兼容）
    description: str   # 默认描述

    # === 新增 i18n 字段 ===
    i18n_display_name: Optional[I18nDict] = Field(
        default=None,
        description="显示名称的多语言翻译"
    )
    i18n_description: Optional[I18nDict] = Field(
        default=None,
        description="描述的多语言翻译"
    )
    i18n_risk_message: Optional[I18nDict] = Field(
        default=None,
        description="风险提示的多语言翻译"
    )

    # === 其他字段保持不变 ===
    total_size: int = Field(0, description="总大小（字节）")
    file_count: int = Field(0, description="文件数量")
    can_cleanup: bool = Field(True, description="是否可清理")
    risk_level: str = Field("safe", description="风险等级: safe/warning/danger")
    risk_message: Optional[str] = Field(None, description="风险提示（默认）")
    # ...
```

**Scanner 使用示例** (`nekro_agent/services/space_cleanup/scanner.py`):

```python
from nekro_agent.schemas.i18n import i18n_text

async def _scan_user_uploads(self) -> ResourceCategory:
    return ResourceCategory(
        resource_type=ResourceType.USER_UPLOADS,
        display_name="聊天上传资源",
        description="聊天中接收到的文件和图片等资源",
        i18n_display_name=i18n_text(
            zh_CN="聊天上传资源",
            en_US="Chat Upload Resources",
        ),
        i18n_description=i18n_text(
            zh_CN="聊天中接收到的文件和图片等资源",
            en_US="Files and images received in chat",
        ),
        risk_level="warning",
        risk_message="清理后AI将无法访问历史消息中的资源文件",
        i18n_risk_message=i18n_text(
            zh_CN="清理后AI将无法访问历史消息中的资源文件",
            en_US="AI will not be able to access files in historical messages after cleanup",
        ),
        # ...
    )
```

### 3.6 插件系统 i18n 扩展

**修改文件**: `nekro_agent/services/plugin/base.py`

```python
from nekro_agent.schemas.i18n import I18nDict, SupportedLang, get_text

class NekroPlugin:
    """Nekro 插件基类"""

    def __init__(
        self,
        name: str,
        module_name: str,
        description: str,
        version: str,
        author: str,
        url: str,
        # === 新增 i18n 参数 ===
        i18n_name: Optional[I18nDict] = None,
        i18n_description: Optional[I18nDict] = None,
        # === 其他参数保持不变 ===
        support_adapter: Optional[List[str]] = None,
        is_builtin: bool = False,
        is_package: bool = False,
    ):
        self.name = name
        self.description = description.strip()
        self.i18n_name = i18n_name
        self.i18n_description = i18n_description
        # ... 其他初始化 ...

    def get_name(self, lang: SupportedLang = SupportedLang.ZH_CN) -> str:
        """获取本地化插件名称"""
        return get_text(self.i18n_name, self.name, lang)

    def get_description(self, lang: SupportedLang = SupportedLang.ZH_CN) -> str:
        """获取本地化插件描述"""
        return get_text(self.i18n_description, self.description, lang)
```

**插件使用示例** (`plugins/builtin/basic.py`):

```python
from nekro_agent.schemas.i18n import i18n_text

plugin = NekroPlugin(
    name="基础交互插件",
    module_name="basic",
    description="提供基础的聊天消息发送、图片/文件资源发送等基础功能",
    i18n_name=i18n_text(
        zh_CN="基础交互插件",
        en_US="Basic Interaction Plugin",
    ),
    i18n_description=i18n_text(
        zh_CN="提供基础的聊天消息发送、图片/文件资源发送等基础功能",
        en_US="Provides basic chat messaging, image/file sending capabilities",
    ),
    version="0.1.1",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11", "minecraft", "sse", "discord", "wechatpad", "telegram"],
)
```

### 3.7 路由改造模式

#### 核心原则

1. **禁止宽泛 try-catch** - 错误由全局异常处理器统一处理
2. **禁止返回无约束字典** - 所有响应必须使用明确的 Pydantic 模型

**❌ 错误 - 返回字典**:
```python
async def start_scan() -> Dict[str, str]:
    return {"scan_id": scan_id}
```

**✅ 正确 - 返回 Pydantic 模型**:
```python
class ScanStartResponse(BaseModel):
    scan_id: str

async def start_scan() -> ScanStartResponse:
    return ScanStartResponse(scan_id=scan_id)
```

#### 禁止宽泛 try-catch

**❌ 错误示范 - 改造前**:

```python
@router.post("/scan/start")
async def start_scan(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    try:
        scan_id = await scanner_service.start_scan()
        return Ret.success(msg="扫描任务已启动", data={"scan_id": scan_id})
    except Exception as e:  # ❌ 宽泛捕获
        return Ret.error(msg=f"启动扫描失败: {e}")  # ❌ 吞掉异常
```

**❌ 错误示范 - 换了个方式继续错**:

```python
@router.post("/scan/start")
async def start_scan(...) -> ScanStartResponse:
    try:
        scan_id = await scanner_service.start_scan()
        return ScanStartResponse(scan_id=scan_id)
    except Exception as e:  # ❌ 还是宽泛捕获
        logger.exception(f"启动扫描失败: {e}")
        raise ScanFailedError(detail=str(e))  # ❌ 无意义的转换
```

**✅ 正确示范 - 直接返回，让全局处理器兜底**:

```python
from pydantic import BaseModel

class ScanStartResponse(BaseModel):
    """扫描启动响应"""
    scan_id: str

@router.post("/scan/start", response_model=ScanStartResponse)
async def start_scan(
    _current_user: DBUser = Depends(get_current_active_user)
) -> ScanStartResponse:
    """启动空间扫描任务"""
    scan_id = await scanner_service.start_scan()  # 直接调用，不捕获
    return ScanStartResponse(scan_id=scan_id)
```

**✅ 正确示范 - 只在需要特殊处理时捕获特定异常**:

```python
from nekro_agent.schemas.errors import ModelGroupNotFoundError

@router.get("/model-group/{name}")
async def get_model_group(name: str) -> ModelGroupResponse:
    """获取模型组配置

    只捕获需要转换为业务错误的特定异常
    """
    try:
        group = config.MODEL_GROUPS[name]  # 可能抛出 KeyError
    except KeyError:
        # ✅ 聚焦处理：只捕获 KeyError，转换为业务错误
        raise ModelGroupNotFoundError(name=name)

    return ModelGroupResponse.from_config(group)
```

**✅ 正确示范 - 服务层主动抛出业务错误**:

```python
# 服务层 (scanner_service.py)
async def start_scan(self) -> str:
    """启动扫描

    Raises:
        ScanFailedError: 扫描任务已在运行
    """
    if self._is_scanning:
        raise ScanFailedError(detail="Scan task is already running")

    # 正常逻辑...
    return scan_id

# 路由层 (space_cleanup.py)
@router.post("/scan/start")
async def start_scan(...) -> ScanStartResponse:
    """启动扫描 - 路由只负责调用和返回"""
    scan_id = await scanner_service.start_scan()
    return ScanStartResponse(scan_id=scan_id)
```

#### 何时捕获异常？

| 场景                   | 是否捕获 | 说明                                |
| ---------------------- | -------- | ----------------------------------- |
| 通用错误处理           | ❌ 禁止  | 让全局处理器处理                    |
| 转换底层异常为业务异常 | ✅ 允许  | 如 KeyError → NotFoundError         |
| 需要清理资源           | ✅ 允许  | 使用 try-finally 或 context manager |
| 重试逻辑               | ✅ 允许  | 捕获特定异常后重试                  |
| 部分失败允许继续       | ✅ 允许  | 如批量操作中单个失败                |

#### 关键变化

1. **移除 `Ret` 包装** - 直接返回数据模型
2. **移除宽泛 try-catch** - 由全局异常处理器统一处理
3. **服务层抛出业务异常** - 错误定义在服务层，路由层只传递
4. **全局处理器负责日志** - 路由中不需要 logger.exception

### 3.8 前端改造

#### 3.8.1 新增类型定义

**新建文件**: `frontend/src/services/api/types.ts`

```typescript
/**
 * 统一 API 类型定义
 */

// i18n 字典类型
export type I18nDict = {
  "zh-CN"?: string;
  "en-US"?: string;
};

// 错误响应类型
export interface ApiErrorResponse {
  error: string; // 错误类名，如 "ConfigNotFoundError"
  message: string; // 本地化错误消息
  detail?: string; // 技术细节（可选）
  data?: unknown; // 附加数据（可选）
}

// 获取本地化文本的工具函数
export function getLocalizedText(
  i18nDict: I18nDict | undefined,
  defaultText: string,
  lang: string = "zh-CN"
): string {
  if (!i18nDict) return defaultText;
  return i18nDict[lang as keyof I18nDict] || defaultText;
}
```

#### 3.8.2 改造 axios 拦截器

**修改文件**: `frontend/src/services/api/axios.ts`

```typescript
import axios, { AxiosError } from "axios";
import i18n from "../../config/i18n";
import { useAuthStore } from "../../stores/auth";
import { config } from "../../config/env";
import type { ApiErrorResponse } from "./types";

// 自定义 API 错误类
export class ApiError extends Error {
  constructor(
    public type: string, // 错误类型（后端类名）
    message: string, // 本地化消息
    public detail?: string, // 技术细节
    public data?: unknown // 附加数据
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const axiosInstance = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// 请求拦截器
axiosInstance.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // 添加语言头
  config.headers["Accept-Language"] = i18n.language;
  return config;
});

// 响应拦截器
axiosInstance.interceptors.response.use(
  // 成功响应：直接返回
  (response) => response,

  // 错误响应：统一处理
  async (error: AxiosError<ApiErrorResponse>) => {
    const { t } = i18n;

    // 网络错误
    if (!error.response) {
      if (error.message === "Network Error") {
        throw new ApiError("NetworkError", t("errors.networkError"));
      }
      throw new ApiError("UnknownError", error.message);
    }

    const { status, data } = error.response;

    // 401 未授权
    if (status === 401) {
      // 非登录接口的 401，执行登出
      if (!error.config?.url?.includes("/user/login")) {
        useAuthStore.getState().logout();
        window.location.href = "/#/login";
      }
      throw new ApiError(
        data?.error || "UnauthorizedError",
        data?.message || t("errors.unauthorized"),
        data?.detail
      );
    }

    // 其他错误：使用后端返回的本地化消息
    if (data?.error && data?.message) {
      throw new ApiError(data.error, data.message, data.detail, data.data);
    }

    // 兜底处理
    throw new ApiError("UnknownError", t("errors.serverError"), error.message);
  }
);

export default axiosInstance;
```

#### 3.8.3 添加前端错误翻译

**新建文件**: `frontend/src/locales/zh-CN/errors.json`

```json
{
  "networkError": "网络连接失败，请检查网络设置",
  "unauthorized": "未授权访问",
  "forbidden": "无权限执行此操作",
  "notFound": "资源不存在",
  "serverError": "服务器内部错误",
  "timeout": "请求超时，请稍后重试"
}
```

**新建文件**: `frontend/src/locales/en-US/errors.json`

```json
{
  "networkError": "Network connection failed, please check your network settings",
  "unauthorized": "Unauthorized access",
  "forbidden": "Permission denied",
  "notFound": "Resource not found",
  "serverError": "Internal server error",
  "timeout": "Request timeout, please try again later"
}
```

**更新 i18n 配置**，添加 errors 命名空间。

---

## 四、改造执行计划

### 4.1 阶段划分

> **注意**: 本次改造仅针对系统核心前后端，**适配器层暂不改造**（涉及大量外部接口对接，改造风险较大）

```
Phase 1: 基础设施 ✅ 已完成
├── 1.1 创建 nekro_agent/schemas/i18n.py ✅
├── 1.2 创建 nekro_agent/schemas/errors.py ✅
├── 1.3 创建 nekro_agent/core/exception_handlers.py ✅
├── 1.4 注册全局异常处理器到 FastAPI 应用 ✅
├── 1.5 前端添加 Accept-Language 请求头 ✅
├── 1.6 前端添加 ApiError 类和错误翻译文件 ✅
└── 1.7 验证基础设施正常工作 ✅

Phase 2: 试点模块改造 - 空间清理 ✅ 已完成
├── 2.1 扩展 ResourceCategory 添加 i18n 字段 ✅
├── 2.2 更新 scanner.py 中所有资源分类添加 i18n ✅
├── 2.3 改造 space_cleanup 路由（移除 Ret，移除宽泛 try-catch）✅
├── 2.4 服务层抛出具体业务异常 ✅
├── 2.5 更新前端 space-cleanup.tsx 使用新响应格式 ✅
├── 2.6 前端根据语言读取 i18n 字段 ✅
├── 2.7 清理前端 console 调用 ✅
└── 2.8 验证空间清理功能正常 ✅

Phase 3: 配置系统改造 ✅ 已完成
├── 3.1 扩展 ExtraField 添加 i18n_title 和 i18n_description 字段 ✅
├── 3.2 更新 CoreConfig 所有配置项添加 i18n（共54个配置项）✅
│   ├── Nekro Cloud 云服务配置（2项）✅
│   ├── 应用配置（8项）✅
│   ├── 模型组配置（3项）✅
│   ├── AI聊天配置（19项）✅
│   ├── 聊天设置（3项）✅
│   ├── 沙盒配置（5项）✅
│   ├── 邮件通知配置（7项）✅
│   ├── 插件配置（3项）✅
│   ├── Weave配置（2项）✅
│   └── 其他功能配置（2项）✅
├── 3.3 配置路由自动提取和返回 i18n 字段 ✅
├── 3.4 前端 ConfigItem 接口添加 i18n 字段 ✅
├── 3.5 前端 ConfigTable 组件使用 i18n 字段显示本地化文本 ✅
├── 3.6 前端实现语言切换无需刷新 ✅
├── 3.7 配置描述支持HTML链接（包含 target='_blank' 安全属性）✅
└── 3.8 验证配置功能正常（向后兼容第三方插件）✅

Phase 4: 插件系统改造 ✅ 已完成
├── 4.1 创建 nekro_agent/api/i18n.py 统一国际化 API 模块 ✅
├── 4.2 更新 nekro_agent/api/__init__.py 暴露 i18n 模块 ✅
├── 4.3 扩展 NekroPlugin 添加 i18n_name 和 i18n_description 参数 ✅
├── 4.4 更新 get_all_ext_meta_data 返回 i18n 字段 ✅
├── 4.5 为所有 19 个内置插件添加国际化 ✅
│   ├── basic.py - 基础交互插件 (5个配置项)
│   ├── dice.py - 掷骰姬
│   ├── email_utils.py - Email工具插件 (2个配置项)
│   ├── emotion.py - 表情包插件 (5个配置项)
│   ├── note.py - 笔记系统插件 (2个配置项)
│   ├── timer.py - 定时器工具集 (1个配置项)
│   ├── whiteboard.py - 直播白板演示插件 (5个配置项)
│   ├── ai_voice.py - AI语音插件 (1个配置项)
│   ├── status.py - 状态控制插件 (4个配置项)
│   ├── view_image.py - 查看图片 (1个配置项)
│   ├── google_search.py - Google搜索工具 (3个配置项)
│   ├── group_honor.py - 群荣誉插件
│   ├── history_travel.py - 漫游历史记录 (2个配置项)
│   ├── judgement.py - 风纪委员 (2个配置项)
│   ├── minecraft_utils.py - Minecraft工具插件
│   ├── bilibili_live_utils.py - Bilibili直播工具插件
│   ├── draw/plugin.py - 绘画插件 (9个配置项)
│   ├── github/plugin.py - GitHub消息推送 (1个配置项)
│   └── dynamic_importer.py - 动态pip导入工具
├── 4.6 前端 Plugin 接口添加 i18n 字段 ✅
├── 4.7 前端插件管理页面使用 getLocalizedText 显示本地化文本 ✅
├── 4.8 更新插件搜索和排序逻辑使用本地化文本 ✅
└── 4.9 验证插件国际化功能正常 ✅

统计: 插件总数 19 个，配置项总数 43 个，100% 完成国际化

Phase 5: 认证授权模块改造 ✅ 已完成
├── 5.1 改造 user 路由 ✅
├── 5.2 替换 http_exception.py 中的预定义异常 ✅
├── 5.3 更新 deps.py 中的权限检查 ✅
├── 5.4 更新前端登录相关页面 ✅
└── 5.5 验证认证流程正常 ✅

Phase 6: 全量核心路由改造 (预计 5-7 天)
├── 6.1 改造 dashboard 路由 ✅
├── 6.2 改造 chat_channel 路由 ✅
├── 6.3 改造 presets 路由 ✅
├── 6.4 改造 logs 路由 ✅
├── 6.5 改造 sandbox 路由 ✅
├── 6.6 改造 cloud/* 路由 (plugins_market, presets_market, auth, telemetry) ✅
├── 6.7 改造 common, restart, webhook 等其他核心路由 ✅
├── 6.8 同步更新前端相关页面 ✅
└── 6.9 全量功能验证 ⚠️（仅完成静态检查）
    ✅ adapters 路由已完成改造

Phase 7: 清理与文档 (预计 2-3 天)
├── 7.1 删除 Ret 类及相关代码 ✅
├── 7.2 运行迁移检查脚本确保无遗留 ✅
├── 7.3 更新 API 文档 ✅
├── 7.4 更新开发规范文档 ✅
└── 7.5 完成迁移验收 ⚠️（仅完成静态检查）

总计: 约 22-35 天
```

### 4.2 暂不改造内容（适配器层）

以下内容涉及大量外部接口对接，改造风险较大，**本次除 onebot_v11 外暂不处理**：

| 适配器目录                         | 问题类型           | 风险说明                             |
| ---------------------------------- | ------------------ | ------------------------------------ |
| `nekro_agent/adapters/email/`      | HTTPException, pass | 邮箱协议对接，稳定性优先             |
| `nekro_agent/adapters/onebot_v11/` | HTTPException       | QQ 机器人核心功能，已完成改造        |
| `nekro_agent/adapters/sse/`        | HTTPException       | 实时通信，错误处理逻辑特殊           |
| `nekro_agent/adapters/telegram/`   | -                   | 外部 API 对接                        |
| `nekro_agent/adapters/discord/`    | -                   | 外部 API 对接                        |
| `nekro_agent/adapters/wechatpad/`  | -                   | 微信协议对接，高风险                 |
| `nekro_agent/adapters/minecraft/`  | -                   | 游戏服务器对接                       |

**后续计划**: 待核心系统改造稳定后，可按剩余适配器逐个进行改造和测试。

### 4.3 每阶段详细任务

#### Phase 1: 基础设施

**任务 1.1**: 创建 `nekro_agent/schemas/i18n.py`

- 定义 `SupportedLang` 枚举
- 定义 `I18nDict` 类型别名
- 实现 `get_text()` 和 `i18n_text()` 工具函数

**任务 1.2**: 创建 `nekro_agent/schemas/errors.py`

- 实现 `AppError` 基类
- 定义所有错误子类（按模块分组）
- 每个错误类包含 `http_status` 和 `i18n_message`

**任务 1.3**: 创建 `nekro_agent/core/exception_handlers.py`

- 实现 `get_request_lang()` 函数
- 实现 `app_error_handler()` 处理器
- 实现 `generic_exception_handler()` 处理器
- 实现 `register_exception_handlers()` 注册函数

**任务 1.4**: 注册全局异常处理器

- 修改 `nekro_agent/api/app.py` 或应用入口
- 调用 `register_exception_handlers(app)`

**任务 1.5**: 前端添加 Accept-Language 请求头

- 修改 `frontend/src/services/api/axios.ts`
- 在请求拦截器中添加 `Accept-Language: {i18n.language}`

**任务 1.6**: 前端添加错误处理

- 创建 `frontend/src/services/api/types.ts`
- 创建 `frontend/src/locales/{zh-CN,en-US}/errors.json`
- 修改 axios 响应拦截器

**任务 1.7**: 验证

- 创建一个测试路由抛出 `AppError`
- 验证中英文消息正确返回
- 验证 HTTP 状态码正确

---

## 五、一次到位策略

### 5.1 彻底移除 Ret 类

**不保留兼容，直接删除**：

```python
# ❌ 删除 nekro_agent/schemas/message.py 中的 Ret 类
# 或者只保留作为历史参考，但禁止使用
```

**搜索并替换所有使用**：

```bash
# 查找所有使用 Ret 的地方
grep -r "from nekro_agent.schemas.message import Ret" --include="*.py"
grep -r "Ret.success\|Ret.fail\|Ret.error" --include="*.py"
grep -r "-> Ret" --include="*.py"
```

### 5.2 前端同步更新

**不需要兼容层**，直接修改所有 API 调用：

```typescript
// 改造前
const response = await axios.get<{ data: ConfigItem[] }>("/config/list");
return response.data.data; // 需要 .data.data

// 改造后
const response = await axios.get<ConfigItem[]>("/config/list");
return response.data; // 直接 .data
```

### 5.3 迁移检查清单（必须执行）

在每个阶段完成后，运行以下检查确保彻底迁移：

> **注意**: 检查范围仅包含核心路由 (`nekro_agent/routers/`)，不包含适配器层 (`nekro_agent/adapters/`)

```bash
# ========================================
# 后端检查（核心路由）
# ========================================

# 1. 确保核心路由没有遗留的 Ret 使用
grep -r "Ret\." nekro_agent/routers/ --include="*.py"
grep -r "from nekro_agent.schemas.message import Ret" nekro_agent/routers/ --include="*.py"
grep -r "-> Ret" nekro_agent/routers/ --include="*.py"

# 2. 确保核心路由中没有宽泛的 try-catch（关键检查！）
grep -rn "except Exception" nekro_agent/routers/ --include="*.py"
grep -rn "except:" nekro_agent/routers/ --include="*.py"

# 3. 确保核心路由中没有 logger.exception（应该在全局处理器中）
grep -rn "logger.exception" nekro_agent/routers/ --include="*.py"

# 4. 确保没有硬编码中文消息在核心路由中
grep -rn "msg=" nekro_agent/routers/ --include="*.py"

# 5. 确保错误类都继承自 AppError
grep -rn "class.*Error.*:" nekro_agent/schemas/errors.py

# ========================================
# 前端检查
# ========================================

# 6. 确保没有 .data.data 模式
grep -rn "\.data\.data" frontend/src/ --include="*.ts" --include="*.tsx"

# 7. 确保所有 API 调用都有错误处理或使用了 hook
grep -rn "catch" frontend/src/services/api/ --include="*.ts"

# 8. 确保使用了新的 ApiError 类
grep -rn "ApiError" frontend/src/services/api/ --include="*.ts"

# ========================================
# 适配器层（本次不检查，仅供参考）
# ========================================

# 适配器层 HTTPException 使用情况（暂不处理）
# grep -rn "raise HTTPException" nekro_agent/adapters/ --include="*.py"
```

**检查结果判定**:

- 检查 1-4: 结果为空才算通过（仅针对 `nekro_agent/routers/`）
- 检查 5: 确保所有错误类定义正确
- 检查 6: 结果为空才算通过
- 检查 7-8: 确保错误处理正确

---

## 六、编码原则与注意事项

### 6.1 错误处理原则（核心）

#### ❌ 禁止：宽泛的错误处理

```python
# ❌ 绝对禁止
try:
    result = await some_service()
except Exception as e:
    logger.exception(f"操作失败: {e}")
    raise SomeError(detail=str(e))

# ❌ 禁止：捕获后只记日志不处理
try:
    result = await some_service()
except Exception:
    logger.exception("出错了")
    pass  # 吞掉异常

# ❌ 禁止：捕获后返回默认值掩盖问题
try:
    result = await some_service()
except Exception:
    result = None  # 掩盖错误
```

#### ✅ 允许：聚焦的错误处理

```python
# ✅ 正确：转换特定异常为业务异常
try:
    config = self.configs[key]
except KeyError:
    raise ConfigNotFoundError(key=key)

# ✅ 正确：需要清理资源
async with aiofiles.open(path) as f:
    content = await f.read()

# ✅ 正确：部分失败允许继续
results = []
for item in items:
    try:
        result = await process(item)
        results.append(result)
    except ItemProcessError:
        # 单个失败不影响整体
        continue

# ✅ 正确：重试逻辑
for attempt in range(3):
    try:
        return await external_api()
    except TimeoutError:
        if attempt == 2:
            raise
        await asyncio.sleep(1)
```

### 6.2 日志记录原则

| 位置           | 是否记录日志 | 说明               |
| -------------- | ------------ | ------------------ |
| 路由层         | ❌ 否        | 全局处理器统一记录 |
| 服务层         | ⚠️ 视情况    | 只记录业务关键操作 |
| 全局异常处理器 | ✅ 是        | 统一记录所有异常   |

```python
# ❌ 路由中禁止
@router.post("/action")
async def action():
    try:
        await service.do()
    except Exception as e:
        logger.exception(f"失败: {e}")  # 禁止！
        raise

# ✅ 让全局处理器负责
@router.post("/action")
async def action():
    return await service.do()  # 直接调用，异常自动被全局处理器捕获并记录
```

### 6.3 代码规范

1. **所有错误类必须继承 `AppError`**
2. **每个错误类必须定义 `http_status` 和 `i18n_message`**
3. **参数化消息使用 `{param}` 占位符**
4. **使用 `i18n_text()` 创建翻译字典（显式关键字参数）**
5. **路由函数保持简洁，只负责参数校验和调用服务层**

### 6.4 测试要求

1. **每个错误类必须有单元测试**
2. **测试消息模板参数插值**
3. **测试中英文消息返回**
4. **测试 HTTP 状态码**
5. **测试全局异常处理器日志输出**

### 6.5 迁移顺序

1. **Phase 1**: 基础设施（i18n、errors、exception_handlers）
2. **Phase 2**: 试点模块（空间清理）验证方案
3. **Phase 3-6**: 按模块逐步改造
4. **Phase 7**: 清理删除旧代码

### 6.6 禁止事项清单

| 序号 | 禁止事项                       | 原因                   |
| ---- | ------------------------------ | ---------------------- |
| 1    | `except Exception` 宽泛捕获    | 掩盖问题，难以调试     |
| 2    | 路由中 `logger.exception()`    | 全局处理器负责         |
| 3    | `Ret.success/fail/error()`     | 已废弃，使用新模式     |
| 4    | 硬编码中文消息                 | 无法国际化             |
| 5    | 添加兼容层代码                 | 兼容层本身是技术债     |
| 6    | `response.data.data` 模式      | 旧响应格式             |
| 7    | 捕获异常后 `pass`              | 吞掉异常               |
| 8    | 捕获异常后返回默认值           | 掩盖错误               |
| 9    | 前端 `console.log/error/warn`  | 使用 logger 工具或移除 |
| 10   | `raise HTTPException` 直接使用 | 使用 `AppError` 子类   |
| 11   | `# type: ignore` 无注释        | 必须说明原因或修复     |

### 6.7 空 except pass 的正确处理

**❌ 错误示范**:

```python
try:
    imaplib.Commands["ID"] = ("AUTH", "SELECTED")
except Exception:
    pass  # 吞掉异常，无法排查问题
```

**✅ 正确做法**:

1. **如果真的需要忽略**，添加明确注释说明原因：

```python
try:
    imaplib.Commands["ID"] = ("AUTH", "SELECTED")
except Exception:
    # 忽略：ID 命令注册可能在某些 IMAP 库版本中已存在
    pass
```

2. **记录日志但继续执行**（推荐）：

```python
try:
    imaplib.Commands["ID"] = ("AUTH", "SELECTED")
except Exception as e:
    logger.debug(f"注册 IMAP ID 命令时出错（可忽略）: {e}")
```

3. **只捕获特定异常**：

```python
try:
    imaplib.Commands["ID"] = ("AUTH", "SELECTED")
except KeyError:
    # ID 命令已注册，忽略
    pass
```

### 6.8 前端 console 的正确处理

**❌ 错误示范**:

```typescript
catch (error) {
  console.error('获取云端插件列表失败:', error)  // 生产环境不应有
  throw error
}
```

**✅ 正确做法**:

1. **移除 catch 中的 console，让错误自然抛出**：

```typescript
// 不需要 try-catch，让调用方处理
const response = await axios.get("/api/plugins");
return response.data;
```

2. **如果需要转换错误，不要重复记录**：

```typescript
try {
  return await axios.get("/api/plugins");
} catch (error) {
  // 不记录 console，axios 拦截器已统一处理
  throw new Error("获取插件失败"); // 或者使用 ApiError
}
```

3. **调试时使用开发环境判断**：

```typescript
if (import.meta.env.DEV) {
  console.debug("Debug info:", data);
}
```

---

## 七、文件清单

### 7.1 新增文件

| 文件路径                                 | 说明           |
| ---------------------------------------- | -------------- |
| `nekro_agent/schemas/i18n.py`            | 国际化基础类型 |
| `nekro_agent/schemas/errors.py`          | 统一错误类型   |
| `nekro_agent/core/exception_handlers.py` | 全局异常处理器 |
| `frontend/src/services/api/types.ts`     | 前端 API 类型  |
| `frontend/src/locales/zh-CN/errors.json` | 中文错误翻译   |
| `frontend/src/locales/en-US/errors.json` | 英文错误翻译   |

### 7.2 需修改文件（详细清单）

#### 后端核心文件

| 文件路径                                        | 修改内容                   | Ret 调用数 |
| ----------------------------------------------- | -------------------------- | ---------- |
| `nekro_agent/schemas/message.py`                | 删除 Ret 类                | -          |
| `nekro_agent/schemas/http_exception.py`         | 删除，替换为 errors.py     | -          |
| `nekro_agent/routers/__init__.py`               | 替换全局异常处理器         | 1          |
| `nekro_agent/core/core_utils.py`                | ExtraField 添加 i18n 字段  | -          |
| `nekro_agent/core/config.py`                    | 配置项添加 i18n            | -          |
| `nekro_agent/schemas/space_cleanup.py`          | ResourceCategory 添加 i18n | -          |
| `nekro_agent/services/plugin/base.py`           | NekroPlugin 添加 i18n      | -          |
| `nekro_agent/services/space_cleanup/scanner.py` | 资源分类添加 i18n          | -          |

#### 后端路由文件（需移除 Ret 和宽泛 try-catch）

| 文件路径                                      | Ret 调用数 | 说明         | 改造状态 |
| --------------------------------------------- | ---------- | ------------ | -------- |
| `nekro_agent/routers/presets.py`              | 42         | 人设管理     | ✅ 已改造 |
| `nekro_agent/routers/cloud/plugins_market.py` | 38         | 云端插件市场 | ✅ 已改造 |
| `nekro_agent/routers/config.py`               | 32         | 配置管理     | ✅ 已改造 |
| `nekro_agent/routers/plugins.py`              | 31         | 插件管理     | ✅ 已改造 |
| `nekro_agent/routers/plugin_editor.py`        | 26         | 插件编辑器   | ✅ 已改造 |
| `nekro_agent/routers/space_cleanup.py`        | 23         | 空间清理     | ✅ 已改造 |
| `nekro_agent/routers/user_manager.py`         | 15         | 用户管理     | ✅ 已改造 |
| `nekro_agent/routers/adapters.py`             | 14         | 适配器管理   | ✅ 已改造 |
| `nekro_agent/routers/chat_channel.py`         | 11         | 聊天频道     | ✅ 已改造 |
| `nekro_agent/routers/cloud/presets_market.py` | 10         | 人设市场     | ✅ 已改造 |
| `nekro_agent/routers/common.py`               | 8          | 通用接口     | ✅ 已改造 |
| `nekro_agent/routers/user.py`                 | 7          | 用户认证     | ✅ 已改造 |
| `nekro_agent/routers/dashboard.py`            | 5          | 仪表盘       | ✅ 已改造 |
| `nekro_agent/routers/restart.py`              | 4          | 重启接口     | ✅ 已改造 |
| `nekro_agent/routers/cloud/auth.py`           | 3          | 云端认证     | ✅ 已改造 |
| `nekro_agent/routers/logs.py`                 | 2          | 日志接口     | ✅ 已改造 |
| `nekro_agent/routers/sandbox.py`              | 2          | 沙箱接口     | ✅ 已改造 |
| `nekro_agent/routers/cloud/telemetry.py`      | 2          | 遥测接口     | ✅ 已改造 |

#### 后端适配器文件（⏸️ 暂不改造）

> **风险说明**: 适配器层涉及大量与外部接口对接的实现，改造风险较大，本次暂不处理。待核心系统改造完成并稳定运行后，可作为独立任务逐个处理。

| 文件路径                                     | 问题类型                   | 说明        | 改造状态     |
| -------------------------------------------- | -------------------------- | ----------- | ------------ |
| `nekro_agent/adapters/email/adapter.py`      | except pass, HTTPException | 邮箱适配器  | ⏸️ 暂不改造 |
| `nekro_agent/adapters/email/routers.py`      | raise HTTPException        | 邮箱路由    | ⏸️ 暂不改造 |
| `nekro_agent/adapters/onebot_v11/routers.py` | raise HTTPException        | OneBot 路由 | ⏸️ 暂不改造 |
| `nekro_agent/adapters/sse/routers.py`        | raise HTTPException        | SSE 路由    | ⏸️ 暂不改造 |
| `nekro_agent/adapters/sse/commands.py`       | raise HTTPException        | SSE 命令    | ⏸️ 暂不改造 |

#### 前端 API 文件（需移除 .data.data 模式）

| 文件路径                                            | .data.data 数量 | 说明           |
| --------------------------------------------------- | --------------- | -------------- |
| `frontend/src/services/api/plugins.ts`              | 10              | 插件 API       |
| `frontend/src/services/api/space-cleanup.ts`        | 9               | 空间清理 API   |
| `frontend/src/services/api/unified-config.ts`       | 6               | 统一配置 API   |
| `frontend/src/services/api/config.ts`               | 5               | 配置 API       |
| `frontend/src/services/api/plugin-editor.ts`        | 5               | 插件编辑器 API |
| `frontend/src/services/api/adapters.ts`             | 4               | 适配器 API     |
| `frontend/src/services/api/dashboard.ts`            | 4               | 仪表盘 API     |
| `frontend/src/services/api/cloud/plugins_market.ts` | 4               | 云端插件 API   |
| `frontend/src/services/api/presets.ts`              | 3               | 人设 API       |
| `frontend/src/services/api/chat-channel.ts`         | 3               | 聊天频道 API   |
| `frontend/src/services/api/auth.ts`                 | 3               | 认证 API       |
| `frontend/src/services/api/sandbox.ts`              | 2               | 沙箱 API       |
| `frontend/src/services/api/logs.ts`                 | 2               | 日志 API       |
| `frontend/src/services/api/cloud/auth.ts`           | 2               | 云端认证 API   |
| 其他 API 文件                                       | 1-2             | -              |

#### 前端页面文件（需清理 console.log/error/warn）

| 文件路径                                         | console 调用数 | 说明         |
| ------------------------------------------------ | -------------- | ------------ |
| `frontend/src/pages/presets/index.tsx`           | 21             | 人设页面     |
| `frontend/src/pages/plugins/editor.tsx`          | 16             | 插件编辑器   |
| `frontend/src/pages/login/index.tsx`             | 9              | 登录页面     |
| `frontend/src/pages/adapter/onebot_v11/logs.tsx` | 8              | OneBot 日志  |
| `frontend/src/pages/cloud/plugins_market.tsx`    | 7              | 云端插件市场 |
| `frontend/src/pages/settings/theme.tsx`          | 7              | 主题设置     |
| `frontend/src/pages/logs/index.tsx`              | 5              | 日志页面     |
| `frontend/src/pages/settings/space-cleanup.tsx`  | 4              | 空间清理页面 |
| 其他页面文件                                     | 1-3            | -            |

#### 其他需处理的文件

| 文件路径                             | 问题                           | 说明       |
| ------------------------------------ | ------------------------------ | ---------- |
| `frontend/src/services/api/axios.ts` | 硬编码中文, 无 Accept-Language | 核心拦截器 |
| `frontend/src/theme/palette.ts`      | console.error                  | 主题加载   |
| `plugins/builtin/*.py`               | 无 i18n                        | 内置插件   |

### 7.3 需删除文件

| 文件路径                                | 原因             |
| --------------------------------------- | ---------------- |
| `nekro_agent/schemas/http_exception.py` | 替换为 errors.py |

---

## 八、验收标准

### 8.1 功能验收

> **验收范围**: 核心路由层 (`nekro_agent/routers/`)，不包含适配器层

- [ ] 核心 API 接口返回标准 HTTP 状态码
- [ ] 错误响应包含 `error`、`message` 字段
- [ ] 根据 `Accept-Language` 返回对应语言消息
- [ ] 配置项、插件、资源分类等支持多语言
- [ ] 前端能正确处理所有错误类型
- [ ] 核心路由中的 `Ret` 类已完全移除
- [ ] 适配器层保持原有实现不变（兼容性验证）

### 8.2 代码质量验收

- [ ] 所有新增代码通过 Ruff 检查
- [ ] 所有新增代码有完整类型注解
- [ ] 关键模块有单元测试
- [ ] 无硬编码用户可见中文字符串（除默认值外）
- [ ] 文档注释完整
- [ ] 核心路由中无宽泛 try-catch（通过迁移检查清单）
- [ ] 核心路由中无 logger.exception（由全局处理器负责）

### 8.3 性能验收

- [ ] 响应时间无明显增加
- [ ] 内存占用无明显增加

### 8.4 兼容性验收

- [ ] 适配器层功能正常（email、onebot_v11、sse 等）
- [ ] 适配器层错误处理保持原有行为
- [ ] 外部接口对接无异常

---

## 附录 A: 错误类型速查表

| 错误类                     | HTTP 状态码 | 使用场景         |
| -------------------------- | ----------- | ---------------- |
| `ValidationError`          | 400         | 请求参数验证失败 |
| `NotFoundError`            | 404         | 通用资源不存在   |
| `ConflictError`            | 409         | 资源已存在/冲突  |
| `UnauthorizedError`        | 401         | 未提供凭证       |
| `TokenExpiredError`        | 401         | Token 过期       |
| `InvalidCredentialsError`  | 401         | 凭证错误         |
| `PermissionDeniedError`    | 403         | 权限不足         |
| `TooManyAttemptsError`     | 429         | 请求过于频繁     |
| `ConfigNotFoundError`      | 404         | 配置项不存在     |
| `ConfigInvalidError`       | 400         | 配置值无效       |
| `ModelGroupNotFoundError`  | 404         | 模型组不存在     |
| `PluginNotFoundError`      | 404         | 插件不存在       |
| `PluginLoadError`          | 500         | 插件加载失败     |
| `ScanNotStartedError`      | 400         | 扫描未启动       |
| `ScanFailedError`          | 500         | 扫描失败         |
| `CleanupTaskNotFoundError` | 404         | 清理任务不存在   |
| `ChannelNotFoundError`     | 404         | 频道不存在       |
| `FileNotFoundError`        | 404         | 文件不存在       |
| `FileTooLargeError`        | 413         | 文件过大         |
| `OperationFailedError`     | 500         | 通用操作失败     |

---

## 附录 B: 快速参考

### 定义新错误类

```python
from nekro_agent.schemas.errors import AppError
from nekro_agent.schemas.i18n import i18n_text

class MyCustomError(AppError):
    """我的自定义错误"""
    http_status = 400
    i18n_message = i18n_text(
        zh_CN="操作 '{action}' 失败: {reason}",
        en_US="Operation '{action}' failed: {reason}",
    )

    def __init__(self, action: str, reason: str, **kwargs):
        super().__init__(action=action, reason=reason, **kwargs)
```

### 在路由中使用

```python
# ✅ 正确：路由保持简洁，不捕获异常
@router.post("/my-action")
async def my_action(data: MyRequest) -> MyResponse:
    result = await service.do_action(data)
    return MyResponse(result=result)

# ✅ 正确：只在需要转换特定异常时捕获
@router.get("/config/{key}")
async def get_config(key: str) -> ConfigResponse:
    try:
        value = config_dict[key]
    except KeyError:
        raise ConfigNotFoundError(key=key)
    return ConfigResponse(value=value)
```

### 在服务层抛出业务异常

```python
# 服务层负责业务逻辑和抛出业务异常
class MyService:
    async def do_action(self, data: MyRequest) -> Result:
        if not self.is_valid(data):
            raise MyCustomError(action="my_action", reason="Invalid data")

        # 正常业务逻辑，不捕获通用异常
        return await self.process(data)
```

### 添加配置项 i18n

```python
from nekro_agent.schemas.i18n import i18n_text

MY_CONFIG: str = Field(
    default="value",
    title="我的配置",
    description="这是我的配置描述",
    json_schema_extra=ExtraField(
        i18n_title=i18n_text(zh_CN="我的配置", en_US="My Config"),
        i18n_description=i18n_text(zh_CN="这是我的配置描述", en_US="This is my config description"),
    ).model_dump(),
)
```

### 前端读取 i18n 字段

```typescript
import { getLocalizedText } from "../services/api/types";
import { useTranslation } from "react-i18next";

function MyComponent({ category }: { category: ResourceCategory }) {
  const { i18n } = useTranslation();

  const displayName = getLocalizedText(
    category.i18n_display_name,
    category.display_name,
    i18n.language
  );

  return <div>{displayName}</div>;
}
```

---

## 附录 C: 错误处理对比速查（核心）

| 场景             | ❌ 错误做法                        | ✅ 正确做法                 |
| ---------------- | ---------------------------------- | --------------------------- |
| **普通路由**     | `try: ... except Exception: raise` | 直接调用，不捕获            |
| **日志记录**     | 路由中 `logger.exception()`        | 由全局处理器负责            |
| **错误返回**     | `return Ret.error(msg="...")`      | `raise SomeError()`         |
| **成功返回**     | `return Ret.success(data={...})`   | `return SomeResponse(...)`  |
| **特定异常转换** | `except Exception:`                | `except KeyError:` 只捕特定 |
| **业务错误**     | 路由中判断后返回                   | 服务层抛出 `AppError` 子类  |
| **兼容旧格式**   | 添加 if-else 判断                  | 一步到位，不做兼容          |

### 全局异常处理器职责

```
异常发生
    ↓
全局异常处理器捕获
    ↓
├── 判断异常类型
│   ├── AppError → 使用定义的 http_status 和 i18n_message
│   ├── ValidationError → 400 + 验证错误详情
│   └── Exception → 500 + logger.exception() 记录堆栈
    ↓
├── 读取 Accept-Language 头
├── 获取本地化消息
├── 记录日志（错误级别根据 http_status）
    ↓
返回 ErrorResponse JSON
```

---

**文档结束**
