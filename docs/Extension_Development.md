# Nekro-Agent 扩展开发指南

## 目录

- [概述](#概述)
- [扩展结构](#扩展结构)
- [API 参考](#api-参考)
- [核心 API](#核心-api)
- [消息 API](#消息-api)
- [定时器 API](#定时器-api)
- [上下文 API](#上下文-api)
- [用户 API](#用户-api)

## 概述

Nekro-Agent 提供了一套完整的扩展开发 API，允许开发者编写自定义扩展来扩展 Agent 的功能。本文档将详细介绍如何开发一个扩展。

## 扩展结构

一个典型的扩展文件结构如下：

```python
from nekro_agent.api import core, message, timer, context, user
from nekro_agent.api.schemas import AgentCtx

__meta__ = core.ExtMetaData(
    name="your_extension",
    description="扩展描述",
    version="0.1.0",
    author="作者",
    url="项目地址",
)

@core.agent_collector.mount_method(core.MethodType.TOOL)
async def your_function(param1: str, param2: int, _ctx: AgentCtx):
    """函数描述

    Args:
        param1 (str): 参数1描述
        param2 (int): 参数2描述
    """
    # 实现你的功能
    pass

async def clean_up():
    """清理扩展 (模块卸载时调用，用于重置全局变量等状态信息)"""
    pass
```

### 扩展注意事项

1. 所有注解会被 AI 引用时参考，请务必准确填写
2. `_ctx: AgentCtx` 中存储有关当前会话的上下文信息，不需要也不能加入到注释，以免误导 AI
3. `_ctx` 参数务必放在最后，以免因 AI 使用传递不规范导致错误
4. 如果需要在注解中编写应用示例等信息，务必不要体现 `_ctx` 的存在，并且使用同步调用的方式
   (即不需要 `await func()`)，因为其实际执行是通过 rpc 在 Nekro-Agent 主服务进行的

## API 参考

### 核心 API

```python
from nekro_agent.api import core
```

核心 API 提供了基础的功能支持：

- `core.ExtMetaData`: 扩展元数据类，用于定义扩展的基本信息
- `core.MethodType`: 方法类型枚举
  - `TOOL`: 工具方法，可被 AI 直接调用，返回结果会通过 RPC 返回给沙盒且允许 AI 获取结果继续处理
  - `AGENT`: Agent 方法，用于实现 Agent 的行为，返回 str (行为执行结果) 同时阻断程序运行并再触发一次新的回复流
  - `BEHAVIOR`: 行为方法，用于执行特定的行为，返回 str (行为执行结果) 会被加入上下文参考
- `core.agent_collector`: 方法收集器，用于注册扩展方法
- `core.logger`: 日志记录器
- `core.config`: 配置访问器
- `core.get_bot()`: 获取机器人实例

### 消息 API

```python
from nekro_agent.api import message
```

消息 API 提供了消息发送相关的功能：

#### send_text

```python
async def send_text(chat_key: str, message: str, ctx: AgentCtx, *, record: bool = True) -> None:
    """发送文本消息

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
        message (str): 要发送的文本消息
        record (bool, optional): 是否记录到上下文。默认为 True
    """
```

#### send_image

```python
async def send_image(chat_key: str, image_path: str, ctx: AgentCtx, *, record: bool = True) -> None:
    """发送图片消息

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
        image_path (str): 图片路径或URL
        record (bool, optional): 是否记录到上下文。默认为 True
    """
```

#### send_file

```python
async def send_file(chat_key: str, file_path: str, ctx: AgentCtx, *, record: bool = True) -> None:
    """发送文件消息

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
        file_path (str): 文件路径或URL
        record (bool, optional): 是否记录到上下文。默认为 True
    """
```

#### download_from_url

```python
async def download_from_url(url: str, ctx: AgentCtx) -> str:
    """从URL下载文件

    Args:
        url (str): 文件URL

    Returns:
        str: 下载后的文件路径
    """
```

### 定时器 API

```python
from nekro_agent.api import timer
```

定时器 API 提供了定时触发自身回复流程相关的功能：

#### set_timer

```python
async def set_timer(chat_key: str, trigger_time: int, event_desc: str) -> bool:
    """设置一个定时器

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
        trigger_time (int): 触发时间戳
        event_desc (str): 事件描述（详细描述事件的 context 信息，触发时提供参考）

    Returns:
        bool: 是否设置成功
    """
```

#### set_temp_timer

```python
async def set_temp_timer(chat_key: str, trigger_time: int, event_desc: str) -> bool:
    """设置一个临时定时器（用于短期自我唤醒检查新消息，同一会话只会保留最后一个临时定时器）

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
        trigger_time (int): 触发时间戳
        event_desc (str): 事件描述（详细描述事件的 context 信息，触发时提供参考）

    Returns:
        bool: 是否设置成功
    """
```

#### clear_timers

```python
async def clear_timers(chat_key: str) -> bool:
    """清空指定会话的所有定时器

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"

    Returns:
        bool: 是否清空成功
    """
```

### 上下文 API

```python
from nekro_agent.api import context
```

上下文 API 提供了会话上下文相关的功能：

#### parse_chat_key

```python
def parse_chat_key(chat_key: str) -> Tuple[str, str]:
    """解析会话标识

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"

    Returns:
        Tuple[str, str]: (会话类型, 会话ID)
    """
```

#### get_chat_type

```python
def get_chat_type(chat_key: str) -> str:
    """获取会话类型

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"

    Returns:
        str: 会话类型
    """
```

#### get_chat_id

```python
def get_chat_id(chat_key: str) -> str:
    """获取会话ID

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"

    Returns:
        str: 会话ID
    """
```

### 用户 API

```python
from nekro_agent.api import user
```

用户 API 提供了用户相关的功能：

#### get_avatar

```python
async def get_avatar(user_qq: str, ctx: AgentCtx) -> str:
    """获取用户头像

    Args:
        user_qq (str): 用户QQ号

    Returns:
        str: 头像文件路径
    """
```

## 最佳实践

1. **类型安全**

   - 使用类型注解
   - 使用 `AgentCtx` 类型作为上下文参数

2. **错误处理**

   - 合理使用 try-except 处理可能的异常
   - 提供有意义的错误信息

3. **文档规范**

   - 为每个函数提供详细的文档字符串
   - 包含参数说明和返回值说明
   - 提供使用示例

4. **代码组织**

   - 相关功能放在同一个扩展中
   - 使用合适的 MethodType 标注函数用途

5. **性能考虑**
   - 避免阻塞操作
   - 合理使用异步编程

## 示例扩展

这里是一个完整的示例扩展，展示了如何使用各种 API：

```python
from nekro_agent.api import core, message, timer, context, user
from nekro_agent.api.schemas import AgentCtx

__meta__ = core.ExtMetaData(
    name="example",
    description="示例扩展",
    version="0.1.0",
    author="Your Name",
    url="https://github.com/yourusername/your-repo",
)

@core.agent_collector.mount_method(core.MethodType.TOOL)
async def send_welcome(chat_key: str, user_qq: str, _ctx: AgentCtx):
    """发送欢迎消息并设置提醒

    Args:
        chat_key (str): 会话标识
        user_qq (str): 用户QQ号
    """
    try:
        # 获取用户头像
        avatar_path = await user.get_avatar(user_qq, _ctx)

        # 发送欢迎消息
        await message.send_text(
            chat_key,
            f"欢迎新成员！",
            _ctx
        )

        # 发送用户头像
        await message.send_image(
            chat_key,
            avatar_path,
            _ctx
        )

        # 设置5分钟后的提醒
        import time
        await timer.set_timer(
            chat_key,
            int(time.time()) + 300,
            f"提醒新成员 {user_qq} 查看群规"
        )

    except Exception as e:
        core.logger.error(f"发送欢迎消息失败: {e}")
        return False

    return True
```

## 注意事项

1. 扩展开发时需要注意以下几点：

   - 所有的扩展方法都应该是异步的（使用 `async def`）
   - 扩展方法的最后一个参数必须是 `_ctx: AgentCtx`
   - 在文档字符串中不要提及 `_ctx` 参数
   - 示例代码中不要体现 `await`

2. 安全性考虑：

   - 不要在扩展中存储敏感信息
   - 谨慎处理用户输入
   - 合理使用权限检查

3. 性能优化：

   - 避免过度频繁的 API 调用
   - 合理使用缓存机制
   - 注意资源释放

4. 代码质量：
   - 遵循 PEP 8 编码规范
   - 保持代码简洁清晰

## 调试技巧

1. 使用 `core.logger` 输出调试信息：

```python
core.logger.debug("调试信息")
core.logger.info("普通信息")
core.logger.warning("警告信息")
core.logger.error("错误信息")
```

2. 使用 `/exec` 命令测试方法：

   - 直接使用管理员账号发送 `/exec 方法名(参数)` 即可在沙盒中运行代码段实现测试方法

3. 错误排查：
   - 检查 API 调用参数
   - 查看日志输出
   - 验证返回值

## 更多资源

- [项目 GitHub 仓库](https://github.com/KroMiose/nekro-agent)
- [问题反馈](https://github.com/KroMiose/nekro-agent/issues)
