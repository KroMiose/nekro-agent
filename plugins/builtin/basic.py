import difflib
import re
from typing import Dict, List

from pydantic import Field

from nekro_agent.api import message, user
from nekro_agent.api.core import logger
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

plugin = NekroPlugin(
    name="[NA] 基础交互插件",
    module_name="basic",
    description="提供基础的聊天消息发送、图片/文件资源发送、用户头像获取、图片观察工具等基础功能",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


# ========================================================================================
# |                              Nekro-Agent 交互基础工具集                                |
# ========================================================================================
#   插件编写注意:
#     1. 所有注解会被 AI 引用时参考，请务必准确填写
#     2. _ctx: AgentCtx 中存储有关当前会话的上下文信息，不需要且不能加入到注释，以免误导 AI
#     3. _ctx 参数务必放在第一个，否则会因为参数位置匹配错误导致调用失败
#     4. 如果需要在注解中编写应用示例等信息，务必不要体现 _ctx 的存在，并且使用 `同步调用` 的方式
#        (即不需要 `await func()` )，因为其实际执行是通过 rpc 在 Nekro-Agent 主服务进行的
#     5. `inject_prompt` 方法会在每次会话触发开始时调用一次，并将返回值注入到会话提示词中
#     6. 插件的清理方法 `clean_up` 会在插件卸载时自动调用，请在此方法中实现清理或重置逻辑
# ========================================================================================


@plugin.mount_config()
class BasicConfig(ConfigBase):
    """基础配置"""

    MY_CUSTOM_FIELD: str = Field(default="", title="插件自定义配置")


# 获取配置
config = plugin.get_config(BasicConfig)
config.MY_CUSTOM_FIELD = "test"


@plugin.mount_prompt_inject_method(name="basic_prompt_inject")
async def basic_prompt_inject(_ctx: AgentCtx):
    """基础提示注入"""
    return ""


def calculate_text_similarity(text1: str, text2: str) -> float:
    """计算两段文本的相似度

    Args:
        text1 (str): 第一段文本
        text2 (str): 第二段文本

    Returns:
        float: 相似度（0-1）
    """
    return difflib.SequenceMatcher(None, text1, text2).ratio()


SEND_MSG_CACHE: Dict[str, List[str]] = {}


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "发送聊天消息文本")
async def send_msg_text(_ctx: AgentCtx, chat_key: str, message_text: str):
    """发送聊天消息文本

    Args:
        chat_key (str): 会话标识
        message_text (str): 消息内容
    """
    global SEND_MSG_CACHE

    if not message_text.strip():
        raise Exception("Error: The message content cannot be empty.")

    message_text = message_text.replace("[@all@]", "@全体成员")

    # 拒绝包含 [image:xxx...] 的图片消息
    if re.match(r"^.*\[image:.*\]$", message_text) and len(message_text) > 100:
        raise Exception(
            "Error: You can't send image message directly, please use the send_msg_file method to send image/file resources.",
        )

    # 初始化消息缓存
    if chat_key not in SEND_MSG_CACHE:
        SEND_MSG_CACHE[chat_key] = []

    recent_messages = SEND_MSG_CACHE[chat_key][-5:] if SEND_MSG_CACHE[chat_key] else []

    # 检查完全匹配
    if message_text in recent_messages:
        # 清空缓存允许再次发送
        SEND_MSG_CACHE[chat_key] = []
        raise Exception(
            "Error: Identical message has been sent recently. Carefully read the recent chat history whether it has sent duplicate messages. If you determine it is necessary, you can resend it.",
        )

    # 检查相似度（仅对超过 12 字符的消息进行检查）
    if len(message_text) > 12:
        for recent_msg in recent_messages:
            similarity = calculate_text_similarity(message_text, recent_msg)
            if similarity > 0.7:
                # 发送系统消息提示避免类似内容
                logger.warning(f"[{chat_key}] 检测到相似度过高的消息: {similarity:.2f}")
                await message_service.push_system_message(
                    chat_key=chat_key,
                    agent_messages="System Alert: You have sent a message that is too similar to a recently sent message! You should KEEP YOUR RESPONSE USEFUL and not redundant and cumbersome!",
                    trigger_agent=False,
                )
                break

    try:
        await message.send_text(chat_key, message_text, _ctx)
    except Exception as e:
        raise Exception(
            "Error sending text message to chat: Make sure the chat key is valid, you have permission to speak and message is not too long.",
        ) from e

    # 更新消息缓存
    SEND_MSG_CACHE[chat_key].append(message_text)
    SEND_MSG_CACHE[chat_key] = SEND_MSG_CACHE[chat_key][-10:]  # 保持最近10条消息


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "发送聊天消息图片/文件资源")
async def send_msg_file(_ctx: AgentCtx, chat_key: str, file_path: str):
    """发送聊天消息图片/文件资源

    Args:
        chat_key (str): 会话标识
        file_path (str): 图片/文件路径或 URL
    """
    try:
        suf = file_path.split(".")[-1]
        if suf in ["jpg", "jpeg", "png", "gif", "webp"]:
            await message.send_image(chat_key, file_path, _ctx)
        else:
            await message.send_file(chat_key, file_path, _ctx)
    except Exception as e:
        raise Exception(f"Error sending file to chat: {e}") from e


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "获取用户头像")
async def get_user_avatar(_ctx: AgentCtx, user_qq: str) -> str:
    """获取用户头像

    Args:
        user_qq (str): 用户 QQ 号

    Returns:
        str: 头像文件路径
    """
    try:
        return await user.get_avatar(user_qq, _ctx)
    except Exception as e:
        raise Exception(f"Error getting user avatar: {e}") from e

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
    global SEND_MSG_CACHE
    SEND_MSG_CACHE = {}
