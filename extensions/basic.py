import time
from typing import Optional

from nekro_agent.core import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
)
from nekro_agent.schemas.chat_channel import PresetStatus, channelData
from nekro_agent.services.chat import chat_service
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector
from nekro_agent.tools.common_util import (
    convert_file_name_to_container_path,
    download_file,
)

__meta__ = ExtMetaData(
    name="basic",
    description="Nekro-Agent 交互基础工具集",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)

# ========================================================================================
# |                              Nekro-Agent 交互基础工具集                                |
# ========================================================================================
#   扩展编写注意:
#     1. 所有注解会被 AI 引用时参考，请务必准确填写
#     2. _ctx: AgentCtx 中存储有关当前会话的上下文信息，不需要也不能加入到注释，以免误导 AI
#     3. _ctx 参数务必放在最后，以免因 AI 使用传递不规范导致错误
#     4. 如果需要在注解中编写应用示例等信息，务必不要体现 _ctx 的存在，并且使用 `同步调用` 的方式
#        (即不需要 `await func()` )，因为其实际执行是通过 rpc 进行的
# ========================================================================================


@agent_collector.mount_method(MethodType.TOOL)
async def send_msg_text(chat_key: str, message: str, _ctx: AgentCtx):
    """发送聊天消息文本

    Args:
        chat_key (str): 会话标识
        message (str): 消息内容
    """

    err_calling = [f"{m.__name__}" for m in agent_collector.get_all_methods()]
    for keyword in err_calling:
        if keyword in message:
            raise Exception(
                f"Incorrect usage of `{keyword}` in this message. If you need to call a method, please use in `script:>` response but not send it as a message.",
            )

    message_ = [AgentMessageSegment(content=message)]
    try:
        await chat_service.send_agent_message(chat_key, message_, _ctx, record=True)
    except Exception as e:
        raise Exception(f"Error sending text message to chat: {e}") from e


@agent_collector.mount_method(MethodType.TOOL)
async def send_msg_img(chat_key: str, file_path: str, _ctx: AgentCtx):
    """发送聊天消息图片资源 (支持资源格式: jpg, jpeg, png, gif, bmp; 不支持的格式请先转换)

    Args:
        chat_key (str): 会话标识
        file_path (str): 图片路径或 URL
    """
    message_ = [AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=file_path)]
    try:
        await chat_service.send_agent_message(chat_key, message_, _ctx, record=True)
    except Exception as e:
        raise Exception(f"Error sending image to chat: {e}") from e


@agent_collector.mount_method(MethodType.TOOL)
async def get_user_avatar(user_qq: str, _ctx: AgentCtx) -> str:
    """获取用户头像

    Args:
        user_qq (str): 用户 QQ 号

    Returns:
        str: 头像文件路径
    """
    try:
        file_path, file_name = await download_file(f"https://q1.qlogo.cn/g?b=qq&nk={user_qq}&s=640")
        return str(convert_file_name_to_container_path(file_name))
    except Exception as e:
        raise Exception(f"Error getting user avatar: {e}") from e


@agent_collector.mount_method(MethodType.BEHAVIOR)
async def update_preset_status(chat_key: str, setting_name: str, description: str, _ctx: AgentCtx) -> str:
    """更新人物设定状态

    **注意**: 你必须在**当且仅当**场景发展变化导致**不符合**当前设定状态时调用此方法来更新自身状态，但不能过度频繁使用，否则会丢失较早的状态记录!

    Args:
        chat_key (str): 会话标识
        setting_name (str): 新状态下的人设名
        description (str): 变化状态描述与原因 (推荐格式 "由于 [事件]，转变为 [新状态的详细描述] [且仍然...(旧状态仍有效的信息可选)]" **事件必须基于上下文进行总结描述尽可能详细地说明人物状态、外观、动作等信息，但如果上一状态中的某些信息依然有效，需要追加补充说明以免丢失信息**)

    Returns:
        str: 操作结果

    Example:
        > Since the number of context items is limited, when your dynamic setting state does not match the current scene, you need to call this method to update it.
        ```
        # 假设新状态下的人设名为 "正在认真看书的可洛喵" 并保持之前 "戴着帽子" 的状态
        update_preset_status(chat_key, "正在认真看书的可洛喵", "由于 ... 可洛喵 ... 转变为 `正在认真看书的可洛喵` 且仍然戴着帽子")
        ```
    """
    db_channel: DBChatChannel = DBChatChannel.get_channel(chat_key)
    channel_data: channelData = await db_channel.get_channel_data()
    before_status: Optional[PresetStatus] = channel_data.get_latest_preset_status()
    new_status = PresetStatus(setting_name=setting_name, description=description, translated_timestamp=int(time.time()))
    await channel_data.update_preset_status(new_status)
    db_channel.save_channel_data(channel_data)

    return (
        f"Preset status updated from `{before_status.setting_name}` to `{setting_name}`"
        if before_status
        else f"Preset status updated to {setting_name}"
    )
