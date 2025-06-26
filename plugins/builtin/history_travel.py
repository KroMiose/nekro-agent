"""
# 漫游历史 (History Travel)

赋予 AI 超越当前对话窗口、回顾和检索完整历史聊天记录的能力。

## 设计理念：历史回溯

AI 的"记忆"（即对话上下文）是有限的，它只能看到最近的几十条消息。当需要回顾很久以前的对话时，这个插件就派上了用场。它就像一个历史记录浏览器，允许 AI "穿越"回过去的任意时间点，查看当时的对话，从而获取完成当前任务所需的旧信息。

这极大地扩展了 AI 的记忆广度，使其能够处理需要长期上下文的复杂任务。

## 主要功能

- **关键词检索**: AI 可以使用关键词（支持 `与/或/非` 的高级搜索语法）在海量的历史记录中进行精确查找。
- **上下文漫游**: 当 AI 通过关键词定位到一条相关的旧消息后，可以进一步获取该消息前后的完整对话，从而精准地"回溯"到当时的场景，全面理解上下文。

## 使用方法

此插件主要由 AI 在后台根据任务需要自动调用。例如：
- 当用户问"我们上次讨论那个项目计划是什么时候？"时，AI 会使用"关键词检索"找到相关的记录。
- 找到记录后，为了解详情，它可能会接着使用"上下文漫游"来查看完整的讨论过程。
"""

import datetime
from typing import List

from pydantic import Field

from nekro_agent.api import core, schemas
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage

plugin = NekroPlugin(
    name="漫游历史记录",
    module_name="history_travel",
    description="提供历史聊天记录精确检索与漫游能力",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class StatusConfig(ConfigBase):
    """状态控制配置"""

    MAX_HISTORY_TRAVEL_QUERY_SIZE: int = Field(default=8, title="漫游记录泛查询数量")
    MAX_HISTORY_TRAVEL_RANGE_QUERY_SIZE: int = Field(default=16, title="漫游记录范围查询最大数量")


# 获取配置和插件存储
config = plugin.get_config(StatusConfig)
store = plugin.store


# region: 漫游消息处理方法
def parse_history_travel_message(db_chat_message: DBChatMessage, config: core.CoreConfig) -> str:
    """解析漫游消息"""
    return db_chat_message.parse_chat_history_prompt("", config, ref_mode=True)


# endregion: 漫游消息处理方法


@plugin.mount_prompt_inject_method("history_travel_prompt")
async def history_travel_prompt(_ctx: schemas.AgentCtx) -> str:
    """漫游记录提示"""
    return ""


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "漫游记录泛查询")
async def find_history_travel(_ctx: schemas.AgentCtx, chat_key: str, keywords: List[str]):
    """Search chat history by keywords

    Args:
        chat_key: Chat unique identifier
        keywords: List of short keywords to search for.
                 Use prefix "+word" for AND (must include),
                 prefix "-word" for NOT (must exclude),
                 normal "word" for OR (any match).

    Examples:
        >>> find_history_travel(_ck, ["吃饭", "午饭"]) # Find messages containing either "吃饭" OR "午饭"
        >>> find_history_travel(_ck, ["+吃饭", "+午饭"]) # Find messages containing BOTH "吃饭" AND "午饭"
        >>> find_history_travel(_ck, ["晚餐", "-鱼"]) # Find messages containing "晚餐" but NOT "鱼"
        "Stop and wait for the result..."
    """
    db_chat_channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not db_chat_channel:
        raise ValueError("未找到会话")

    core_config = await db_chat_channel.get_effective_config()
    conversation_start_time: datetime.datetime = db_chat_channel.conversation_start_time
    conversation_start_timestamp = int(conversation_start_time.timestamp())

    # 安全地获取上下文截止时间点
    # 首先获取最近的消息总数
    total_messages = await DBChatMessage.filter(chat_key=chat_key).count()

    context_cutoff_timestamp = 0
    # 只有当消息数量超过上下文大小时才设置截止时间
    if total_messages > core_config.AI_CHAT_CONTEXT_MAX_LENGTH:
        # 获取上下文边界消息
        oldest_context_message = (
            await DBChatMessage.filter(chat_key=chat_key)
            .order_by("-send_timestamp")  # 按时间降序排列
            .offset(core_config.AI_CHAT_CONTEXT_MAX_LENGTH - 1)  # 跳过最近的N-1条
            .limit(1)  # 只取一条
            .first()
        )

        if oldest_context_message:
            context_cutoff_timestamp = oldest_context_message.send_timestamp

    # 分类关键词
    or_keywords = []  # 或关系(默认)
    and_keywords = []  # 与关系(必须包含)
    not_keywords = []  # 非关系(必须排除)

    for keyword in keywords:
        if keyword.startswith("+"):
            and_keywords.append(keyword[1:])
        elif keyword.startswith("-"):
            not_keywords.append(keyword[1:])
        else:
            or_keywords.append(keyword)

    # 记录日志，方便调试
    logger.info(f"搜索会话 {chat_key} 中的关键词，OR: {or_keywords}, AND: {and_keywords}, NOT: {not_keywords}")
    logger.info(f"上下文截止时间戳: {context_cutoff_timestamp}")

    # 构建基础查询
    base_query = DBChatMessage.filter(
        chat_key=chat_key,
        send_timestamp__gte=conversation_start_timestamp,
    )

    # 添加上下文截止时间条件
    if context_cutoff_timestamp > 0:
        base_query = base_query.filter(send_timestamp__lt=context_cutoff_timestamp)

    # 处理OR关键词
    db_chat_message_list = []
    db_chat_msg_id_set = set()
    keyword_match_count = {}  # 记录每条消息匹配的关键词数量

    if or_keywords:
        # 如果有OR关键词，先按OR关系查询
        for keyword in or_keywords:
            query = base_query.filter(content_text__icontains=keyword)

            db_chat_message = await query.order_by("-update_time").limit(config.MAX_HISTORY_TRAVEL_QUERY_SIZE * 4).all()

            # 记录每个关键词的结果数量
            logger.info(f"OR关键词 '{keyword}' 匹配到 {len(db_chat_message)} 条消息")

            for msg in db_chat_message:
                if msg.id not in db_chat_msg_id_set:
                    db_chat_message_list.append(msg)
                    db_chat_msg_id_set.add(msg.id)
                    keyword_match_count[msg.id] = 1
                else:
                    # 增加已存在消息的关键词匹配计数
                    keyword_match_count[msg.id] = keyword_match_count.get(msg.id, 0) + 1
    else:
        # 如果没有OR关键词，则查询所有消息
        db_chat_message = await base_query.order_by("-update_time").limit(config.MAX_HISTORY_TRAVEL_QUERY_SIZE * 4).all()
        for msg in db_chat_message:
            db_chat_message_list.append(msg)
            db_chat_msg_id_set.add(msg.id)
            keyword_match_count[msg.id] = 0

    # 处理AND和NOT关键词进行过滤
    filtered_messages = []
    for msg in db_chat_message_list:
        # 检查是否满足AND条件
        and_match = True
        for keyword in and_keywords:
            if keyword.lower() not in msg.content_text.lower():
                and_match = False
                break

        if not and_match:
            continue

        # 检查是否满足NOT条件
        not_match = False
        for keyword in not_keywords:
            if keyword.lower() in msg.content_text.lower():
                not_match = True
                break

        if not_match:
            continue

        # 通过了所有条件，添加到结果
        filtered_messages.append(msg)

        # 更新匹配分数 - AND关键词匹配增加更高权重
        for keyword in and_keywords:
            if keyword.lower() in msg.content_text.lower():
                keyword_match_count[msg.id] = keyword_match_count.get(msg.id, 0) + 2

    # 先按关键词匹配数量和更新时间排序，选出最相关的消息
    relevant_messages = sorted(filtered_messages, key=lambda x: (-keyword_match_count.get(x.id, 0), x.update_time))[
        : config.MAX_HISTORY_TRAVEL_QUERY_SIZE
    ]

    # 最后按发送时间戳从早到晚排序，确保消息按时间顺序呈现
    result_messages = sorted(relevant_messages, key=lambda x: x.send_timestamp)

    # 记录最终返回的消息数量
    logger.info(f"最终返回 {len(result_messages)} 条消息")

    # 如果没有找到任何结果，返回特殊提示
    if not result_messages:
        not_msg = f", NOT: {', '.join(not_keywords)}" if not_keywords else ""
        and_msg = f", AND: {', '.join(and_keywords)}" if and_keywords else ""
        or_msg = f"OR: {', '.join(or_keywords)}" if or_keywords else "no keywords"
        return f"[No messages found matching {or_msg}{and_msg}{not_msg}]"

    additional_info = f"\n\n[Query {len(result_messages)} messages. You NEED to use the 'find_history_travel_range' method to get more context around a specific message. DO NOT GUESS THE EXACT CONTEXT ACCORDING TO THE SIMPLIFIED MESSAGE.]"

    return "\n\n".join([parse_history_travel_message(msg, core_config) for msg in result_messages]) + additional_info


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "漫游记录范围查询")
async def find_history_travel_range(
    _ctx: schemas.AgentCtx,
    chat_key: str,
    base_msg_id: str,
    prev_count: int = 2,
    next_count: int = 10,
):
    """Search chat history around a specific message (Useful for finding the context of a specific message or reference message)

    Args:
        chat_key: Chat unique identifier
        base_msg_id: Base message ID
        prev_count: Number of messages to fetch before the base message (default: 2)
        next_count: Number of messages to fetch after the base message (default: 10)

    Examples:
        >>> find_history_travel_range(_ck, "xxxxxx") # Get from the 2nd message before to the 10th message after the message with ID xxxxxx
        "Stop and wait for the result..."
    """
    if prev_count + next_count > config.MAX_HISTORY_TRAVEL_RANGE_QUERY_SIZE:
        raise ValueError("查询范围过大")

    db_chat_channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not db_chat_channel:
        raise ValueError("未找到会话")

    base_message = await DBChatMessage.get_or_none(message_id=base_msg_id)
    if not base_message:
        raise ValueError("未找到消息")

    db_chat_channel = await DBChatChannel.get(chat_key=chat_key)
    core_config = await db_chat_channel.get_effective_config()

    # 查询前的消息
    prev_messages = (
        await DBChatMessage.filter(
            chat_key=chat_key,
            send_timestamp__lt=base_message.send_timestamp,
        )
        .order_by("-send_timestamp")
        .limit(prev_count)
    )[
        ::-1
    ]  # 反转以确保时间顺序

    # 查询后的消息
    next_messages = (
        await DBChatMessage.filter(
            chat_key=chat_key,
            send_timestamp__gt=base_message.send_timestamp,
        )
        .order_by("send_timestamp")
        .limit(next_count)
    )

    result_messages = [*prev_messages, base_message, *next_messages]

    result = "\n\n".join([parse_history_travel_message(msg, core_config) for msg in result_messages])

    # 添加超限说明
    if len(result_messages) >= config.MAX_HISTORY_TRAVEL_RANGE_QUERY_SIZE:
        result += "\n\n[The number of returned messages has reached the query limit. If you need more context, please make another query.]"

    return result


@plugin.mount_on_channel_reset()
async def on_channel_reset(_ctx: schemas.AgentCtx):
    """重置插件状态"""


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
