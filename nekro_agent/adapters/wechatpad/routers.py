from fastapi import APIRouter, Request, Response
from typing import Dict, Any, TYPE_CHECKING

from nekro_agent.core import logger
from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
)
from nekro_agent.schemas.chat_message import ChatMessageSegment, ChatType
from nekro_agent.adapters.utils import adapter_utils

from .schemas import WeChatPadMessageEvent, MessageType

if TYPE_CHECKING:
    from .adapter import WeChatPadAdapter

# 实例化一个路由
router = APIRouter()


async def handle_wechat_event(event: Dict[str, Any]):
    """处理解析后的微信事件"""
    
    # 获取适配器实例
    adapter: "WeChatPadAdapter" = adapter_utils.get_adapter("wechatpad")
    
    # 尝试解析为消息事件
    try:
        msg_event = WeChatPadMessageEvent(**event)
        
        # 只处理文本消息（后续可扩展其他类型）
        if msg_event.MsgType == MessageType.TEXT and msg_event.Content:
            await handle_text_message(adapter, msg_event)
        else:
            logger.debug(f"跳过非文本消息，类型: {msg_event.MsgType}")
            
    except Exception as e:
        logger.error(f"解析微信事件失败: {e}")
        logger.debug(f"原始事件数据: {event}")


async def handle_text_message(adapter: "WeChatPadAdapter", msg_event: WeChatPadMessageEvent):
    """处理文本消息事件"""
    
    if not msg_event.FromUserName or not msg_event.Content:
        logger.warning("消息缺少必要字段，跳过处理")
        return
    
    # 获取自身信息用于判断 is_self
    try:
        self_info = await adapter.get_self_info()
        bot_wxid = self_info.user_id
    except Exception as e:
        logger.warning(f"获取自身信息失败，无法判断 is_self: {e}")
        bot_wxid = ""
    
    # 判断是否为自己发送的消息
    is_self = msg_event.FromUserName == bot_wxid
    
    # 如果是自己发送的消息，跳过处理
    if is_self:
        logger.debug(f"跳过自己发送的消息: {msg_event.Content[:50]}...")
        return
    
    # 判断是群聊还是私聊
    is_group = bool(msg_event.ChatroomId)
    channel_id = msg_event.ChatroomId if is_group else msg_event.FromUserName
    chat_type = ChatType.GROUP if is_group else ChatType.PRIVATE
    
    # 判断是否为 @ 消息（仅在群聊中有意义）
    is_tome = False
    if is_group and bot_wxid:
        # 检查消息中是否包含 @ 机器人的内容
        # 微信中 @ 消息通常以 @显示名 开头，或者检查 AtWxIDList
        is_tome = (f"@{bot_wxid}" in msg_event.Content or 
                  msg_event.Content.startswith("@") or 
                  (msg_event.AtWxIDList and bot_wxid in msg_event.AtWxIDList))
    elif not is_group:
        # 私聊消息默认为 @ 机器人
        is_tome = True
    
    # 构造平台频道信息
    platform_channel = PlatformChannel(
        channel_id=channel_id,
        channel_name="",  # 暂时为空，后续可通过 API 获取
        channel_type=chat_type,
    )
    
    # 构造平台用户信息
    platform_user = PlatformUser(
        user_id=msg_event.FromUserName,
        user_name=msg_event.FromUserName,  # 暂时使用 wxid 作为用户名
        platform_name="微信",
        avatar_url="",  # 暂时为空，后续可通过 API 获取
    )
    
    # 构造消息段
    content_segments = [
        ChatMessageSegment(
            type="text",
            data={"text": msg_event.Content}
        )
    ]
    
    # 构造平台消息
    platform_message = PlatformMessage(
        message_id=msg_event.MsgId or msg_event.NewMsgId or "",
        sender_id=msg_event.FromWxid,
        sender_name=msg_event.FromWxid,
        sender_nickname=msg_event.FromWxid,  # 暂时使用 wxid，后续可通过 API 获取昵称
        content_data=content_segments,
        content_text=msg_event.Content,
        is_tome=is_tome,
        timestamp=msg_event.CreateTime or 0,
        is_self=is_self,
    )
    
    # 提交消息到收集器
    await collect_message(adapter, platform_channel, platform_user, platform_message)
    
    logger.info(f"处理微信消息: [{channel_id}] {msg_event.FromWxid}: {msg_event.Content}")


@router.post("/webhook", summary="接收 WeChatPadPro 事件回调")
async def wechat_webhook(request: Request):
    """
    此端点用于接收 WeChatPadPro 推送的事件。
    请确保在 WeChatPadConfig 中配置的 WECHATPAD_CALLBACK_URL 指向此端点。
    """
    try:
        event_data = await request.json()
        # WeChatPadPro 的事件可能没有统一的 'type' 字段，需要根据具体结构来判断
        # 这里我们直接将整个数据包传递给处理函数
        await handle_wechat_event(event_data)
        return Response(status_code=200, content="OK")
    except Exception as e:
        logger.error(f"处理微信 Webhook 失败: {e!s}")
        logger.exception(e)
        # 返回 200 OK，避免微信服务因回调失败而反复重试
        return Response(status_code=200, content="Error processing webhook")
