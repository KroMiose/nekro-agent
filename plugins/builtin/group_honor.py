"""
# 群荣誉 (Group Honor)

一个简单的群组管理插件，赋予 AI 在群聊中为用户设置"特殊头衔"的能力。

## 主要功能

- **设置头衔**: AI 可以根据与用户的互动情况（例如完成任务、达成成就等），调用工具为用户授予一个自定义的、有期限的特殊头衔（即 QQ 群中昵称前方的彩色称号）。
- **移除头衔**: 将头衔设置为空即可移除。

## 使用方法

此插件主要由 AI 在后台根据特定情况自动调用，例如，当用户在与 AI 的互动中表现出色时，AI 可能会决定授予其一个头衔作为奖励。
"""

from typing import List

from pydantic import Field

from nekro_agent.adapters.onebot_v11.core.bot import get_bot
from nekro_agent.api import core, i18n
from nekro_agent.api.plugin import (
    ConfigBase,
    ExtraField,
    NekroPlugin,
    SandboxMethodType,
)
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType

plugin = NekroPlugin(
    name="群荣誉插件",
    module_name="group_honor",
    description="提供群荣誉功能，支持设置用户群组头衔",
    version="0.2.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11"],
    i18n_name=i18n.i18n_text(
        zh_CN="群荣誉插件",
        en_US="Group Honor Plugin",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="提供群荣誉功能，支持设置用户群组头衔",
        en_US="Provides group honor features for setting user group titles",
    ),
)


@plugin.mount_config()
class GroupHonorConfig(ConfigBase):
    """群荣誉配置"""

    MAX_TITLE_LENGTH: int = Field(default=6, title="最大头衔长度")
    ALLOW_GROUPS: List[str] = Field(
        default=[],
        title="允许使用头衔管理功能的群组列表",
        description="如果为空，则允许所有群组使用头衔管理功能",
        json_schema_extra=ExtraField(sub_item_name="群组").model_dump(),
    )
    PROTECTED_USER_IDS: List[str] = Field(
        default=[],
        title="受保护的用户 QQ 列表",
        description="受保护的用户无法被授予头衔",
        json_schema_extra=ExtraField(sub_item_name="QQ").model_dump(),
    )
    BLOCK_KEYWORDS: List[str] = Field(
        default=["管理员", "群主"],
        title="禁止使用的关键词",
        json_schema_extra=ExtraField(sub_item_name="关键词").model_dump(),
    )


# 获取配置
config = plugin.get_config(GroupHonorConfig)


@plugin.mount_prompt_inject_method(name="group_honor_prompt_inject")
async def group_honor_prompt_inject(_ctx: AgentCtx):
    """群荣誉提示注入"""

    if len(config.ALLOW_GROUPS) == 0:
        return "状态: 群头衔管理功能在当前聊天可用"

    group_id = _ctx.chat_key.split("_")[1]
    if group_id in config.ALLOW_GROUPS:
        return "状态: 群头衔管理功能在当前聊天可用"

    return "状态: 群头衔管理功能在当前聊天不可用"


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

    if user_qq in config.PROTECTED_USER_IDS:
        raise ValueError("用户头衔受保护，无法变更")

    for keyword in config.BLOCK_KEYWORDS:
        if keyword in special_title:
            raise ValueError(f"头衔中包含禁止使用的关键词: {keyword}")

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


@plugin.mount_collect_methods()
async def collect_available_methods(_ctx: AgentCtx):
    """根据适配器收集可用方法"""

    if len(config.ALLOW_GROUPS) == 0:
        return [set_user_special_title]

    group_id = _ctx.chat_key.split("_")[1]
    if group_id in config.ALLOW_GROUPS:
        return [set_user_special_title]

    return []


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
