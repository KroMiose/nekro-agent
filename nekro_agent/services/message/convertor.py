from fileinput import filename
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union, cast

import json5
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GroupUploadNoticeEvent,
    Message,
    MessageEvent,
)

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
    segments_from_list,
)
from nekro_agent.tools.common_util import (
    copy_to_upload_dir,
    download_file,
)
from nekro_agent.tools.onebot_util import get_user_group_card_name
from nekro_agent.tools.path_convertor import get_sandbox_path


async def convert_chat_message(
    ob_event: Union[MessageEvent, GroupMessageEvent, GroupUploadNoticeEvent],
    msg_to_me: bool,
    bot: Bot,  # noqa: ARG001
    db_chat_channel: DBChatChannel,
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
            local_path, file_name = await download_file(
                ob_event.file.model_extra["url"],
                use_suffix=suffix,
                from_chat_key=db_chat_channel.chat_key,
            )
            ret_list.append(
                ChatMessageSegmentFile(
                    type=ChatMessageSegmentType.FILE,
                    text="",
                    file_name=file_name,
                    local_path=local_path,
                    remote_url="",
                ),
            )
        elif ob_event.file.id:
            file_data = await bot.get_file(file_id=ob_event.file.id)
            logger.debug(f"获取文件: {file_data}")
            # TODO: 获取文件: {'file': '/app/.config/QQ/NapCat/temp/XXXXXX.csv', 'url': '/app/.config/QQ/NapCat/temp/XXXXXX.csv', 'file_size': '1079', 'file_name': 'XXXXXX.csv'}
            # napcat 挂载目录 ${NEKRO_DATA_DIR}/napcat_data/QQ:/app/.config/QQ
            target_file_path = str(Path(NAPCAT_TEMPFILE_DIR) / file_data["file_name"])
            if Path(target_file_path).exists():
                local_path, file_name = await copy_to_upload_dir(
                    file_path=target_file_path,
                    file_name=file_data["file_name"],
                    from_chat_key=db_chat_channel.chat_key,
                )
                logger.debug(f"上传文件转移: {target_file_path} -> {local_path}")
                ret_list.append(
                    ChatMessageSegmentFile(
                        type=ChatMessageSegmentType.FILE,
                        text="",
                        file_name=file_name,
                        local_path=local_path,
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
                local_path, file_name = await download_file(
                    remote_url,
                    use_suffix=suffix,
                    from_chat_key=db_chat_channel.chat_key,
                )
                ret_list.append(
                    ChatMessageSegmentImage(
                        type=ChatMessageSegmentType.IMAGE,
                        text="",
                        file_name=file_name,
                        local_path=local_path,
                        remote_url=remote_url,
                    ),
                )
            elif "file" in seg.data:
                seg_local_path = seg.data["file"]
                if seg_local_path.startswith("file:"):
                    seg_local_path = seg_local_path[len("file:") :]
                local_path, file_name = await copy_to_upload_dir(
                    seg_local_path,
                    use_suffix=suffix,
                    from_chat_key=db_chat_channel.chat_key,
                )
                ret_list.append(
                    ChatMessageSegmentImage(
                        type=ChatMessageSegmentType.IMAGE,
                        text="",
                        file_name=file_name,
                        local_path=local_path,
                        remote_url="",
                    ),
                )
            else:
                logger.warning(f"OneBot image message without url: {seg}")
                continue

        elif seg.type == "at":
            assert isinstance(ob_event, GroupMessageEvent)
            at_qq = str(seg.data["qq"])
            bot_qq = str(config.BOT_QQ)
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
            if not config.SESSION_ENABLE_AT:
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
                        target_qq=at_qq,
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
                target_qq=str(config.BOT_QQ),
                target_nickname=(await db_chat_channel.get_preset()).name,
            ),
        )

    return ret_list, is_tome, message_id


def convert_raw_msg_data_json_to_msg_prompt(json_data: str, one_time_code: str, travel_mode: bool = False) -> str:
    """将数据库保存的原始消息数据 JSON 转换为提示词字符串

    Args:
        json_data (str): 数据库保存的原始消息数据 JSON

    Returns:
        str: 提示词字符串
    """

    prompt_str = ""

    for seg in segments_from_list(cast(List[Dict[str, Any]], json5.loads(json_data))):
        if isinstance(seg, ChatMessageSegmentImage):
            prompt_str += (
                f"<Image:{get_sandbox_path(seg.file_name)}>"
                if travel_mode
                else f"<{one_time_code} | Image:{get_sandbox_path(seg.file_name)}>"
            )
        elif isinstance(seg, ChatMessageSegmentFile):
            prompt_str += (
                f"<File:{get_sandbox_path(seg.file_name)}>"
                if travel_mode
                else f"<{one_time_code} | File:{get_sandbox_path(seg.file_name)}>"
            )
        elif isinstance(seg, ChatMessageSegmentAt):
            prompt_str += (
                f"<At:[@qq:{seg.target_qq};nickname:{seg.target_nickname}@]>"
                if travel_mode
                else f"<{one_time_code} | At:[@qq:{seg.target_qq};nickname:{seg.target_nickname}@]>"
            )
        elif isinstance(seg, ChatMessageSegment):
            prompt_str += seg.text

    return prompt_str
