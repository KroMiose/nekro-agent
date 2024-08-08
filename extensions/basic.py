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
#        (即不需要 `await func()` )，因为其实际执行是通过 rpc 进行的
# ========================================================================================


@agent_collector.mount_method(MethodType.TOOL)
async def send_msg_text(chat_key: str, message: str, _ctx: AgentCtx) -> bool:
    """发送聊天消息文本

    Args:
        chat_key (str): 会话标识
        message (str): 消息内容

    Returns:
        bool: 是否发送成功
    """
    try:
        message_ = [AgentMessageSegment(content=message)]
        await chat_service.send_agent_message(chat_key, message_, _ctx, record=True)
    except Exception as e:
        logger.exception(f"Error sending message to chat: {e}")
        return False
    else:
        return True


@agent_collector.mount_method(MethodType.TOOL)
async def send_msg_img(chat_key: str, file_path: str, _ctx: AgentCtx) -> bool:
    """发送聊天消息图片资源 (支持资源格式: jpg, jpeg, png, gif, bmp; 不支持的格式请先转换)

    Args:
        chat_key (str): 会话标识
        file_path (str): 图片路径或 URL

    Returns:
        bool: 是否发送成功
    """
    try:
        message_ = [AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=file_path)]
        await chat_service.send_agent_message(chat_key, message_, _ctx, record=True)
    except Exception as e:
        logger.exception(f"Error sending message to chat: {e}")
        return False
    else:
        return True


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
