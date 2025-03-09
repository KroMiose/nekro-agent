from typing import Any, Dict, List, Type, cast

from pydantic import Field

from nekro_agent.api import core, message, user
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

plugin = NekroPlugin(
    name="basic",
    description="[NA] 基础交互工具集",
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
#     5. 扩展的清理方法 `clean_up` 会在扩展卸载时自动调用，请在此方法中实现清理或重置逻辑
# ========================================================================================


@plugin.mount_config()
class BasicConfig(ConfigBase):
    """基础配置"""

    some_field: str = Field(default="", title="一些配置")


# 获取配置
config = plugin.get_config(BasicConfig)
config.some_field = "test"


@plugin.mount_prompt_inject_method(name="basic_prompt_inject")
async def basic_prompt_inject(_ctx: AgentCtx):
    """基础提示注入"""
    return "This is a injected prompt test."


SEND_MSG_CACHE: Dict[str, List[str]] = {}


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "发送聊天消息文本")
async def send_msg_text(chat_key: str, message_text: str, _ctx: AgentCtx):
    """发送聊天消息文本

    Args:
        chat_key (str): 会话标识
        message_text (str): 消息内容
    """
    global SEND_MSG_CACHE

    if message_text in SEND_MSG_CACHE.get(_ctx.from_chat_key, []):
        core.logger.warning(f"[{_ctx.from_chat_key}] 检测到重复消息, 跳过发送...")
        SEND_MSG_CACHE[_ctx.from_chat_key] = [msg for msg in SEND_MSG_CACHE[_ctx.from_chat_key] if msg != message_text]
        return

    try:
        await message.send_text(chat_key, message_text, _ctx)
    except Exception as e:
        raise Exception(
            "Error sending text message to chat: Make sure the chat key is correct, you have permission to speak, and the content is not empty or too long.",
        ) from e

    if _ctx.from_chat_key not in SEND_MSG_CACHE:
        SEND_MSG_CACHE[_ctx.from_chat_key] = []

    SEND_MSG_CACHE[_ctx.from_chat_key].append(message_text)
    SEND_MSG_CACHE[_ctx.from_chat_key] = SEND_MSG_CACHE[_ctx.from_chat_key][-10:]


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "发送聊天消息图片/文件资源")
async def send_msg_file(chat_key: str, file_path: str, _ctx: AgentCtx):
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
async def get_user_avatar(user_qq: str, _ctx: AgentCtx) -> str:
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
    """清理扩展"""
    global SEND_MSG_CACHE
    SEND_MSG_CACHE = {}
