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
        # 如果存在思维链，先提取思维链
        think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
        think_match = think_pattern.search(cleaned_content)

        if think_match:
            # 提取思维链内容并清理可能存在的嵌套标签
            thought_chain = think_match.group(1).strip()
            thought_chain = re.sub(r"</?think>", "", thought_chain)

            # 在思维链之后查找代码块
            remaining_content = cleaned_content[think_match.end() :].strip()
            code_pattern = re.compile(r"```(?:python)?\s*(.*?)```(?:\s*$|(?=\s*```\s*$))", re.DOTALL)
            code_match = code_pattern.search(remaining_content)

            if code_match:
                code_content = code_match.group(1).strip()

    # 如果通过思维链匹配没有提取到代码内容，尝试直接匹配代码块
    if not code_content:
        # 提取最长的完整代码块（从```python到最后一个```）
        code_pattern = re.compile(r"```(?:python)?\s*(.*?)```(?:\s*$|(?=\s*```\s*$))", re.DOTALL)
        code_matches = code_pattern.finditer(cleaned_content)

        # 获取所有匹配结果
        matches_list = list(code_matches)
        if matches_list:
            # 选择最长的代码块
            code_content = max((match.group(1).strip() for match in matches_list), key=len)
        else:
            # 如果没有代码块，移除思维链部分后的内容作为代码
            content_without_think = re.sub(r"<think>.*?</think>", "", cleaned_content, flags=re.DOTALL).strip()
            code_content = content_without_think

    # 如果依然没有代码内容，则搜索全部响应内容取最长的代码块
    if not code_content:
        code_pattern = re.compile(r"```(?:python)?\s*(.*?)```(?:\s*$|(?=\s*```\s*$))", re.DOTALL)
        code_matches = code_pattern.finditer(cleaned_content)
        matches_list = list(code_matches)
        if matches_list:
            code_content = max((match.group(1).strip() for match in matches_list), key=len)

    if code_content.strip().startswith("```python"):
        code_content = code_content.strip()[len("```python") :].strip()
    if code_content.strip().endswith("```"):
        code_content = code_content.strip()[: -len("```")].strip()

    return ParsedCodeRunData(raw_content=raw_content, code_content=fix_code_content(code_content), thought_chain=thought_chain)


def fix_code_content(code_content: str) -> str:
    """修复代码内容"""
    # 修正代码块去掉所有 from plugins ... import ... 开头的行
    code_content = re.sub(r"^from plugins.*\n", "", code_content, flags=re.MULTILINE)
    code_content = re.sub(r"^from predefined_methods .*\n", "", code_content, flags=re.MULTILINE)
    code_content = re.sub(r"^from predefined_plugins .*\n", "", code_content, flags=re.MULTILINE)
    code_content = re.sub(r"^from core\.api.*\n", "", code_content, flags=re.MULTILINE)
    # 修正代码块去掉所有 from plugin_manager ... import ... 开头的行
    return re.sub(r"^from plugin_manager.*\n", "", code_content, flags=re.MULTILINE)


def fix_raw_response(raw_response: str) -> str:
    """修复原始响应"""
    # logger.debug(f"Raw response: {raw_response}")
    # 修正基本 at 格式
    raw_response = raw_response.replace("[qq:", "[@qq:")
    raw_response = raw_response.replace("@[qq:", "[@qq:")
    # 修正 [@qq:123456] -> [@qq:123456@]
    raw_response = re.sub(r"\[@qq:(\d+)\]", r"[@qq:\1@]", raw_response)
    # 修正 [@qq:123456;nickname:Abc] -> [@qq:123456@]
    raw_response = re.sub(r"\[@qq:(\d+);nickname[\=\:](.+)\]", r"[@qq:\1@]", raw_response)
    # 修正 [@123456] -> [@qq:123456@]
    raw_response = re.sub(r"\[@(\d+)\]", r"[@qq:\1@]", raw_response)
    # 修正 (@qq:123456@) -> [@qq:123456@]
    raw_response = re.sub(r"\(@qq:(\d+)@\)", r"[@qq:\1@]", raw_response)
    # 修正 (@qq:123456) -> [@qq:123456@]
    raw_response = re.sub(r"\(@qq:(\d+)\)", r"[@qq:\1@]", raw_response)
    # 修正 (@123456@) -> [@qq:123456@]
    raw_response = re.sub(r"\( ?@(\d+)@ ?\)", r"[@qq:\1@]", raw_response)
    # 修正  <7e56b348 | At:[@qq:xxx@]> -> [@qq:xxx@]
    raw_response = re.sub(r"<\w{8} ?\| At:\[@qq:(\d+)@\]>", r"[@qq:\1@]", raw_response)
    # 修正 (@[@qq:123456@]) -> [@qq:123456@]
    raw_response = re.sub(r"\(@\[@qq:(\d+)@\]\)", r"[@qq:\1@]", raw_response)
    # 修正 <@123456> -> [@qq:123456@]
    raw_response = re.sub(r"<@(\d+)>", r"[@qq:\1@]", raw_response)
    # 修正 @123456@) -> [@qq:123456@]
    raw_response = re.sub(r"@(\d+)@\)", r"[@qq:\1@]", raw_response)
    # 修正 (@123456) -> [@qq:123456@]
    raw_response = re.sub(r"\( ?@(\d+) ?\)", r"[@qq:\1@]", raw_response)
    # 修正 @123456@) -> [@qq:123456@]
    raw_response = re.sub(r"@(\d+)@ ?\)", r"[@qq:\1@]", raw_response)

    # 处理类似 `<1952b262 | message separator>` 模型幻觉续写的情况，截断其后的所有内容
    reg = r"<\w{8} \| message separator>"
    match = re.search(reg, raw_response)
    if match:
        raw_response = raw_response[: match.start()]

    # 检查是否存在多个 <think> 标签
    tags = ["<think>", "</think>"]
    for tag in tags:
        if raw_response.count(tag) > 1 and raw_response.endswith(tag):
            raw_response = raw_response[: -len(tag)]

    # logger.debug(f"Fixed raw response: {raw_response}")
    return raw_response.strip()
