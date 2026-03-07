import json
import re
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger

logger = get_sub_logger("adapter.feishu")

AT_PATTERN = re.compile(r"\[@id:(\S+?)(?:;nickname:.*?)?@\]")


class SegAt(BaseModel):
    """@ 消息段"""

    platform_user_id: str


def parse_at_from_text(text: str) -> List[Union[str, SegAt]]:
    """从文本中解析 @ 信息

    解析 '[@id:ou_xxx;nickname:用户名@]' 格式，其余文本不变。

    Args:
        text: 待解析文本

    Returns:
        解析结果列表（原始文本或 SegAt 对象）
    """
    result: List[Union[str, SegAt]] = []
    start = 0
    while True:
        at_index = text.find("[@", start)
        if at_index == -1:
            if start < len(text):
                result.append(text[start:])
            break

        result.append(text[start:at_index])

        end_index = text.find("@]", at_index)
        if end_index == -1:
            result.append(text[at_index:])
            break

        seg_content = text[at_index + 2 : end_index]

        if seg_content.strip().startswith("id:"):
            parts = seg_content.strip().split(";")
            uid_part = parts[0]
            uid = uid_part.replace("id:", "").strip()
            if uid:
                result.append(SegAt(platform_user_id=uid))
            else:
                result.append(text[at_index : end_index + 2])
        else:
            result.append(text[at_index : end_index + 2])

        start = end_index + 2

    return [item for item in result if item]


def remove_mention_tags(text: str, mentions: Optional[Dict[str, Any]], bot_open_id: str) -> str:
    """移除飞书消息中的 @_user_N mention 占位符

    Args:
        text: 消息文本
        mentions: 消息中的 mention 信息字典
        bot_open_id: 机器人自身的 open_id

    Returns:
        清理后的纯文本
    """
    if not mentions:
        return text

    for _key, mention in mentions.items():
        mention_key = mention.get("key", "")
        if mention_key and mention_key in text:
            # 如果 mention 的是机器人自身，直接移除占位符
            if mention.get("id", {}).get("open_id") == bot_open_id:
                text = text.replace(mention_key, "")
            else:
                # 其他用户的 mention 替换为名称
                name = mention.get("name", "")
                text = text.replace(mention_key, f"@{name}" if name else "")

    return text.strip()


def is_bot_mentioned(mentions: Optional[Dict[str, Any]], bot_open_id: str) -> bool:
    """检查 mentions 列表中是否包含机器人

    Args:
        mentions: 消息中的 mention 信息字典
        bot_open_id: 机器人自身的 open_id

    Returns:
        是否 @ 了机器人
    """
    if not mentions:
        return False

    for _key, mention in mentions.items():
        if mention.get("id", {}).get("open_id") == bot_open_id:
            return True

    return False


def extract_text_from_post(content: Dict[str, Any]) -> str:
    """从飞书 post（富文本）消息中提取纯文本

    飞书富文本结构：
    {
        "zh_cn": {
            "title": "标题",
            "content": [
                [{"tag": "text", "text": "内容"}, {"tag": "at", "user_id": "ou_xxx"}],
                [{"tag": "text", "text": "第二行"}]
            ]
        }
    }

    Args:
        content: 飞书 post 消息的 content 字典

    Returns:
        提取的纯文本
    """
    text_parts: List[str] = []

    # post 内容可能有多种语言，取第一个可用的
    post_data = None
    for _lang, data in content.items():
        if isinstance(data, dict):
            post_data = data
            break

    if not post_data:
        return ""

    title = post_data.get("title", "")
    if title:
        text_parts.append(title)

    paragraphs = post_data.get("content", [])
    for paragraph in paragraphs:
        if not isinstance(paragraph, list):
            continue
        line_parts: List[str] = []
        for element in paragraph:
            if not isinstance(element, dict):
                continue
            tag = element.get("tag", "")
            if tag == "text":
                line_parts.append(element.get("text", ""))
            elif tag == "a":
                line_parts.append(element.get("text", "") or element.get("href", ""))
            elif tag == "at":
                user_name = element.get("user_name", "")
                if user_name:
                    line_parts.append(f"@{user_name}")
        if line_parts:
            text_parts.append("".join(line_parts))

    return "\n".join(text_parts)


def parse_message_content(msg_type: str, content_str: str) -> Dict[str, Any]:
    """解析消息内容 JSON 字符串

    Args:
        msg_type: 消息类型
        content_str: 消息内容的 JSON 字符串

    Returns:
        解析后的字典
    """
    try:
        return json.loads(content_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"无法解析消息内容: msg_type={msg_type}, content={content_str}")
        return {}
