import time
from typing import Optional, Union

from nonebot import on_message, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GroupUploadNoticeEvent,
    MessageEvent,
)
from nonebot.matcher import Matcher

from nekro_agent.adapters.interface import (
    BaseAdapter,
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
    collect_message,
)
from nekro_agent.adapters.interface.schemas.extra import PlatformMessageExt
from nekro_agent.adapters.onebot_v11.tools.convertor import convert_chat_message
from nekro_agent.adapters.onebot_v11.tools.onebot_util import (
    gen_chat_text,
    get_chat_info,
    get_message_reply_info,
    get_user_name,
)
from nekro_agent.core import config, logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_user import DBUser


def register_matcher(adapter: BaseAdapter):

    @on_message(priority=99999, block=False).handle()
    async def _(_: Matcher, event: Union[MessageEvent, GroupMessageEvent], bot: Bot):
        """消息匹配器"""

        # 频道信息处理
        channel_id, chat_type = await get_chat_info(event=event)
        plt_channel: PlatformChannel = PlatformChannel(channel_id=channel_id, channel_name="", channel_type=chat_type)
        db_chat_channel: DBChatChannel = await plt_channel.get_db_chat_channel(adapter)

        if not db_chat_channel.channel_name:
            plt_channel = await adapter.get_channel_info(channel_id)

        # 用户信息处理
        sender_name: Optional[str] = event.sender.nickname or event.sender.card
        assert sender_name

        user_qq = str(event.sender.user_id)
        user_avatar: str = f"https://q1.qlogo.cn/g?b=qq&nk={user_qq}&s=640"

        plt_user: PlatformUser = PlatformUser(
            platform_name="qq",
            user_id=user_qq,
            user_name=sender_name,
            user_avatar=user_avatar,
        )

        # 消息内容处理
        content_data, msg_tome, message_id = await convert_chat_message(event, event.to_me, bot, db_chat_channel, adapter)
        if not content_data:  # 忽略无法转换的消息
            logger.warning(f"无法转换的消息: {event.get_plaintext()}")
            return

        sender_nickname: str = await get_user_name(
            event=event,
            bot=bot,
            user_id=plt_user.user_id,
            db_chat_channel=db_chat_channel,
        )
        content_text, is_tome = await gen_chat_text(event=event, bot=bot, db_chat_channel=db_chat_channel)

        if any(content_text.startswith(prefix) for prefix in config.AI_IGNORED_PREFIXES):
            logger.info(f"忽略前缀匹配的消息: {content_text[:32]}...")
            return

        ref_msg_id = await get_message_reply_info(event=event)

        plt_msg: PlatformMessage = PlatformMessage(
            message_id=message_id,
            sender_id=plt_user.user_id,
            sender_name=sender_name,
            sender_nickname=sender_nickname,
            content_data=content_data,
            content_text=content_text,
            is_tome=bool(is_tome or msg_tome),
            timestamp=int(time.time()),
            ext_data=PlatformMessageExt(ref_msg_id=ref_msg_id),
        )

        # 提交收集消息
        await collect_message(adapter, plt_channel, plt_user, plt_msg)

    @on_notice(priority=99999, block=False).handle()
    async def _(_: Matcher, event: GroupUploadNoticeEvent, bot: Bot):
        """上传事件匹配器"""
        # 频道信息处理
        channel_id, chat_type = await get_chat_info(event=event)
        plt_channel: PlatformChannel = PlatformChannel(channel_id=channel_id, channel_name="", channel_type=chat_type)
        db_chat_channel: DBChatChannel = await plt_channel.get_db_chat_channel(adapter)

        # 用户信息处理
        platform_userid: str = str(event.user_id)
        user: Optional[DBUser] = await DBUser.get_or_none(adapter_key=adapter.key, platform_userid=platform_userid)

        if not user:
            if platform_userid == (await adapter.get_self_info()).user_id:
                return
            raise ValueError(f"用户 {platform_userid} 尚未注册，请先发送任意消息注册后即可上传文件") from None

        if not user.is_active:
            logger.info(f"用户 {platform_userid} 被封禁，封禁结束时间: {user.ban_until}")
            return

        # 用户信息处理
        sender_name: Optional[str] = user.username
        plt_user: PlatformUser = PlatformUser(platform_name="qq", user_id=platform_userid, user_name=sender_name)

        # 消息内容处理
        content_data, msg_tome, message_id = await convert_chat_message(event, False, bot, db_chat_channel, adapter)
        if not content_data:  # 忽略无法转换的消息
            return

        sender_nickname: str = await get_user_name(
            event=event,
            bot=bot,
            user_id=platform_userid,
            db_chat_channel=db_chat_channel,
        )

        plt_msg: PlatformMessage = PlatformMessage(
            message_id=message_id,
            sender_id=platform_userid,
            sender_name=sender_name,
            sender_nickname=sender_nickname,
            content_data=content_data,
            content_text="",
            is_tome=bool(msg_tome),
            timestamp=int(time.time()),
        )

        # 提交收集消息
        await collect_message(adapter, plt_channel, plt_user, plt_msg)
