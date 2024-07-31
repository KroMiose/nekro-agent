import json
from typing import List

from nonebot.adapters.onebot.v11 import (
    Message,
)

from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    segments_from_list,
)
from nekro_agent.tools.common_util import download_file, get_downloaded_prompt_file_path


async def convert_chat_message(ob_message: Message) -> List[ChatMessageSegment]:
    """转换 OneBot 消息为 ChatMessageSegment 列表

    Args:
        ob_message (Message): OneBot 消息

    Returns:
        List[ChatMessageSegment]: ChatMessageSegment 列表
    """

    ret_list: List[ChatMessageSegment] = []

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
                suffix = "." + seg.data["file"].split(".")[-1].lower()
            except Exception:
                suffix = ""
            remote_url: str = seg.data["url"]
            local_path, file_name = await download_file(remote_url, use_suffix=suffix)
            ret_list.append(
                ChatMessageSegmentImage(
                    type=ChatMessageSegmentType.IMAGE,
                    text="",
                    file_name=file_name,
                    local_path=local_path,
                    remote_url=remote_url,
                ),
            )

        elif seg.type == "file":
            ...  # TODO: llob 传递过来的文件没有直链，待补充实现

    return ret_list


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

    return convert_chat_message_to_prompt_str(segments_from_list(json.loads(json_data)), one_time_code)
