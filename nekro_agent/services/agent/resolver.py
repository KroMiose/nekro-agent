import re
from typing import Tuple

from pydantic import BaseModel


class ParsedCodeRunData(BaseModel):
    raw_content: str
    code_content: str
    thought_chain: str


def parse_chat_response(raw_content: str) -> ParsedCodeRunData:
    """
    解析聊天响应内容，提取思维链和代码内容。

    Args:
        raw_content: 原始响应内容

    Returns:
        ParsedCodeRunData对象, 即代码执行数据
    """
    # 清理和准备内容
    cleaned_content = raw_content.strip()
    thought_chain = ""
    code_content = ""

    # 检查是否同时存在<think>和</think>标签
    has_think_tags = "<think>" in cleaned_content and "</think>" in cleaned_content

    if has_think_tags:
        # 如果存在思维链，匹配思维链和代码内容
        think_pattern = re.compile(r"<think>(.*?)</think>\s*(?:```(?:python)?\s*(.*?)```)?", re.DOTALL)
        match = think_pattern.search(cleaned_content)

        if match:
            # 提取思维链内容并清理可能存在的嵌套标签
            thought_chain = match.group(1).strip()
            thought_chain = re.sub(r"</?think>", "", thought_chain)

            # 如果匹配到了代码块
            if match.group(2):
                code_content = match.group(2).strip()

    # 如果通过思维链匹配没有提取到代码内容，尝试直接匹配代码块
    if not code_content:
        # 提取所有代码块
        code_pattern = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)
        code_matches = code_pattern.findall(cleaned_content)

        if code_matches:
            # 选择最长的代码块
            code_content = max(code_matches, key=len).strip()
        else:
            # 如果没有代码块，移除思维链部分后的内容作为代码
            content_without_think = re.sub(r"<think>.*?</think>", "", cleaned_content, flags=re.DOTALL).strip()
            code_content = content_without_think

    return ParsedCodeRunData(raw_content=raw_content, code_content=code_content, thought_chain=thought_chain)
