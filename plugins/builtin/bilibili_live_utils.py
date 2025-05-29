import re
from typing import Dict, List

from pydantic import Field

from nekro_agent.api import core
from nekro_agent.api.plugin import (
    ConfigBase,
    NekroPlugin,
    SandboxMethod,
    SandboxMethodType,
)
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.message_service import message_service
from nekro_agent.tools.common_util import calculate_text_similarity

plugin = NekroPlugin(
    name="Bilibili 直播工具插件",
    module_name="bilibili_live_utils",
    description="提供 Bilibili 直播适配器专用的消息发送和Live2d模型设置等功能",
    version="0.1.0",
    author="Zaxpris",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["bilibili_live"],
)

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

config: BasicConfig = plugin.get_config(BasicConfig)

# 消息缓存
SEND_MSG_CACHE: Dict[str, List[str]] = {}

@plugin.mount_prompt_inject_method(name="basic_prompt_inject")
async def basic_prompt_inject(_ctx: AgentCtx):
    """可用表情提示词注入"""
    chat_key = _ctx.chat_key
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id) # type: ignore
    avilable_expressions = ""
    if ws_client:
        msg = {
            "type": "emotion",
            "data": {},
        }
        avilable_expressions = await ws_client.send_animate_control(msg)
        core.logger.info(f"[{chat_key}] 可用表情：{avilable_expressions}")
    basic_prompt =f"""
    当执行send_text_message, set_expression时,设定的发言的和表情任务都会被存进队列,
    只有当执行send_execute时,队列中的动画任务才会被执行
    你可以通过上一次send_execute和下一次send_execute之间增加延迟来实现你想要的模型控制效果
    以下是你可用的表情：
    {avilable_expressions}
    """
    return basic_prompt  # noqa: RET504

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="计算总朗读时长",
    description="计算所有文本在给定语速下的总朗读时长",
)
async def calculate_total_duration(texts: List[str], speeds: List[float]) -> float:
    """
    计算所有文本在给定语速下的总朗读时长
    
    参数:
        texts (List[str]): 要朗读的文本字符串列表
        speeds (List[float]): 朗读速度列表 (每秒字符数)
    
    返回:
        float: 总时长(秒)
    """
    if len(texts) != len(speeds):
        raise ValueError("文本列表和速度列表的长度必须相同")
    
    total_duration = 0.0
    
    for text, speed in zip(texts, speeds):
        # 去除引号并计算字符数
        clean_text = text.strip("'\"")
        char_count = len(clean_text)
        
        # 计算该文本在给定速度下的朗读时长
        duration = char_count / speed
        total_duration += duration
    
    return total_duration + 0.1
@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送文本消息",
    description="发送聊天消息文本，附带缓存消息重复检查",
)
async def send_text_message(_ctx: AgentCtx, chat_key: str, message_text: List[str], speeds: List[float]):
    """发送聊天消息文本

    Attention: Do not expose any unnecessary technical id or key in the message content.

    Args:
        chat_key (str): 会话标识
        message_text (List[str]): 消息内容列表
        speeds (List[float]): 语速列表，单位为每秒钟字数
        5.0为中速，8.0为快速，2.0为慢速
    """
    global SEND_MSG_CACHE

    # 检查消息列表是否为空或者长度不匹配
    if not message_text:
        raise Exception("Error: The message list cannot be empty.")
    
    if len(message_text) != len(speeds):
        raise Exception("Error: The length of message_text and speeds must be equal.")
    
    # 检查每条消息内容
    for text in message_text:
        if not text.strip():
            raise Exception("Error: The message content cannot be empty.")
        
        # 拒绝包含 [image:xxx...] 的图片消息
        if re.match(r"^.*\[image:.*\]$", text) and len(text) > 100:
            raise Exception(
                "Error: You can't send image message directly, please use the send_msg_file method to send image/file resources.",
            )

    # 初始化消息缓存
    if chat_key not in SEND_MSG_CACHE:
        SEND_MSG_CACHE[chat_key] = []

    recent_messages = SEND_MSG_CACHE[chat_key][-5:] if SEND_MSG_CACHE[chat_key] else []

    # 合并所有消息文本用于检查
    combined_message = " ".join(message_text)

    # 检查完全匹配
    if combined_message in recent_messages:
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
    for recent_msg in recent_messages:
        similarity = calculate_text_similarity(combined_message, recent_msg, min_length=config.SIMILARITY_CHECK_LENGTH)
        if similarity > config.SIMILARITY_THRESHOLD:
            # 发送系统消息提示避免类似内容
            core.logger.warning(f"[{chat_key}] 检测到相似度过高的消息: {similarity:.2f}")
            await message_service.push_system_message(
                chat_key=chat_key,
                agent_messages="System Alert: You have sent a message that is too similar to a recently sent message! You should KEEP YOUR RESPONSE USEFUL and not redundant and cumbersome!",
                trigger_agent=False,
            )
            break

    # TODO: 在这里实现实际的消息发送逻辑
    # 此处预留给用户自行实现发送功能
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id) # type: ignore
    if ws_client:
        msg = {
            "type": "say",
            "data": {
                "text": message_text,
                "speed": speeds,
                "delay": 0.0,
            },
        }
        await ws_client.send_animate_control(msg)
    # 更新消息缓存
    SEND_MSG_CACHE[chat_key].append(combined_message)
    SEND_MSG_CACHE[chat_key] = SEND_MSG_CACHE[chat_key][-10:]  # 保持最近10条消息

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="设置Live2d表情",
    description="设置Live2d表情",
)
async def set_expression(_ctx: AgentCtx, chat_key: str, expression: str, duration: float):
    """设置Live2d表情

    Args:
        chat_key (str): 会话标识
        expression (str): 表情名称
        duration (float): 表情持续时间
    """
    # TODO: 在这里实现实际的Live2d模型设置逻辑
    # 此处预留给用户自行实现设置功能
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id) # type: ignore
    if ws_client:
        msg = {
            "type": "emotion",
            "data": {
                "name": expression,
                "duration": duration,
                "delay": 0.0,
            },
        }
        await ws_client.send_animate_control(msg)

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送执行指令",
    description="发送执行指令",
)
async def send_execute(_ctx: AgentCtx, chat_key: str):
    """发送执行指令

    Args:
        chat_key (str): 会话标识
    """
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id) # type: ignore
    if ws_client:
        msg = {
            "type": "execute",
            "data": {
                "loop": 0,
            },
        }
        await ws_client.send_animate_control(msg)

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
    global SEND_MSG_CACHE
    SEND_MSG_CACHE = {}
    
