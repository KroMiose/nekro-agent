import datetime
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from lunar_python import Lunar
from pydantic import BaseModel, Field, ValidationError

from nekro_agent.core.config import CoreConfig, ModelConfigGroup, config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.chat_message import (
    ChatMessageSegmentImage,
)
from nekro_agent.services.memory.feature_flags import is_memory_system_enabled
from nekro_agent.tools.common_util import compress_image
from nekro_agent.tools.path_convertor import (
    convert_filename_to_access_path,
    convert_filename_to_sandbox_upload_path,
)

from ..creator import ContentSegment, OpenAIChatMessage
from .base import PromptTemplate, env, register_template

logger = get_sub_logger("agent_runtime")


class MemoryRecallQuerySpec(BaseModel):
    query_text: str
    focus_text: str = ""
    focus_points: list[str] = Field(default_factory=list)
    context_texts: list[str] = Field(default_factory=list)
    time_from: datetime.datetime | None = None
    time_to: datetime.datetime | None = None


class MemoryRecallPlan(BaseModel):
    queries: list[MemoryRecallQuerySpec] = Field(default_factory=list)


def _build_rule_based_memory_recall_query(recent_messages: List[DBChatMessage]) -> MemoryRecallQuerySpec | None:
    """从近期消息中构建更聚焦的记忆检索查询。

    优先关注：
    1. 最近窗口中的多个非 bot 主题
    2. 被引用的上一条消息
    3. 临近上下文中的关键句
    """
    non_bot_messages = [
        msg
        for msg in recent_messages
        if msg.sender_id != "-1" and msg.content_text and msg.content_text.strip()
    ]
    if not non_bot_messages:
        return None

    focus_messages: list[str] = []
    focus_points: list[str] = []
    focus_message = non_bot_messages[-1]
    focus_text = focus_message.content_text.strip()[:180]
    focus_messages.append(focus_text)
    focus_points.append(focus_text)

    ref_msg_id = focus_message.ext_data_obj.ref_msg_id
    if ref_msg_id:
        for msg in reversed(recent_messages):
            if msg.message_id == ref_msg_id and msg.content_text and msg.content_text.strip():
                quoted = msg.content_text.strip()[:180]
                focus_messages.append(quoted)
                if quoted not in focus_points:
                    focus_points.append(quoted)
                break

    for msg in reversed(non_bot_messages[:-1]):
        text = msg.content_text.strip()
        if not text:
            continue
        if text not in focus_messages:
            focus_messages.append(text[:120])
        short_text = text[:120]
        if short_text not in focus_points:
            focus_points.append(short_text)
        if len(focus_messages) >= 6:
            break

    return MemoryRecallQuerySpec(
        query_text="\n".join(focus_messages),
        focus_text=focus_text,
        focus_points=focus_points[:4],
        context_texts=focus_messages,
    )


async def _build_enhanced_memory_recall_plan(recent_messages: List[DBChatMessage]) -> MemoryRecallPlan | None:
    if not config.MEMORY_ENABLE_ENHANCED_RETRIEVAL:
        return None

    conversation_lines: list[str] = []
    for msg in recent_messages[-12:]:
        if not msg.content_text or not msg.content_text.strip():
            continue
        sender = msg.sender_nickname or msg.sender_name or f"User_{msg.sender_id}"
        if msg.sender_id == "-1":
            sender = "Assistant"
        content = msg.content_text.strip()[:400]
        conversation_lines.append(f"[{sender}] {content}")

    if not conversation_lines:
        return None

    prompt = (
        "请根据最近对话，为记忆检索生成结构化检索计划。\n"
        "目标：找出与当前用户真实关注点相关的历史记忆，而不是机械重复最后一句话。\n"
        "要求：\n"
        "1. 结合最近多轮对话理解用户当前任务。\n"
        "2. 如果最后一句是唤醒词、续接词、确认词或指代弱的短句，需要向前补全真实关注点。\n"
        "3. 可以输出 1 到 3 组 queries，用于不同角度召回。\n"
        "4. 每组 query_text 必须是自然语言检索语句，避免只有关键词堆砌。\n"
        "5. focus_points 应提炼关键约束、实体、目标或问题点。\n"
        "6. context_texts 应包含支撑该检索意图的近期上下文短句。\n"
        "7. 只有在最近对话明确出现时间线索时，才填写 time_from / time_to，否则填 null。\n"
        '8. 严格输出 JSON，对象格式为 {"queries":[...] }。\n'
        "9. 如果最近对话不足以构造有效检索计划，返回空数组 queries。\n\n"
        "JSON Schema:\n"
        "{\n"
        '  "queries": [\n'
        "    {\n"
        '      "query_text": "自然语言检索语句",\n'
        '      "focus_text": "本组检索的核心关注点",\n'
        '      "focus_points": ["关键点1", "关键点2"],\n'
        '      "context_texts": ["相关上下文1", "相关上下文2"],\n'
        '      "time_from": null,\n'
        '      "time_to": null\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "最近对话：\n"
        + "\n".join(conversation_lines)
    )

    try:
        from nekro_agent.services.agent.openai import gen_openai_chat_response, parse_extra_body

        model_group_name = config.MEMORY_ENHANCED_RETRIEVAL_MODEL_GROUP or config.USE_MODEL_GROUP
        model_group = config.get_model_group_info(model_group_name)
        extra_body = parse_extra_body(
            model_group.EXTRA_BODY,
            source_hint=f"Enhanced memory retrieval model group: {model_group_name}",
        ) or {}
        extra_body.setdefault("response_format", {"type": "json_object"})

        response = await gen_openai_chat_response(
            model=model_group.CHAT_MODEL,
            messages=[
                {"role": "system", "content": "你是一个记忆检索规划助手，负责为历史记忆检索生成结构化查询计划。"},
                {"role": "user", "content": prompt},
            ],
            api_key=model_group.API_KEY,
            base_url=model_group.BASE_URL,
            temperature=0.2,
            max_tokens=1200,
            extra_body=extra_body,
        )
        plan = MemoryRecallPlan.model_validate(json.loads(response.response_content))
        if not plan.queries:
            return None
        normalized_queries = [
            query
            for query in plan.queries
            if query.query_text.strip() and (query.context_texts or query.focus_text.strip())
        ][:3]
        if not normalized_queries:
            return None
        return MemoryRecallPlan(queries=normalized_queries)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"增强记忆检索规划解析失败，已回退规则检索: {e}")
        return None
    except Exception as e:
        logger.warning(f"增强记忆检索规划失败，已回退规则检索: {e}")
        return None


async def _build_memory_recall_plan(recent_messages: List[DBChatMessage]) -> MemoryRecallPlan:
    enhanced_plan = await _build_enhanced_memory_recall_plan(recent_messages)
    if enhanced_plan is not None:
        return enhanced_plan

    fallback_query = _build_rule_based_memory_recall_query(recent_messages)
    if fallback_query is None:
        return MemoryRecallPlan()
    return MemoryRecallPlan(queries=[fallback_query])


async def _inject_memory_context(
    workspace_id: int | None,
    recent_messages: List[DBChatMessage],
    max_memories: int = 8,
    max_length: int | None = None,
) -> str:
    """注入记忆上下文

    Args:
        workspace_id: 工作区 ID
        recent_messages: 近期消息列表（用于构建查询）
        max_memories: 最大记忆数量
        max_length: 最大字符长度

    Returns:
        记忆上下文字符串
    """
    if workspace_id is None or not is_memory_system_enabled():
        return ""
    if max_length is None:
        max_length = config.MEMORY_CONTEXT_MAX_LENGTH

    try:
        from nekro_agent.services.memory.retriever import (
            MemoryRecallQuery,
            compile_memories_for_context,
            retrieve_memories,
        )

        recall_plan = await _build_memory_recall_plan(recent_messages)
        if not recall_plan.queries:
            return ""

        aggregated_focus_points: list[str] = []
        aggregated_context_texts: list[str] = []
        aggregated_focus_text = ""
        deduped_memories: dict[tuple[str, int], Any] = {}

        for query_spec in recall_plan.queries:
            recall_query = MemoryRecallQuery(
                query_text=query_spec.query_text,
                focus_text=query_spec.focus_text,
                focus_points=query_spec.focus_points,
                context_texts=query_spec.context_texts,
                time_from=query_spec.time_from,
                time_to=query_spec.time_to,
            )
            if not aggregated_focus_text and recall_query.focus_text.strip():
                aggregated_focus_text = recall_query.focus_text
            for point in recall_query.focus_points:
                normalized_point = point.strip()
                if normalized_point and normalized_point not in aggregated_focus_points:
                    aggregated_focus_points.append(normalized_point)
            for text in recall_query.context_texts:
                normalized_text = text.strip()
                if normalized_text and normalized_text not in aggregated_context_texts:
                    aggregated_context_texts.append(normalized_text)

            memories = await retrieve_memories(
                workspace_id=workspace_id,
                query=recall_query.query_text,
                limit=max_memories,
                time_from=recall_query.time_from,
                time_to=recall_query.time_to,
            )
            for memory in memories:
                dedupe_key = (memory.source_type, memory.target_id)
                existing = deduped_memories.get(dedupe_key)
                if existing is None or memory.effective_weight > existing.effective_weight:
                    deduped_memories[dedupe_key] = memory

        memories = sorted(
            deduped_memories.values(),
            key=lambda item: item.effective_weight,
            reverse=True,
        )[:max_memories]

        if not memories:
            return ""

        compiled_recall_query = MemoryRecallQuery(
            query_text="\n".join(aggregated_context_texts) or recall_plan.queries[0].query_text,
            focus_text=aggregated_focus_text,
            focus_points=aggregated_focus_points[:6],
            context_texts=aggregated_context_texts[:8],
        )
        memory_context = await compile_memories_for_context(
            recall_query=compiled_recall_query,
            memories=memories,
            max_length=max_length,
        )
        return memory_context + "\n\n" if memory_context else ""

    except Exception as e:
        logger.debug(f"记忆注入失败（可忽略）: {e}")
        return ""


@register_template("history.j2", "history_first_start")
class HistoryFirstStart(PromptTemplate):
    enable_cot: bool


@register_template("history.j2", "history_debug_prompt")
class HistoryDebugPrompt(PromptTemplate):
    runout_reason: str
    code_output: str


@register_template("history.j2", "history_data")
class HistoryPrompt(PromptTemplate):
    plugin_injected_prompt: str
    chat_key: str
    current_time: str
    lunar_time: str


async def render_history_data(
    chat_key: str,
    db_chat_channel: DBChatChannel,
    one_time_code: str,
    config: CoreConfig,
    plugin_injected_prompt: str = "",
    record_sta_timestamp: Optional[float] = None,
    model_group: Optional[ModelConfigGroup] = None,
) -> OpenAIChatMessage:
    if record_sta_timestamp is None:
        record_sta_timestamp = int(time.time() - config.AI_CHAT_CONTEXT_EXPIRE_SECONDS)

    # 获取当前使用的模型组，如果没有传入则使用默认模型组
    if model_group is None:
        model_group = config.MODEL_GROUPS[config.USE_MODEL_GROUP]

    recent_chat_messages: List[DBChatMessage] = await (
        DBChatMessage.filter(
            send_timestamp__gte=max(record_sta_timestamp, db_chat_channel.conversation_start_time.timestamp()),
            chat_key=chat_key,
        )
        .order_by("-send_timestamp")
        .limit(config.AI_CHAT_CONTEXT_MAX_LENGTH * 3)
    )
    # 过滤掉较早的 System 消息，只保留最近 10 条消息中的前 3 条
    _to_remove_msgs: List[DBChatMessage] = []
    keep_system_msg_count = config.AI_SYSTEM_NOTIFY_WINDOW_SIZE
    for i, msg in enumerate(recent_chat_messages):
        if msg.is_system:
            if keep_system_msg_count > 0 and i < config.AI_SYSTEM_NOTIFY_LIMIT:
                keep_system_msg_count -= 1
            else:
                _to_remove_msgs.append(msg)
    recent_chat_messages = [msg for msg in recent_chat_messages if msg not in _to_remove_msgs]
    # 反转列表顺序并确保不超过最大长度
    recent_chat_messages = recent_chat_messages[::-1][-config.AI_CHAT_CONTEXT_MAX_LENGTH :]

    if not recent_chat_messages:
        return OpenAIChatMessage.from_text("user", "[Not new message revived yet]")

    # 提取并构造图片片段
    image_segments: List[ChatMessageSegmentImage] = []
    for db_message in recent_chat_messages:
        for seg in db_message.parse_content_data():
            if isinstance(seg, ChatMessageSegmentImage):
                image_segments.append(seg)

    img_seg_pairs: List[Tuple[str, Dict[str, Any]]] = []
    img_seg_set: Set[str] = set()
    if image_segments and model_group.ENABLE_VISION:
        for seg in image_segments[::-1]:
            if len(img_seg_set) >= config.AI_VISION_IMAGE_LIMIT:
                break
            if seg.local_path:
                if seg.file_name in img_seg_set:
                    continue
                access_path = convert_filename_to_access_path(seg.file_name, chat_key)
                if not access_path.exists():
                    logger.warning(f"图片不存在: {access_path}")
                    continue
                img_seg_set.add(seg.file_name)
                # 检查图片大小
                if access_path.stat().st_size > config.AI_VISION_IMAGE_SIZE_LIMIT_KB * 1024:
                    # 压缩图片
                    try:
                        compressed_path = compress_image(access_path, config.AI_VISION_IMAGE_SIZE_LIMIT_KB)
                    except Exception as e:
                        logger.error(f"压缩图片时发生错误: {e} | 图片路径: {access_path} 跳过处理...")
                        continue
                    img_seg_pairs.append(
                        (
                            f"<{one_time_code} | Image:{convert_filename_to_sandbox_upload_path(seg.file_name)}>",
                            ContentSegment.image_content_from_path(str(compressed_path)),
                        ),
                    )
                    logger.info(f"压缩图片: {access_path.name} -> {compressed_path.stat().st_size / 1024}KB")
                else:
                    img_seg_pairs.append(
                        (
                            f"<{one_time_code} | Image:{convert_filename_to_sandbox_upload_path(seg.file_name)}>",
                            ContentSegment.image_content_from_path(str(access_path)),
                        ),
                    )
            elif seg.remote_url:
                if seg.remote_url in img_seg_set:
                    continue
                img_seg_set.add(seg.remote_url)
                img_seg_pairs.append(
                    (
                        f"<{one_time_code} | Image:{seg.remote_url}>",
                        ContentSegment.image_content(seg.remote_url),
                    ),
                )
            else:
                logger.warning(f"图片路径无效: {seg}")

    openai_chat_message: OpenAIChatMessage = OpenAIChatMessage.from_template(
        "user",
        HistoryPrompt(
            plugin_injected_prompt=plugin_injected_prompt,
            chat_key=chat_key,
            current_time=time.strftime("%Y-%m-%d %H:%M:%S %Z %A", time.localtime()),
            lunar_time=Lunar.fromDate(datetime.datetime.now()).toString(),
        ),
        env,
    )

    logger.debug(f"已加载到 {len(img_seg_pairs)} 张图片")
    img_seg_pairs = img_seg_pairs[::-1]  # 反转得到正确排序的 描述-图片 对

    if img_seg_pairs:
        openai_chat_message.add(
            ContentSegment.text_content(
                f'<{one_time_code} | recent_chat_images count="{len(img_seg_pairs)}">\n'
                "Match each image to its corresponding message in Recent Messages by the path reference.\n\n",
            ),
        )
        for _idx, (img_seg_prompt, img_seg_content) in enumerate(img_seg_pairs, 1):
            # 从 img_seg_prompt 中提取路径: "<code | Image:path>" -> "path"
            img_path = img_seg_prompt.split("Image:")[-1].rstrip(">")
            openai_chat_message.add(
                ContentSegment.text_content(
                    f'<{one_time_code} | image path="{img_path}">\n',
                ),
            )
            openai_chat_message.add(img_seg_content)
            openai_chat_message.add(
                ContentSegment.text_content(
                    f"\n</{one_time_code} | image>\n\n",
                ),
            )
        openai_chat_message.add(
            ContentSegment.text_content(
                f"</{one_time_code} | recent_chat_images>\n\n",
            ),
        )

    # 注入记忆上下文
    memory_context = await _inject_memory_context(
        workspace_id=db_chat_channel.workspace_id,
        recent_messages=recent_chat_messages,
    )
    if memory_context:
        openai_chat_message.add(ContentSegment.text_content(memory_context))

    openai_chat_message.add(
        ContentSegment.text_content(
            "Recent Messages:\n",
        ),
    )

    ref_msg_set: Set[str] = set()
    for db_message in recent_chat_messages:
        if db_message.ext_data_obj.ref_msg_id:
            ref_msg_set.add(db_message.message_id)
            ref_msg_set.add(db_message.ext_data_obj.ref_msg_id)

    chat_history_prompts: List[str] = []
    for db_message in recent_chat_messages:
        chat_history_prompts.append(
            db_message.parse_chat_history_prompt(
                one_time_code,
                config,
                ref_mode=config.AI_ALWAYS_INCLUDE_MSG_ID or db_message.message_id in ref_msg_set,
            ),
        )

    # 确保总记录长度不超过最大字符长度（从后往前累积，保留较新的消息）
    total_length = 0
    start_idx = 0
    for i in range(len(chat_history_prompts) - 1, -1, -1):
        prompt_length = len(chat_history_prompts[i])
        if total_length + prompt_length > config.AI_CONTEXT_LENGTH_PER_SESSION:
            start_idx = i + 1  # 从下一条消息开始保留
            break
        total_length += prompt_length
    chat_history_prompts = chat_history_prompts[start_idx:]

    chat_history_prompt = f"\n<{one_time_code} | message separator>\n".join(chat_history_prompts)
    chat_history_prompt += f"\n<{one_time_code} | message separator>\n"
    openai_chat_message.add(ContentSegment.text_content(chat_history_prompt))

    logger.info(f"加载最近 {len(recent_chat_messages)} 条对话记录 ({len(ref_msg_set)} 条引用相关消息)")

    return openai_chat_message
