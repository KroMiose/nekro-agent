import hashlib
import time
from typing import Optional, Union

from nonebot import on_message
from nonebot.adapters.minecraft import Bot, Event
from nonebot.adapters.minecraft.event.base import (
    BaseChatEvent,
    BaseDeathEvent,
    BasePlayerCommandEvent,
)
from nonebot.matcher import Matcher

from nekro_agent.adapters.interface import (
    BaseAdapter,
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
    collect_message,
)
from nekro_agent.core import config, logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentType,
    ChatType,
)


def register_matcher(adapter: BaseAdapter):
    @on_message(priority=999, block=False).handle()
    async def _(_matcher: Matcher, event: Union[BaseChatEvent, BasePlayerCommandEvent, BaseDeathEvent], _bot: Bot):
        """Minecraft 消息收集与预处理"""

        plt_channel: PlatformChannel = PlatformChannel(
            channel_id=event.server_name,
            channel_name=event.server_name,
            channel_type=ChatType.GROUP,
        )

        sender_name: Optional[str] = event.player.nickname
        original_player_uuid = str(event.player.uuid)
        short_player_id = hashlib.sha1(original_player_uuid.encode("utf-8")).hexdigest()[:10]

        plt_user: PlatformUser = PlatformUser(
            platform_name="Minecraft",
            user_id=short_player_id,
            user_name=sender_name,
            user_avatar="",
        )

        msg_list = []
        plain_text_content = event.message.extract_plain_text()
        msg_list.append(
            ChatMessageSegment(
                type=ChatMessageSegmentType.TEXT,
                text=plain_text_content,
            ),
        )
        logger.info(f"Minecraft Message:{plain_text_content}")
        msg_id_from_event = event.message_id
        if msg_id_from_event and msg_id_from_event.strip():
            msg_id = msg_id_from_event
        else:
            msg_id = f"mc_{event.server_name}_{short_player_id}_{int(event.timestamp)}"

        plt_msg: PlatformMessage = PlatformMessage(
            message_id=msg_id,
            sender_id=short_player_id,
            sender_name=sender_name,
            sender_nickname=sender_name,
            content_data=msg_list,
            content_text=event.message.extract_plain_text(),
            is_tome=False,
            timestamp=int(event.timestamp),
        )

        await collect_message(adapter, plt_channel, plt_user, plt_msg)
