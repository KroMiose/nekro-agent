from nekro_agent.api import context, core
from nekro_agent.api.schemas import AgentCtx

__meta__ = core.ExtMetaData(
    name="group_honor",
    description="[NA] 群荣誉",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@core.agent_collector.mount_method(core.MethodType.TOOL)
async def set_user_special_title(chat_key: str, user_qq: str, special_title: str, days: int, _ctx: AgentCtx) -> bool:
    """赋予用户头衔称号

    Args:
        chat_key (str): 聊天的唯一标识符 (仅支持群组)
        user_qq (str): 用户 QQ 号
        special_title (str): 头衔 (不超过6个字符, 为空则移除头衔)
        days (int): 有效期/天

    Returns:
        bool: 操作是否成功
    """
    chat_type = context.get_chat_type(chat_key)
    chat_id = context.get_chat_id(chat_key)

    if chat_type != "group":
        core.logger.error(f"不支持 {chat_type} 类型")
        return False

    try:
        await core.get_bot().call_api(
            "set_group_special_title",
            group_id=int(chat_id),
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


async def clean_up():
    """清理扩展"""
