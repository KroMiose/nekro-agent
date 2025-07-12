import re
from typing import List, Union

from pydantic import BaseModel

from nekro_agent.core.logger import logger

# 更新正则表达式以支持带有昵称的复杂 @ 格式
# 例如 [@id:123456;nickname:SomeUser@]
AT_PATTERN = re.compile(r"\[@id:(\d+?)(?:;nickname:.*?)?@\]")


class SegAt(BaseModel):
    """@ 消息段"""

    platform_user_id: str


def parse_at_from_text(text: str) -> List[Union[str, SegAt]]:
    """从文本中解析@信息
    需要提取 '[@id:123456;nickname:用户名@]' 或 '[@id:123456@]' 这样的格式，其余的文本不变

    Args:
        text (str): 文本

    Returns:
        List[Union[str, SegAt]]: 解析结果 (原始文本或SegAt对象)
    """
    result: List[Union[str, SegAt]] = []
    start = 0
    while True:
        at_index = text.find("[@", start)
        # 如果找不到更多的`[@`，则将剩余的文本全部添加到结果中并结束循环
        if at_index == -1:
            if start < len(text):
                result.append(text[start:])
            break

        # 添加`[@`之前的部分
        result.append(text[start:at_index])

        end_index = text.find("@]", at_index)
        # 如果找不到匹配的`@]`，则将从`[@`开始的剩余文本视为普通文本
        if end_index == -1:
            result.append(text[at_index:])
            break

        # 提取`[@`和`@]`之间的内容
        seg_content = text[at_index + 2 : end_index]

        # 检查内容是否以 "id:" 开头
        if seg_content.strip().startswith("id:"):
            parts = seg_content.strip().split(";")
            uid_part = parts[0]
            uid = uid_part.replace("id:", "").strip()
            # 确保提取的ID是数字
            if uid.isdigit():
                result.append(SegAt(platform_user_id=uid))
            else:  # ID格式不正确，将整个`[@...@]`视为普通文本
                result.append(text[at_index : end_index + 2])
        else:  # @格式不符合预期，将整个`[@...@]`视为普通文本
            result.append(text[at_index : end_index + 2])

        # 更新下一次搜索的起始位置
        start = end_index + 2

    # 过滤掉可能产生的空字符串
    return [item for item in result if item] 