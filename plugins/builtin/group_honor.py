"""
# 群荣誉 (Group Honor)

一个简单的群组管理插件，赋予 AI 在群聊中为用户设置"特殊头衔"的能力。

## 主要功能

- **设置头衔**: AI 可以根据与用户的互动情况（例如完成任务、达成成就等），调用工具为用户授予一个自定义的、有期限的特殊头衔（即 QQ 群中昵称前方的彩色称号）。
- **移除头衔**: 将头衔设置为空即可移除。

## 使用方法

此插件主要由 AI 在后台根据特定情况自动调用，例如，当用户在与 AI 的互动中表现出色时，AI 可能会决定授予其一个头衔作为奖励。
"""

from pydantic import Field

from nekro_agent.adapters.onebot_v11.core.bot import get_bot
from nekro_agent.api import core
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType

plugin = NekroPlugin(
    name="群荣誉插件",
    module_name="group_honor",
    description="提供群荣誉功能，支持设置用户特殊头衔",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11"],
)


@plugin.mount_config()
class GroupHonorConfig(ConfigBase):
    """群荣誉配置"""

    MAX_TITLE_LENGTH: int = Field(default=6, title="最大头衔长度")


# 获取配置
config = plugin.get_config(GroupHonorConfig)


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "赋予用户头衔称号")
async def set_user_special_title(_ctx: AgentCtx, chat_key: str, user_qq: str, special_title: str, days: int) -> bool:
    """赋予用户头衔称号

    Args:
        chat_key (str): 聊天的唯一标识符 (仅支持群组)
        user_qq (str): 用户 QQ 号
        special_title (str): 头衔 (不超过6个字符, 为空则移除头衔)
        days (int): 有效期/天

    Returns:
        bool: 操作是否成功
    """
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
    chat_type = db_chat_channel.chat_type
    chat_id = db_chat_channel.channel_id

    if chat_type != ChatType.GROUP:
        core.logger.error(f"不支持 {chat_type} 类型")
        return False

    # 检查头衔长度
    if len(special_title) > config.MAX_TITLE_LENGTH:
        core.logger.error(f"头衔长度超过限制 ({len(special_title)} > {config.MAX_TITLE_LENGTH})")
        return False

    try:
        await get_bot().call_api(
            "set_group_special_title",
            group_id=int(chat_id.split("_")[1]),
            user_id=int(user_qq),
            special_title=special_title,
            duration=days * 24 * 60 * 60,
        )
        core.logger.info(f"[{chat_key}] 已授予用户 {user_qq} 头衔 {special_title} {days} 天")

    except Exception as e:
        core.logger.error(f"[{chat_key}] 授予用户 {user_qq} 头衔 {special_title} {days} 天失败: {e}")
        return False
    else:
        return True


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
