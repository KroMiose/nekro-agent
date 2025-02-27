"""
仅供上架 NoneBot 商城检查使用，移除所有功能
"""

from nonebot import get_driver
from nonebot.plugin import PluginMetadata
from pydantic import BaseModel


class _Config(BaseModel):
    pass


__plugin_meta__ = PluginMetadata(
    name="nekro-agent",
    description="集代码执行/高扩展性为一体的聊天机器人，应用了容器化技术快速构建沙盒 Agent 执行环境",
    usage="",
    type="application",
    homepage="https://github.com/KroMiose/nekro-agent",
    supported_adapters={"~onebot.v11"},
    config=_Config,
)

global_config = get_driver().config
