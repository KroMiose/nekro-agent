"""NoneBot @ 解析工具

这个模块包含 NoneBot 平台特定的 @ 解析功能。
"""

from typing import List, Optional, Union

from pydantic import BaseModel

from nekro_agent.adapters.onebot_v11.tools.onebot_util import get_user_group_card_name
from nekro_agent.models.db_chat_channel import DBChatChannel


class SegAt(BaseModel):
    """@ 消息段"""

    platform_user_id: str
    nickname: Optional[str]


async def parse_at_from_text(text: str, db_chat_channel: DBChatChannel) -> List[Union[str, SegAt]]:
    """从文本中解析@信息 (NoneBot 平台特定功能)
    需要提取 '[@id:123456;nickname:用户名@]' 或 '[@id:123456@]' 这样的格式，其余的文本不变

    Args:
        text (str): 文本
        db_chat_channel (DBChatChannel): 聊天频道信息
        adapter (BaseAdapter): 适配器实例

    Returns:
        List[Union[str, SegAt]]: 解析结果 (原始文本或SegAt对象)

    Examples:
        >>> parse_at_from_text("hello [@id:123456;nickname:用户名@]")
        ['hello ', SegAt(platform_user_id='123456', nickname='用户名')]
        >>> parse_at_from_text("hello [@id:123456@]")
        ['hello ', SegAt(platform_user_id='123456', nickname=None)]
        >>> parse_at_from_text("hello world")
        ['hello world']
    """
    adapter = db_chat_channel.adapter
    result = []
    start = 0
    while True:
        at_index = text.find("[@", start)
        if at_index == -1:
            result.append(text[start:])
            break
        result.append(text[start:at_index])
        end_index = text.find("@]", at_index)
        if end_index == -1:
            result.append(text[at_index:])
            break
        seg = text[at_index + 2 : end_index]
        if "nickname:" in seg:
            parts = seg.split(";")
            uid = parts[0].replace("id:", "").strip()
            nickname = parts[1].replace("nickname:", "").strip()
            if not adapter.config.SESSION_ENABLE_AT:
                result.append(f"{nickname}")
            else:
                if "group" in db_chat_channel.chat_key:
                    result.append(SegAt(platform_user_id=uid, nickname=None))
                else:
                    result.append("")  # 私聊无法@
        else:
            uid = seg.replace("id:", "").strip()
            if not adapter.config.SESSION_ENABLE_AT:
                if "group" in db_chat_channel.chat_key:
                    group_id = db_chat_channel.chat_key.replace("group_", "")
                    nickname = await get_user_group_card_name(group_id=group_id, user_id=uid, db_chat_channel=db_chat_channel)
                    result.append(f"{nickname}")
                else:
                    result.append("")
            else:
                if "group" in db_chat_channel.chat_key:
                    result.append(SegAt(platform_user_id=uid, nickname=None))
                else:
                    result.append("")  # 私聊无法@
        start = end_index + 2  # 跳过 '@]' 标志
    return result
