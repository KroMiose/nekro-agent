
"""SSE @ 解析工具

这个模块包含 SSE 适配器特定的 @ 解析功能。
"""

from typing import List, Optional, Union

from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_chat_channel import DBChatChannel


logger = get_sub_logger("adapter.sse")
class SegAt(BaseModel):
    """@ 消息段"""

    platform_user_id: str
    nickname: Optional[str]


async def parse_at_from_text(text: str, db_chat_channel: DBChatChannel) -> List[Union[str, SegAt]]:
    """从文本中解析@信息 (SSE 平台特定功能)

    需要提取以下格式的@信息，其余的文本不变：
    - '[@id:user123;nickname:用户名@]' - 带昵称的@
    - '[@id:user123@]' - 不带昵称的@
    - '[@id:abcd#1234@]' - 带#分隔符的特殊ID格式

    Args:
        text (str): 文本
        db_chat_channel (DBChatChannel): 聊天频道信息

    Returns:
        List[Union[str, SegAt]]: 解析结果 (原始文本或SegAt对象)

    Examples:
        >>> await parse_at_from_text("hello [@id:123456;nickname:用户名@]", db_chat_channel)
        ['hello ', SegAt(platform_user_id='123456', nickname='用户名')]
        >>> await parse_at_from_text("hello [@id:123456@]", db_chat_channel)
        ['hello ', SegAt(platform_user_id='123456', nickname=None)]
        >>> await parse_at_from_text("hello [@id:abcd#1234@]", db_chat_channel)
        ['hello ', SegAt(platform_user_id='abcd#1234', nickname=None)]
        >>> await parse_at_from_text("hello world", db_chat_channel)
        ['hello world']
    """
    adapter = db_chat_channel.adapter
    result = []
    start = 0

    # 从chat_key提取channel_id
    _, channel_id = adapter.parse_chat_key(db_chat_channel.chat_key)

    while True:
        # 查找 [@
        at_index = text.find("[@", start)
        if at_index == -1:
            # 没有找到，添加剩余文本
            result.append(text[start:])
            break

        # 添加 [@ 之前的文本
        result.append(text[start:at_index])

        # 查找 @]
        end_index = text.find("@]", at_index)
        if end_index == -1:
            # 没有找到结束标记，添加剩余文本
            result.append(text[at_index:])
            break

        # 提取 [@ 和 @] 之间的内容
        seg = text[at_index + 2 : end_index]

        # 解析内容
        if "nickname:" in seg:
            # 格式: id:xxx;nickname:yyy
            parts = seg.split(";")
            uid = parts[0].replace("id:", "").strip()
            nickname = parts[1].replace("nickname:", "").strip()

            # 检查是否启用@功能
            if not adapter.config.SESSION_ENABLE_AT:
                # 禁用@时，只显示昵称
                result.append(f"{nickname}")
            else:
                # 启用@时，添加@消息段
                result.append(SegAt(platform_user_id=uid, nickname=nickname))
        else:
            # 格式: id:xxx (可能包含#等特殊字符)
            uid = seg.replace("id:", "").strip()

            # 检查是否启用@功能
            if not adapter.config.SESSION_ENABLE_AT:
                # 禁用@时，尝试获取用户昵称
                try:
                    user_info = await adapter.get_user_info(uid, channel_id)
                    nickname = user_info.user_name or uid
                    result.append(f"{nickname}")
                except Exception:
                    logger.warning(f"解析 @消息 时获取用户信息失败: {uid!s} {channel_id!s} | 原始文本: {text!s}")
            else:
                # 启用@时，添加@消息段
                result.append(SegAt(platform_user_id=uid, nickname=None))

        # 移动到 @] 之后
        start = end_index + 2

    return result
