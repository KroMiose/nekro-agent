from typing import Dict, List, Optional

from nekro_agent.core import logger
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
)
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
#        (即不需要 `await func()` )，因为其实际执行是通过 rpc 在 Nekro-Agent 主服务进行的
# ========================================================================================


SEND_MSG_CACHE: Dict[str, List[str]] = {}


@agent_collector.mount_method(MethodType.TOOL)
async def send_msg_text(chat_key: str, message: str, _ctx: AgentCtx):
    """发送聊天消息文本

    Args:
        chat_key (str): 会话标识
        message (str): 消息内容
    """
    global SEND_MSG_CACHE

    if message in SEND_MSG_CACHE.get(_ctx.from_chat_key, []):
        return

    message_ = [AgentMessageSegment(content=message)]
    try:
        await chat_service.send_agent_message(chat_key, message_, _ctx, record=True)
    except Exception as e:
        raise Exception(f"Error sending text message to chat: {e}") from e

    if _ctx.from_chat_key not in SEND_MSG_CACHE:
        SEND_MSG_CACHE[_ctx.from_chat_key] = []

    SEND_MSG_CACHE[_ctx.from_chat_key].append(message)
    SEND_MSG_CACHE[_ctx.from_chat_key] = SEND_MSG_CACHE[_ctx.from_chat_key][-10:]


@agent_collector.mount_method(MethodType.TOOL)
async def send_msg_file(chat_key: str, file_path: str, _ctx: AgentCtx):
    """发送聊天消息图片/文件资源

    Args:
        chat_key (str): 会话标识
        file_path (str): 图片/文件路径或 URL
    """
    message_ = [AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=file_path)]
    try:
        suf = file_path.split(".")[-1]
        if suf in ["jpg", "jpeg", "png", "gif", "webp"]:
            await chat_service.send_agent_message(chat_key, message_, _ctx, record=True)
        else:
            await chat_service.send_agent_message(chat_key, message_, _ctx, file_mode=True, record=True)

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
        file_path, file_name = await download_file(
            f"https://q1.qlogo.cn/g?b=qq&nk={user_qq}&s=640",
            from_chat_key=_ctx.from_chat_key,
        )
        return str(convert_file_name_to_container_path(file_name))
    except Exception as e:
        raise Exception(f"Error getting user avatar: {e}") from e
