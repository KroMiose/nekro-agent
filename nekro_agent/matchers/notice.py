import time
from typing import Any, Dict, Optional, Type

from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Bot, NoticeEvent
from nonebot.matcher import Matcher

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.notice import BaseNoticeHandler, NoticeConfig, notice_manager
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.chat_message import ChatMessage, ChatType
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.user import query_user_by_bind_qq
from nekro_agent.tools.onebot_util import get_chat_info, get_user_name
from nekro_agent.tools.time_util import format_duration


class PokeNoticeHandler(BaseNoticeHandler):
    """戳一戳通知处理器"""

    def match(self, event_dict: Dict[str, Any]) -> Optional[Dict[str, str]]:
        if event_dict["notice_type"] != "notify" or event_dict.get("sub_type") != "poke":
            return None
        return {
            "user_id": str(event_dict["user_id"]),
            "target_id": str(event_dict["target_id"]),
        }

    def format_message(self, info: Dict[str, str]) -> str:
        if str(info["target_id"]) == str(config.BOT_QQ):
            return f"(戳了戳 {config.AI_CHAT_PRESET_NAME})"
        return f"(戳了戳 {info['target_id']})"


class GroupIncreaseNoticeHandler(BaseNoticeHandler):
    """群成员增加通知处理器"""

    def get_notice_config(self) -> NoticeConfig:
        return NoticeConfig(force_tome=True, use_system_sender=True)

    def match(self, event_dict: Dict[str, Any]) -> Optional[Dict[str, str]]:
        if event_dict["notice_type"] != "group_increase":
            return None
        return {
            "user_id": str(event_dict["user_id"]),
        }

    def format_message(self, info: Dict[str, str]) -> str:
        return f"(新成员 (qq:{info['user_id']}) 加入群聊)"


class GroupDecreaseNoticeHandler(BaseNoticeHandler):
    """群成员减少通知处理器"""

    def get_notice_config(self) -> NoticeConfig:
        return NoticeConfig(force_tome=True, use_system_sender=True)

    def match(self, event_dict: Dict[str, Any]) -> Optional[Dict[str, str]]:
        if event_dict["notice_type"] != "group_decrease":
            return None
        return {
            "user_id": str(event_dict["user_id"]),
        }

    def format_message(self, info: Dict[str, str]) -> str:
        return f"(成员 (qq:{info['user_id']}) 退出群聊)"


class GroupBanNoticeHandler(BaseNoticeHandler):
    """群禁言通知处理器"""

    def get_notice_config(self) -> NoticeConfig:
        return NoticeConfig(force_tome=False, use_operator_as_sender=True)

    def match(self, event_dict: Dict[str, Any]) -> Optional[Dict[str, str]]:
        if event_dict["notice_type"] != "group_ban":
            return None
        return {
            "user_id": str(event_dict["user_id"]),
            "operator_id": str(event_dict["operator_id"]),
            "duration": str(event_dict["duration"]),
        }

    def format_message(self, info: Dict[str, str]) -> str:
        duration = int(info["duration"])
        if duration == 0:
            return f"(成员 (qq:{info['user_id']}) 被管理员 (qq:{info['operator_id']}) 解除禁言)"
        duration_str = format_duration(duration)
        return f"(成员 (qq:{info['user_id']}) 被管理员 (qq:{info['operator_id']}) 禁言 {duration_str})"


class GroupRecallNoticeHandler(BaseNoticeHandler):
    """群消息撤回通知处理器"""

    def get_notice_config(self) -> NoticeConfig:
        return NoticeConfig(force_tome=False, use_system_sender=True)

    def match(self, event_dict: Dict[str, Any]) -> Optional[Dict[str, str]]:
        if event_dict["notice_type"] != "group_recall":
            return None
        return {
            "user_id": str(event_dict["user_id"]),
            "operator_id": str(event_dict["operator_id"]),
            "message_id": str(event_dict["message_id"]),
        }

    def format_message(self, info: Dict[str, str]) -> str:
        # 如果是自己撤回
        if info["user_id"] == info["operator_id"]:
            return f"(成员 (qq:{info['user_id']}) 撤回了一条消息，但该消息仍然对你可见)"
        # 如果是被管理员撤回
        return f"(成员 (qq:{info['user_id']}) 的一条消息被管理员 (qq:{info['operator_id']}) 撤回，但该消息仍然对你可见)"


# 注册所有通知处理器
notice_manager.register(PokeNoticeHandler())
notice_manager.register(GroupIncreaseNoticeHandler())
notice_manager.register(GroupDecreaseNoticeHandler())
notice_manager.register(GroupBanNoticeHandler())
notice_manager.register(GroupRecallNoticeHandler())


"""通用通知匹配器"""
notice_matcher: Type[Matcher] = on_notice(priority=99999, block=False)


@notice_matcher.handle()
async def _(
    _: Matcher,
    event: NoticeEvent,
    bot: Bot,
):
    # 处理通知事件
    result = await notice_manager.handle(event, bot)
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
    chat_key, chat_type = await get_chat_info(event=event)

    # 格式化消息
    content_text = handler.format_message(info)

    if handler.config.use_system_sender:
        # 使用系统消息
        await message_service.push_system_message(
            chat_key=chat_key,
            agent_messages=content_text,
            trigger_agent=handler.config.force_tome,
        )
    else:
        # 使用普通消息
        bind_qq: str = handler.get_sender_bind_qq(info)
        user: Optional[DBUser] = await query_user_by_bind_qq(bind_qq)
        sender_nickname = await get_user_name(event=event, bot=bot, user_id=bind_qq)

        chat_message: ChatMessage = ChatMessage(
            message_id="",
            sender_id=str(user.id) if user else bind_qq,
            sender_real_nickname=user.username if user else sender_nickname,
            sender_nickname=sender_nickname,
            sender_bind_qq=bind_qq,
            is_tome=(
                1
                if (
                    handler.config.force_tome or (isinstance(handler, PokeNoticeHandler) and info["target_id"] == config.BOT_QQ)
                )
                else 0
            ),
            is_recalled=False,
            chat_key=chat_key,
            chat_type=chat_type,
            content_text=content_text,
            content_data=[],
            raw_cq_code="",
            ext_data={},
            send_timestamp=int(time.time()),
        )
        await message_service.push_human_message(message=chat_message)
