import time
from datetime import datetime
from typing import Any, Dict, Optional, Type

from nonebot import on_notice
from nonebot.adapters.minecraft import Bot, NoticeEvent
from nonebot.matcher import Matcher

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.chat_message import ChatMessage, ChatType
from nekro_agent.services.message_service import message_service
from nekro_agent.services.notice_service import (
    BaseNoticeHandler,
    NoticeConfig,
    NoticeResult,
)
from nekro_agent.tools.time_util import format_duration


class PlayerJoinNoticeHandler(BaseNoticeHandler):
    """玩家加入通知处理器"""

    def get_notice_config(self) -> NoticeConfig:
        return NoticeConfig(force_tome=True, use_system_sender=True)

    def match(self, _db_chat_channel: DBChatChannel, event_dict: Dict[str, Any]) -> Optional[Dict[str, str]]:
        if event_dict["sub_type"] != "join":
            return None
        return {
            "user_id": str(event_dict["player"].nickname),
        }

    async def format_message(self, _db_chat_channel: DBChatChannel, info: Dict[str, str]) -> str:
        return f"(玩家 {info['user_id']} 加入了服务器)"

class PlayerQuitNoticeHandler(BaseNoticeHandler):
    """玩家离开通知处理器"""

    def get_notice_config(self) -> NoticeConfig:
        return NoticeConfig(force_tome=True, use_system_sender=True)

    def match(self, _db_chat_channel: DBChatChannel, event_dict: Dict[str, Any]) -> Optional[Dict[str, str]]:
        if event_dict["sub_type"] != "quit":
            return None
        return {
            "user_id": str(event_dict["player"].nickname),
        }

    async def format_message(self, _db_chat_channel: DBChatChannel, info: Dict[str, str]) -> str:
        return f"(玩家 {info['user_id']} 离开了服务器)"

class NoticeHandlerManager:
    """通知处理器管理器"""

    def __init__(self):
        self._handlers: list[BaseNoticeHandler] = []

    def register(self, handler: BaseNoticeHandler):
        """注册处理器"""
        self._handlers.append(handler)

    async def handle(self, event: NoticeEvent, _bot: Bot, db_chat_channel: DBChatChannel) -> Optional[NoticeResult]:
        """处理通知事件

        Args:
            event (NoticeEvent): 通知事件
            _bot (Bot): 机器人实例

        Returns:
            Optional[NoticeResult]: 处理结果，包含处理器实例和通知信息
        """
        # 预处理事件为字典
        event_dict = dict(event)

        for handler in self._handlers:
            if info := handler.match(db_chat_channel, event_dict):
                return NoticeResult(
                    handler=handler,
                    info=info,
                )
        return None

    def get_sender_platform_userid(self, info: Dict[str, str]) -> str:
        """获取发送者平台用户ID"""
        return info["user_id"]

notice_manager = NoticeHandlerManager()

notice_manager.register(PlayerJoinNoticeHandler())
notice_manager.register(PlayerQuitNoticeHandler())

"""通用通知匹配器"""
notice_matcher: Type[Matcher] = on_notice(priority=99999, block=False)


@notice_matcher.handle()
async def _(_: Matcher, event: NoticeEvent, bot: Bot):
    # 处理通知事件
    chat_key = "minecraft-" + event.server_name
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
    result = await notice_manager.handle(event, bot, db_chat_channel)
    if not result:
        event_dict = dict(event)
        logger.debug(
            f"收到未处理的通知类型: {event_dict}\n"
            f"notice_type: {event_dict.get('notice_type')}\n"
            f"sub_type: {event_dict.get('sub_type')}\n",
        )
        return

    handler = result["handler"]
    info = result["info"]

    # 格式化消息
    content_text = await handler.format_message(db_chat_channel, info)

    if handler.config.use_system_sender:
        # 使用系统消息
        await message_service.push_system_message(
            chat_key=chat_key,
            agent_messages=content_text,
            trigger_agent=handler.config.force_tome,
        )
    else:
        # 使用普通消息
        platform_userid: str = handler.get_sender_platform_userid(info)
        user: Optional[DBUser] = await DBUser.get_or_none(
            adapter_key=db_chat_channel.adapter_key,
            platform_userid=platform_userid,
        )
        sender_nickname = event.player.nickname

        if user and not user.is_active:
            logger.info(f"用户 {platform_userid} 被封禁，封禁结束时间: {user.ban_until}")
            return

        chat_message: ChatMessage = ChatMessage(
            message_id="",
            sender_id=str(user.id) if user else platform_userid,
            sender_name=user.username if user else sender_nickname,
            sender_nickname=sender_nickname,
            adapter_key=db_chat_channel.adapter_key,
            platform_userid=platform_userid,
            is_tome=1 if handler.config.force_tome else 0,
            is_recalled=False,
            chat_key=chat_key,
            chat_type=ChatType.GROUP,
            content_text=content_text,
            content_data=[],
            raw_cq_code="",
            ext_data={},
            send_timestamp=int(time.time()),
        )
        await message_service.push_human_message(message=chat_message, user=user)