import difflib
import hashlib
import re
from pathlib import Path
from typing import Dict, List

import aiofiles
import magic
from pydantic import Field

from nekro_agent.api import message, user
from nekro_agent.api.core import logger
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.tools.common_util import download_file
from nekro_agent.tools.path_convertor import (
    convert_to_container_path,
    convert_to_host_path,
    is_url_path,
)

plugin = NekroPlugin(
    name="基础交互插件",
    module_name="basic",
    description="提供基础的聊天消息发送、图片/文件资源发送、用户头像获取、图片观察工具等基础功能",
    version="0.1.1",
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

    STRICT_MESSAGE_FILTER: bool = Field(
        default=False,
        title="启用严格重复消息过滤",
        description="启用后，完全重复的消息将直接抛出异常，否则仅过滤并提示",
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.7,
        title="消息相似度警告阈值",
        description="当消息相似度超过该阈值时，将触发系统警告提示引导 AI 调整生成策略",
    )
    SIMILARITY_CHECK_LENGTH: int = Field(
        default=12,
        title="启用消息相似度检查阈值",
        description="当消息长度超过该阈值时，将进行相似度检查",
    )
    ALLOW_AT_ALL: bool = Field(
        default=False,
        title="允许 @全体成员",
        description="启用后，消息中可以触发 @全体成员 功能；禁用时将被替换为纯文本形式的 @全体成员",
    )


# 获取配置
config: BasicConfig = plugin.get_config(BasicConfig)


@plugin.mount_prompt_inject_method(name="basic_prompt_inject")
async def basic_prompt_inject(_ctx: AgentCtx):
    """示例提示注入"""
    return ""


SEND_MSG_CACHE: Dict[str, List[str]] = {}
SEND_FILE_CACHE: Dict[str, List[str]] = {}  # 文件 MD5 缓存，格式: {chat_key: [md5_1, md5_2, md5_3]}


def _calculate_text_similarity(text1: str, text2: str) -> float:
    """计算两段文本的相似度

    Args:
        text1 (str): 第一段文本
        text2 (str): 第二段文本

    Returns:
        float: 相似度（0-1）
    """
    return difflib.SequenceMatcher(None, text1, text2).ratio()


async def _calculate_file_md5(file_path: str) -> str:
    """计算文件的 MD5 值或获取标识

    Args:
        file_path (str): 文件路径或 URL

    Returns:
        str: 本地文件返回 MD5 哈希值，URL 返回其链接
    """
    # 对于网络资源，直接返回 URL 作为标识
    if is_url_path(file_path):
        return file_path

    # 处理本地文件
    try:
        md5_hash = hashlib.md5()
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(4096)
                if not chunk:
                    break
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except Exception as e:
        logger.warning(f"计算文件 MD5 失败: {e}")
        return file_path  # 如果无法计算 MD5，则返回文件路径作为标识


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送聊天消息文本",
    description="发送聊天消息文本，附带缓存消息重复检查",
)
async def send_msg_text(_ctx: AgentCtx, chat_key: str, message_text: str):
    """发送聊天消息文本

    Attention: Do not expose any unnecessary technical id or key in the message content.

    Args:
        chat_key (str): 会话标识
        message_text (str): 消息内容
    """
    global SEND_MSG_CACHE

    if not message_text.strip():
        raise Exception("Error: The message content cannot be empty.")

    if not config.ALLOW_AT_ALL:
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
        if config.STRICT_MESSAGE_FILTER:
            raise Exception(
                "Error: Identical message has been sent recently. Carefully read the recent chat history whether it has sent duplicate messages. Please generate more interesting replies. If you COMPLETELY DETERMINED that it is necessary, resend it. SPAM IS NOT ALLOWED!",
            )
        await message_service.push_system_message(
            chat_key=chat_key,
            agent_messages="System Alert: Identical message has been sent recently. Auto Skip this message. Carefully read the recent chat history whether it has sent duplicate messages. If you COMPLETELY DETERMINED that it is necessary, resend it. SPAM IS NOT ALLOWED!",
            trigger_agent=False,
        )
        return

    # 检查相似度（仅对超过限定字符的消息进行检查）
    if len(message_text) > config.SIMILARITY_CHECK_LENGTH:
        for recent_msg in recent_messages:
            similarity = _calculate_text_similarity(message_text, recent_msg)
            if similarity > config.SIMILARITY_THRESHOLD:
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
        logger.exception(f"发送消息失败: {e}")
        raise Exception(
            "Error sending text message to chat: Make sure the chat key is valid, you have permission to speak and message is not too long.",
        ) from e

    # 更新消息缓存
    SEND_MSG_CACHE[chat_key].append(message_text)
    SEND_MSG_CACHE[chat_key] = SEND_MSG_CACHE[chat_key][-10:]  # 保持最近10条消息


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送聊天消息图片/文件资源",
    description="发送聊天消息图片/文件资源，附带缓存文件重复检查",
)
async def send_msg_file(_ctx: AgentCtx, chat_key: str, file_path: str):
    """发送聊天消息图片/文件资源

    Args:
        chat_key (str): 会话标识
        file_path (str): 图片/文件路径或 URL 容器内路径
    """
    global SEND_FILE_CACHE
    file_container_path = file_path  # 防止误导llm
    if not isinstance(file_container_path, str):
        raise TypeError("Error: The file argument must be a string with the correct file shared path or URL.")

    if is_url_path(file_container_path):
        file_host_path, _ = await download_file(file_container_path, from_chat_key=chat_key)
        file_container_path = str(convert_to_container_path(Path(file_host_path)))
    else:
        file_host_path = str(
            convert_to_host_path(Path(file_container_path), _ctx.from_chat_key, container_key=_ctx.container_key),
        )
        if not Path(file_host_path).exists():
            raise FileNotFoundError(
                f"The file `{file_container_path}` does not exist! Attention: The file you generated in previous conversation may not be persistence in sandbox environment, please check it.",
            )
    # 初始化文件缓存
    if chat_key not in SEND_FILE_CACHE:
        SEND_FILE_CACHE[chat_key] = []

    # 计算文件 MD5
    file_md5 = await _calculate_file_md5(file_host_path)

    # 检查是否重复发送
    if file_md5 in SEND_FILE_CACHE[chat_key]:
        SEND_FILE_CACHE[chat_key].remove(file_md5)
        if config.STRICT_MESSAGE_FILTER:
            raise Exception(
                "Error: Identical file has been sent recently. Please check if this file is really needed to be sent again. Please generate more interesting replies. SPAM IS NOT ALLOWED!",
            )
        await message_service.push_system_message(
            chat_key=chat_key,
            agent_messages="System Alert: Identical file has been sent recently. Auto Skip this file. Please check if this file is really needed to be sent again. Please generate more interesting replies. SPAM IS NOT ALLOWED!",
            trigger_agent=False,
        )
        return

    try:
        # 使用magic库检测文件MIME类型
        async with aiofiles.open(file_host_path, "rb") as f:
            file_data = await f.read()
            mime_type = magic.from_buffer(file_data, mime=True)
            is_image = mime_type.startswith("image/")

        if is_image:
            await message.send_image(chat_key, file_container_path, _ctx)
        else:
            await message.send_file(chat_key, file_container_path, _ctx)

        # 更新文件缓存
        SEND_FILE_CACHE[chat_key].append(file_md5)
        SEND_FILE_CACHE[chat_key] = SEND_FILE_CACHE[chat_key][-3:]  # 只保留最近 3 个文件的 MD5
    except Exception as e:
        raise Exception(
            f"Error sending file to chat: {e}, make sure the file path is valid(in shared directory or uploads directory).",
        ) from e


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="获取用户头像",
    description="获取用户头像",
)
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
    global SEND_MSG_CACHE, SEND_FILE_CACHE
    SEND_MSG_CACHE = {}
    SEND_FILE_CACHE = {}
