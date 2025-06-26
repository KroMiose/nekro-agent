import time
from typing import TYPE_CHECKING, Optional

from nekro_agent.core import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.chat_message import ChatMessage
from nekro_agent.schemas.user import UserCreate
from nekro_agent.services.message_service import message_service
from nekro_agent.services.user.util import user_register

if TYPE_CHECKING:
    from nekro_agent.adapters.interface import (
        BaseAdapter,
        PlatformChannel,
        PlatformMessage,
        PlatformUser,
    )


async def collect_message(
    adapter: "BaseAdapter",
    platform_channel: "PlatformChannel",
    platform_user: "PlatformUser",
    platform_message: "PlatformMessage",
) -> None:
    """适配器消息收集器"""

    db_chat_channel: DBChatChannel = await DBChatChannel.get_or_create(
        adapter_key=adapter.key,
        channel_id=platform_channel.channel_id,
        channel_type=platform_channel.channel_type,
        channel_name=platform_channel.channel_name,
    )

    if not db_chat_channel.is_active:
        return

    # 用户处理
    user: Optional[DBUser] = await DBUser.get_by_union_id(adapter_key=adapter.key, platform_userid=platform_user.user_id)

    if not user:
        ret = await user_register(
            UserCreate(
                username=platform_user.user_name,
                password="",
                adapter_key=adapter.key,
                platform_userid=platform_user.user_id,
            ),
        )

        if not ret:
            logger.error(f"注册用户失败: {platform_user.user_name} - {platform_user.user_id}")
            return

        user = await DBUser.get_by_union_id(adapter_key=adapter.key, platform_userid=platform_user.user_id)
        assert user

    if not user.is_active:
        logger.info(f"用户 {platform_user.user_id} 被封禁，封禁结束时间: {user.ban_until}")
        return

    if platform_message.is_self:
        logger.info(f'接收自身消息 "{platform_message.content_text}"，跳过...')
        return

    chat_message: ChatMessage = ChatMessage(
        message_id=platform_message.message_id,
        sender_id=platform_user.user_id,
        sender_name=platform_user.user_name,
        sender_nickname=platform_message.sender_nickname,
        adapter_key=adapter.key,
        platform_userid=platform_user.user_id,
        is_tome=platform_message.is_tome,
        is_recalled=False,
        chat_key=db_chat_channel.chat_key,
        chat_type=platform_channel.channel_type,
        content_text=platform_message.content_text,
        content_data=platform_message.content_data,
        raw_cq_code="",
        ext_data=platform_message.ext_data.model_dump() if platform_message.ext_data else {},
        send_timestamp=int(time.time()),
    )

    ref_str: str = (
        f" (ref: {platform_message.ext_data.ref_msg_id})"
        if platform_message.ext_data and platform_message.ext_data.ref_msg_id
        else ""
    )

    logger.info(
        f"Message Collect: [{chat_message.chat_key}] {platform_user.platform_name} {chat_message.sender_nickname}: {chat_message.content_text}{ref_str}",
    )

    await message_service.push_human_message(message=chat_message, user=user, db_chat_channel=db_chat_channel)
