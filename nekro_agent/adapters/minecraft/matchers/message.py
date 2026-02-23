import hashlib
from typing import Optional

from nonebot import on_message
from nonebot.adapters.minecraft import Bot
from nonebot.adapters.minecraft.event import MessageEvent
from nonebot.matcher import Matcher

from nekro_agent.adapters.interface import (
    BaseAdapter,
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
    collect_message,
)
from nekro_agent.core import logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentType,
    ChatType,
)


def register_matcher(adapter: BaseAdapter):
    @on_message(priority=999, block=False).handle()
    async def _(_matcher: Matcher, event: MessageEvent, _bot: Bot):
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

        message = event.get_message()
        plain_text_content = message.extract_plain_text()
        msg_list = [
            ChatMessageSegment(
                type=ChatMessageSegmentType.TEXT,
                text=plain_text_content,
            ),
        ]
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
            content_text=plain_text_content,
            is_tome=False,
            timestamp=int(event.timestamp),
        )

        await collect_message(adapter, plt_channel, plt_user, plt_msg)
