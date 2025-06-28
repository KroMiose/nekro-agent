from pathlib import Path
from typing import List, Tuple, Union

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GroupUploadNoticeEvent,
    Message,
    MessageEvent,
)

from nekro_agent.adapters.interface.base import BaseAdapter
from nekro_agent.adapters.onebot_v11.tools.onebot_util import get_user_group_card_name
from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import NAPCAT_TEMPFILE_DIR
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentAt,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)
from nekro_agent.tools.common_util import (
    copy_to_upload_dir,
    download_file,
)


async def convert_chat_message(
    ob_event: Union[MessageEvent, GroupMessageEvent, GroupUploadNoticeEvent],
    msg_to_me: bool,
    bot: Bot,  # noqa: ARG001
    db_chat_channel: DBChatChannel,
    adapter: BaseAdapter,
) -> Tuple[List[ChatMessageSegment], bool, str]:
    """转换 OneBot 消息为 ChatMessageSegment 列表

    Args:
        ob_message (Message): OneBot 消息

    Returns:
        List[ChatMessageSegment]: ChatMessageSegment 列表
        bool: 是否为机器人发送的消息
        str: 消息 ID
    """

    ret_list: List[ChatMessageSegment] = []
    is_tome = False

    if isinstance(ob_event, GroupUploadNoticeEvent):
        if ob_event.file.size > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            logger.warning(f"文件过大，跳过处理: {ob_event.file.name}")
            return ret_list, False, ""
        if ob_event.file.model_extra and ob_event.file.model_extra.get("url"):
            suffix = "." + ob_event.file.name.rsplit(".", 1)[-1]
            if not ob_event.file.model_extra["url"].startswith("http"):
                logger.warning(f"上传文件无法获取到直链: {ob_event.file.model_extra['url']}")
                return ret_list, False, ""
            ret_list.append(
                await ChatMessageSegmentFile.create_from_url(
                    url=ob_event.file.model_extra["url"],
                    from_chat_key=db_chat_channel.chat_key,
                ),
            )
        elif ob_event.file.id:
            file_data = await bot.get_file(file_id=ob_event.file.id)
            logger.debug(f"获取文件: {file_data}")
            # TODO: 获取文件: {'file': '/app/.config/QQ/NapCat/temp/XXXXXX.csv', 'url': '/app/.config/QQ/NapCat/temp/XXXXXX.csv', 'file_size': '1079', 'file_name': 'XXXXXX.csv'}
            # napcat 挂载目录 ${NEKRO_DATA_DIR}/napcat_data/QQ:/app/.config/QQ
            target_file_path = str(Path(NAPCAT_TEMPFILE_DIR) / file_data["file_name"])
            if Path(target_file_path).exists():
                ret_list.append(
                    await ChatMessageSegmentFile.create_form_local_path(
                        local_path=target_file_path,
                        from_chat_key=db_chat_channel.chat_key,
                        file_name=file_data["file_name"],
                    ),
                )
            else:
                logger.warning(f"文件不存在: {target_file_path}")
        else:
            logger.debug(f"无法处理的文件消息: {ob_event.file}")

        return ret_list, False, ""

    ob_message: Message = ob_event.message
    message_id: str = str(ob_event.message_id)

    for seg in ob_message:
        if seg.type == "text":
            ret_list.append(
                ChatMessageSegment(
                    type=ChatMessageSegmentType.TEXT,
                    text=seg.data.get("text", ""),
                ),
            )

        elif seg.type == "image":
            try:
                if "filename" in seg.data:
                    suffix = "." + seg.data["filename"].split(".")[-1].lower()
                elif "file_id" in seg.data:
                    suffix = "." + seg.data["file_id"].split(".")[-1].lower()
                else:
                    suffix = "." + seg.data["file"].split(".")[-1].lower()
                if len(suffix) > 10:
                    logger.warning(f"文件后缀过长: {suffix}; from: {seg=}; 取消后缀")
                    suffix = ""
            except Exception:
                suffix = ""
            if "url" in seg.data:
                remote_url: str = seg.data["url"]
                ret_list.append(
                    await ChatMessageSegmentImage.create_from_url(
                        url=remote_url,
                        from_chat_key=db_chat_channel.chat_key,
                        use_suffix=suffix,
                    ),
                )
            elif "file" in seg.data:
                seg_local_path = seg.data["file"]
                if seg_local_path.startswith("file:"):
                    seg_local_path = seg_local_path[len("file:") :]
                ret_list.append(
                    await ChatMessageSegmentImage.create_form_local_path(
                        local_path=seg_local_path,
                        from_chat_key=db_chat_channel.chat_key,
                        use_suffix=suffix,
                    ),
                )
            else:
                logger.warning(f"OneBot image message without url: {seg}")
                continue

        elif seg.type == "at":
            assert isinstance(ob_event, GroupMessageEvent)
            at_qq = str(seg.data["qq"])
            bot_qq = (await adapter.get_self_info()).user_id
            if at_qq == bot_qq:
                at_qq = bot_qq
                is_tome = True
                nick_name = (await db_chat_channel.get_preset()).name
            else:
                nick_name = await get_user_group_card_name(
                    group_id=ob_event.group_id,
                    user_id=at_qq,
                    db_chat_channel=db_chat_channel,
                )
            logger.info(f"OneBot at message: {at_qq=} {nick_name=}")
            if not adapter.config.SESSION_ENABLE_AT:
                ret_list.append(
                    ChatMessageSegment(
                        type=ChatMessageSegmentType.TEXT,
                        text=f"@{nick_name}",
                    ),
                )
            else:
                logger.info(f"Session Allow At: {nick_name}")
                ret_list.append(
                    ChatMessageSegmentAt(
                        type=ChatMessageSegmentType.AT,
                        text="",
                        target_platform_userid=at_qq,
                        target_nickname=nick_name,
                    ),
                )

        elif seg.type == "file":
            ...  # TODO: llob 传递过来的文件没有直链，待补充实现

    if msg_to_me and not is_tome:
        is_tome = True
        ret_list.insert(
            0,
            ChatMessageSegmentAt(
                type=ChatMessageSegmentType.AT,
                text="",
                target_platform_userid=(await adapter.get_self_info()).user_id,
                target_nickname=(await db_chat_channel.get_preset()).name,
            ),
        )

    return ret_list, is_tome, message_id


def get_channel_type(channel_id: str) -> ChatType:
    try:
        chat_type, _ = channel_id.split("_")
        return ChatType(chat_type)
    except ValueError as e:
        raise ValueError(f"Invalid channel id: {channel_id}") from e
