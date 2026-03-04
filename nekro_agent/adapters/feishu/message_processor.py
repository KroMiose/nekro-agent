from typing import TYPE_CHECKING, Any, Dict

from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.extra import PlatformMessageExt
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)

from .tools import (
    extract_text_from_post,
    is_bot_mentioned,
    parse_message_content,
    remove_mention_tags,
)

logger = get_sub_logger("adapter.feishu")

if TYPE_CHECKING:
    from .adapter import FeishuAdapter
    from .client import FeishuClient


async def handle_message(
    client: "FeishuClient",
    adapter: "FeishuAdapter",
    event_data: Dict[str, Any],
) -> None:
    """处理飞书消息事件

    将飞书原始事件转换为 NekroAgent 标准格式并分发。

    Args:
        client: 飞书客户端实例
        adapter: 飞书适配器实例
        event_data: 飞书事件数据
    """
    try:
        sender = event_data.get("sender", {})
        sender_id = sender.get("sender_id", {})
        sender_open_id = sender_id.get("open_id", "")
        sender_type = sender.get("sender_type", "")

        # 忽略非用户消息（如机器人、系统消息等）
        if sender_type != "user":
            logger.debug(f"忽略非用户消息: sender_type={sender_type}")
            return

        message = event_data.get("message", {})
        msg_type = message.get("message_type", "")
        message_id = message.get("message_id", "")
        chat_id = message.get("chat_id", "")
        chat_type = message.get("chat_type", "")
        content_str = message.get("content", "{}")
        mentions_raw = message.get("mentions", [])

        bot_info = client.bot_info
        bot_open_id = bot_info.user_id if bot_info else ""

        # 1. 过滤机器人自身消息
        if sender_open_id == bot_open_id:
            return

        # 2. 确定 channel_id 格式
        if chat_type == "group":
            channel_id = f"group_{chat_id}"
            channel_type = ChatType.GROUP
        else:
            channel_id = f"private_{sender_open_id}"
            channel_type = ChatType.PRIVATE

        chat_key = adapter.build_chat_key(channel_id)

        # 3. 构建 mentions 字典（key -> mention info）
        mentions: Dict[str, Any] = {}
        if mentions_raw:
            for mention in mentions_raw:
                mention_key = mention.get("key", "")
                if mention_key:
                    mentions[mention_key] = mention

        # 4. 根据 msg_type 解析消息内容
        content = parse_message_content(msg_type, content_str)
        segments: list[ChatMessageSegment] = []
        content_text = ""

        if msg_type == "text":
            text = content.get("text", "")
            text = remove_mention_tags(text, mentions, bot_open_id)
            content_text = text
            if text:
                segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=text))

        elif msg_type == "image":
            image_key = content.get("image_key", "")
            if image_key:
                try:
                    image_bytes = await client.download_image(message_id, image_key)
                    segment = await ChatMessageSegmentImage.create_from_bytes(
                        _bytes=image_bytes,
                        from_chat_key=chat_key,
                        file_name=f"{image_key}.png",
                    )
                    segments.append(segment)
                    content_text = segment.text
                except Exception:
                    logger.exception(f"下载图片失败: image_key={image_key}")
                    content_text = "[图片]"
                    segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text="[图片]"))

        elif msg_type == "post":
            text = extract_text_from_post(content)
            content_text = text
            if text:
                segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=text))

        elif msg_type == "file":
            file_key = content.get("file_key", "")
            file_name = content.get("file_name", "unknown_file")
            if file_key:
                try:
                    file_bytes = await client.download_file(message_id, file_key)
                    segment = await ChatMessageSegmentFile.create_from_bytes(
                        _bytes=file_bytes,
                        from_chat_key=chat_key,
                        file_name=file_name,
                    )
                    segments.append(segment)
                    content_text = segment.text
                except Exception:
                    logger.exception(f"下载文件失败: file_key={file_key}")
                    content_text = f"[文件: {file_name}]"
                    segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=content_text))

        else:
            content_text = f"[不支持的消息类型: {msg_type}]"
            segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=content_text))

        if not segments:
            logger.debug("空消息，已忽略")
            return

        # 5. 判断 is_tome
        is_tome = is_bot_mentioned(mentions, bot_open_id) or chat_type == "p2p"

        # 6. 获取发送者信息
        sender_name = sender_open_id
        try:
            user_info = await client.get_user_info(sender_open_id)
            sender_name = user_info.get("name", sender_open_id)
        except Exception:
            logger.debug(f"获取用户信息失败: open_id={sender_open_id}")

        # 7. 获取频道名称
        channel_name = channel_id
        if chat_type == "group":
            try:
                chat_info = await client.get_chat_info(chat_id)
                channel_name = chat_info.get("name", channel_id)
            except Exception:
                logger.debug(f"获取群聊信息失败: chat_id={chat_id}")

        # 8. 构造标准对象
        platform_user = PlatformUser(
            platform_name="feishu",
            user_id=sender_open_id,
            user_name=sender_name,
        )

        platform_channel = PlatformChannel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_type=channel_type,
        )

        platform_message = PlatformMessage(
            message_id=message_id,
            sender_id=sender_open_id,
            sender_name=sender_name,
            sender_nickname=sender_name,
            content_text=content_text.strip(),
            content_data=segments,
            is_tome=is_tome,
            ext_data=PlatformMessageExt(),
        )

        # 9. 分发消息
        await collect_message(
            adapter=adapter,
            platform_channel=platform_channel,
            platform_user=platform_user,
            platform_message=platform_message,
        )

    except Exception:
        logger.exception("处理飞书消息事件失败")
