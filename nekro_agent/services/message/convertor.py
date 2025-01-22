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
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentAt,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    segments_from_list,
)
from nekro_agent.tools.common_util import (
    download_file,
    get_downloaded_prompt_file_path,
    move_to_upload_dir,
)
from nekro_agent.tools.onebot_util import get_user_group_card_name


async def convert_chat_message(
    ob_event: Union[MessageEvent, GroupMessageEvent, GroupUploadNoticeEvent],
    msg_to_me: bool,
    bot: Bot,  # noqa: ARG001
    chat_key: str,  # noqa: ARG001
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
                return ret_list, False, ""
            local_path, file_name = await download_file(
                ob_event.file.model_extra["url"],
                use_suffix=suffix,
                from_chat_key=chat_key,
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
                local_path, file_name = await download_file(remote_url, use_suffix=suffix, from_chat_key=chat_key)
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
                local_path, file_name = await move_to_upload_dir(seg_local_path, use_suffix=suffix, from_chat_key=chat_key)
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
                nick_name = config.AI_CHAT_PRESET_NAME
            else:
                nick_name = await get_user_group_card_name(group_id=ob_event.group_id, user_id=at_qq)
            logger.info(f"OneBot at message: {at_qq=} {nick_name=}")
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
        ret_list.insert(
            0,
            ChatMessageSegmentAt(
                type=ChatMessageSegmentType.AT,
                text="",
                target_qq=str(config.BOT_QQ),
                target_nickname=config.AI_CHAT_PRESET_NAME,
            ),
        )

    return ret_list, is_tome, message_id


def convert_chat_message_to_prompt_str(chat_message: List[ChatMessageSegment], one_time_code: str) -> str:
    """将 ChatMessageSegment 列表转换为提示词字符串

    Args:
        chat_message (List[ChatMessageSegment]): ChatMessageSegment 列表

    Returns:
        str: 提示词字符串
    """

    prompt_str = ""

    for seg in chat_message:
        if isinstance(seg, ChatMessageSegmentImage):
            prompt_str += f"<{one_time_code} | Image:{get_downloaded_prompt_file_path(seg.file_name)}>"
        elif isinstance(seg, ChatMessageSegmentFile):
            prompt_str += f"<{one_time_code} | File:{get_downloaded_prompt_file_path(seg.file_name)}>"
        elif isinstance(seg, ChatMessageSegmentAt):
            prompt_str += f"<{one_time_code} | At:[@qq:{seg.target_qq};nickname:{seg.target_nickname}@]>"
        elif isinstance(seg, ChatMessageSegment):
            prompt_str += seg.text

    return prompt_str


def convert_raw_msg_data_json_to_msg_prompt(json_data: str, one_time_code: str):
    """将数据库保存的原始消息数据 JSON 转换为提示词字符串

    Args:
        json_data (str): 数据库保存的原始消息数据 JSON

    Returns:
        str: 提示词字符串
    """

    return convert_chat_message_to_prompt_str(
        segments_from_list(cast(List[Dict[str, Any]], json5.loads(json_data))),
        one_time_code,
    )
