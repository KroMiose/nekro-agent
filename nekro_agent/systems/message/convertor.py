from typing import List

from nonebot.adapters.onebot.v11 import (
    Message,
)

from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
)
from nekro_agent.tools.common_util import download_file


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
