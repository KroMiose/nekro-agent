"""Nekro-Agent API

此包提供了 Nekro-Agent 的公共 API 接口，用于扩展开发。

Example:
    ```python
    from nekro_agent.api import message, timer, user, context, core, llm

    # 发送消息
    await message.send_text("group_123456", "你好，世界！", ctx)

    # 设置定时器
    await timer.set_timer("group_123456", int(time.time()) + 300, "提醒吃早餐", ctx)

    # 获取用户头像
    avatar_path = await user.get_avatar("123456789", ctx)

    # 解析会话标识
    chat_type, chat_id = context.parse_chat_key("group_123456")

    # 使用核心功能
    core.logger.info("这是一条日志")

    # 使用 LLM 模型
    response = await llm.get_chat_response([
        {"role": "user", "content": "你好，请帮我写一首诗"}
    ])
    ```
"""

from nekro_agent.api import context, core, message, plugin, schemas, timer, user

__all__ = [
    "context",
    "core",
    "message",
    "plugin",
    "schemas",
    "timer",
    "user",
]
