import datetime
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from lunar_python import Lunar

from nekro_agent.core import config, logger
from nekro_agent.core.config import ModelConfigGroup
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.chat_message import (
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
)
from nekro_agent.tools.common_util import compress_image
from nekro_agent.tools.path_convertor import (
    convert_filename_to_access_path,
    get_sandbox_path,
)

from ..creator import ContentSegment, OpenAIChatMessage
from .base import PromptTemplate, register_template


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
        .limit(config.AI_CHAT_CONTEXT_MAX_LENGTH)
    )
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
                            f"<{one_time_code} | Image:{get_sandbox_path(seg.file_name)}>",
                            ContentSegment.image_content_from_path(str(compressed_path)),
                        ),
                    )
                    logger.info(f"压缩图片: {access_path.name} -> {compressed_path.stat().st_size / 1024}KB")
                else:
                    img_seg_pairs.append(
                        (
                            f"<{one_time_code} | Image:{get_sandbox_path(seg.file_name)}>",
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
            plugin_injected_prompt="",
            chat_key=chat_key,
            current_time=time.strftime("%Y-%m-%d %H:%M:%S %Z %A", time.localtime()),
            lunar_time=Lunar.fromDate(datetime.datetime.now()).toString(),
        ),
    )

    logger.debug(f"已加载到 {len(img_seg_pairs)} 张图片")
    img_seg_pairs = img_seg_pairs[::-1]  # 反转得到正确排序的 描述-图片 对
    if img_seg_pairs:
        openai_chat_message.add(
            ContentSegment.text_content(
                "Here are latest images in the chat history, carefully identify the image sender and use your vision if needed:",
            ),
        )
    for img_seg_prompt, img_seg_content in img_seg_pairs:
        openai_chat_message.add(ContentSegment.text_content(img_seg_prompt))
        openai_chat_message.add(img_seg_content)

    openai_chat_message.add(
        ContentSegment.text_content(
            "Recent Messages:\n",
        ),
    )

    chat_history_prompts: List[str] = []
    for db_message in recent_chat_messages:
        chat_history_prompts.append(db_message.parse_chat_history_prompt(one_time_code))

    chat_history_prompt = f"\n<{one_time_code} | message separator>\n".join(chat_history_prompts)
    chat_history_prompt += "\n<{one_time_code} | message separator>\n"
    openai_chat_message.add(ContentSegment.text_content(chat_history_prompt))

    logger.info(f"加载最近 {len(recent_chat_messages)} 条对话记录")

    return openai_chat_message
