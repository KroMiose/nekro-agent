"""Nekro-Agent API

此包提供了 Nekro-Agent 的公共 API 接口，用于扩展开发。

Example:
    ```python
    from nekro_agent.api import message, timer, user, context, core, llm, i18n
    from nekro_agent.api.plugin import NekroPlugin, ExtraField

    # 发送消息
    await message.send_text(_ck, "你好，世界！", ctx)

    # 设置定时器
    await timer.set_timer(_ck, int(time.time()) + 300, "提醒吃早餐", ctx)

    # 使用核心功能
    core.logger.info("这是一条日志")

    # 创建国际化插件
    plugin = NekroPlugin(
        name="我的插件",
        module_name="my_plugin",
        description="描述",
        i18n_name=i18n.i18n_text(zh_CN="我的插件", en_US="My Plugin"),
        i18n_description=i18n.i18n_text(zh_CN="描述", en_US="Description"),
    )
    ```
"""

from nekro_agent.api import core, i18n, message, plugin, schemas, signal, timer

__all__ = [
    "core",
    "i18n",
    "message",
    "plugin",
    "schemas",
    "signal",
    "timer",
]
