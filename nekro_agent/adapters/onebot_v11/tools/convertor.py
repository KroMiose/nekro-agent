import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Union

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GroupUploadNoticeEvent,
    Message,
    MessageEvent,
)

from nekro_agent.adapters.interface.base import BaseAdapter
from nekro_agent.adapters.onebot_v11.tools.onebot_util import get_user_group_card_name
from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import NAPCAT_TEMPFILE_DIR
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentAt,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentJsonCard,
    ChatMessageSegmentType,
    ChatType,
)

# JSON卡片处理常量
JSON_CARD_FALLBACK_TEXT = "[JSON卡片]"  # i18n: JSON Card fallback placeholder


@dataclass
class CardCore:
    """JSON卡片核心字段规范化结构

    用于统一提取 meta.detail 中的关键字段，减少解析过程中的重复判断
    """

    app_title: str | None = None  # meta.detail.title - 应用名称/标题
    card_desc: str | None = None  # meta.detail.desc - 卡片描述/内容
    url: str | None = None  # meta.detail.qqdocurl 或 meta.detail.url - 跳转链接
    host_nick: str | None = None  # meta.detail.host.nick - 分享者昵称
    icon: str | None = None  # meta.detail.icon - 图标
    preview: str | None = None  # meta.detail.preview - 预览图


def _get_str(detail: dict, key: str, strip: bool = False) -> str | None:
    """从 detail 字典中安全获取字符串值

    Args:
        detail: JSON卡片 detail 字典
        key: 字段名
        strip: 是否删除首尾空白

    Returns:
        字符串值或 None
    """
    value = detail.get(key)
    if isinstance(value, str):
        return value.strip() if strip else value
    return None


def _extract_card_core(json_data: dict) -> CardCore:
    """从JSON卡片中提取规范化的核心字段

    统一处理 meta/detail 的提取逻辑，减少两个函数间的重复代码

    Args:
        json_data: 完整的JSON卡片数据

    Returns:
        CardCore 实例，包含提取到的关键字段
    """
    detail = _extract_detail_from_meta(json_data)
    if detail is None:
        return CardCore()

    # 优先级：qqdocurl > url
    url = None
    if isinstance(detail.get("qqdocurl"), str):
        url = detail["qqdocurl"]
    elif isinstance(detail.get("url"), str):
        url = detail["url"]

    # 安全提取 host.nick
    host_data = detail.get("host")
    host_nick = host_data.get("nick") if isinstance(host_data, dict) and isinstance(host_data.get("nick"), str) else None

    return CardCore(
        app_title=_get_str(detail, "title", strip=True),
        card_desc=_get_str(detail, "desc", strip=True),
        url=url,
        host_nick=host_nick,
        icon=_get_str(detail, "icon"),
        preview=_get_str(detail, "preview"),
    )


def extract_json_card_details(json_data: dict) -> tuple[str, dict[str, str | None]]:
    """从JSON卡片数据中提取详细信息

    Returns:
        tuple: (text_summary, card_info_dict)
    """
    core = _extract_card_core(json_data)

    card_info: dict[str, str | None] = {
        "title": core.app_title,
        "desc": core.card_desc,
        "icon": core.icon,
        "preview": core.preview,
        "url": core.url,
        "share_from_nick": core.host_nick,
    }

    # Fallback: 如果没有 title，尝试从 prompt 字段提取
    if (not card_info["title"] or not str(card_info["title"]).strip()) and "prompt" in json_data:
        prompt = json_data["prompt"]
        if isinstance(prompt, str) and prompt.strip():
            # 移除[QQ小程序]前缀
            if prompt.startswith("[QQ小程序]"):
                prompt = prompt[len("[QQ小程序]") :].strip()
            if prompt:
                card_info["desc"] = prompt[:100]

    # 生成文本摘要
    text_summary = _generate_json_card_summary(card_info)

    return text_summary, card_info


def _generate_json_card_summary(card_info: dict[str, str | None]) -> str:
    """根据提取的卡片信息生成文本摘要

    Args:
        card_info: 包含title, desc, share_from_nick, url等的字典

    Returns:
        str: 格式化的摘要文本
        格式：[卡片消息]由{转发人昵称}转发自{应用名称}的标题为{标题}的卡片消息，链接（如有）为{链接}
    """
    # 提取各个字段，并过滤掉空字符串
    share_from_nick = card_info.get("share_from_nick") or None
    app_name = (card_info.get("title") or "").strip() or None  # 应用名称
    card_title = (card_info.get("desc") or "").strip() or None  # 卡片标题
    url = card_info.get("url") or None

    # 如果连标题和应用名都没有，降级处理
    if not card_title and not app_name:
        # 即使没有标题和应用名，也要包含分享者或链接信息
        fallback_parts = ["[卡片消息]"]
        if share_from_nick:
            fallback_parts.append(f"由{share_from_nick}分享")
        if url:
            # 截断长URL，只保留前50个字符
            display_url = url if len(url) <= 50 else f"{url[:50]}..."
            fallback_parts.append(f"链接:{display_url}")
        result = "".join(fallback_parts)
        return result if len(result) > 4 else "[卡片消息]"

    # 构建消息文本
    parts = ["[卡片消息]"]

    # 添加转发人信息
    if share_from_nick:
        parts.append(f"由{share_from_nick}")

    # 添加应用名称
    if app_name:
        if share_from_nick:
            parts.append(f"转发自{app_name}的")
        else:
            parts.append(f"来自{app_name}的")

    # 添加标题
    if card_title:
        # 移除引号并截断
        if card_title.startswith('"') and card_title.endswith('"'):
            card_title = card_title[1:-1]
        parts.append(f'标题为"{card_title}"的')

    parts.append("卡片消息")

    # 添加链接（如果有）
    if url:
        # 截断长URL
        display_url = url if len(url) <= 50 else f"{url[:50]}..."
        parts.append(f"，链接为{display_url}")

    return "".join(parts)


def parse_onebot_json_segment(seg: dict) -> tuple[str, dict[str, str | None], dict]:
    """解析OneBot JSON卡片消息段

    Args:
        seg: OneBot MessageSegment 的 data 字典（包含 "data" 键的字典）

    Returns:
        tuple: (text_summary, card_info, json_data)
        - text_summary: 格式化后的卡片摘要文本
        - card_info: 提取的卡片关键信息字典
        - json_data: 解析后的完整JSON数据

    Raises:
        json.JSONDecodeError: 当 JSON 格式错误时抛出
        Exception: 其他异常情况

    Note:
        异常由调用方负责捕获和处理，调用方应构造降级文本
    """
    json_str = seg.get("data", "")
    json_data = json.loads(json_str) if isinstance(json_str, str) else json_str

    # 记录原始JSON（调试用）
    logger.debug(f"收到JSON卡片(原始): {json.dumps(json_data, ensure_ascii=False)}")

    # 记录格式化后的关键字段（日常使用）
    formatted_card = format_json_card_for_log(json_data)
    logger.info(f"收到JSON卡片: {json.dumps(formatted_card, ensure_ascii=False)}")

    # 提取卡片详细信息
    text_summary, card_info = extract_json_card_details(json_data)

    return text_summary, card_info, json_data


def format_json_card_for_log(json_data: dict) -> dict:
    """格式化JSON卡片用于日志输出，只保留关键字段

    Args:
        json_data: 完整的JSON卡片数据

    Returns:
        dict: 包含关键字段的字典 {标题, 跳转链接, 转发人, 应用}
    """
    core = _extract_card_core(json_data)

    formatted: dict[str, str | None] = {
        "标题": core.card_desc,
        "跳转链接": core.url,
        "转发人": core.host_nick,
        "应用": core.app_title,
    }

    # 只返回非空字段，保持日志简洁
    return {k: v for k, v in formatted.items() if v is not None} or {"提示": "无法解析卡片信息"}


def _extract_detail_from_meta(json_data: dict) -> dict | None:
    """从JSON卡片的meta中提取第一个有效的detail

    Args:
        json_data: 完整的JSON卡片数据

    Returns:
        第一个有效的detail字典，如果没有则返回None
    """
    if "meta" not in json_data or not isinstance(json_data["meta"], dict):
        return None

    meta = json_data["meta"]
    for detail_key in ["detail_1", "detail_2", "detail_3"]:
        if detail_key in meta and isinstance(meta[detail_key], dict):
            detail = meta[detail_key]
            # 检查是否包含至少一个有效字段
            if any(detail.get(k) for k in ["title", "desc", "url", "qqdocurl"]):
                return detail

    return None


async def convert_chat_message(
    ob_event: Union[MessageEvent, GroupMessageEvent, GroupUploadNoticeEvent],
    msg_to_me: bool,
    bot: Bot,  # noqa: ARG001
    db_chat_channel: DBChatChannel,
    adapter: BaseAdapter,
) -> Tuple[List[ChatMessageSegment], bool, str]:
    """转换 OneBot 消息为 ChatMessageSegment 列表

    Args:
        ob_message (Message): OneBot 消息

    Returns:
        List[ChatMessageSegment]: ChatMessageSegment 列表
        bool: 是否为机器人发送的消息
        str: 消息 ID
    """

    ret_list: List[ChatMessageSegment] = []
    is_tome = False

    if isinstance(ob_event, GroupUploadNoticeEvent):
        if ob_event.file.size > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            logger.warning(f"文件过大，跳过处理: {ob_event.file.name}")
            return ret_list, False, ""
        if ob_event.file.model_extra and ob_event.file.model_extra.get("url"):
            suffix = "." + ob_event.file.name.rsplit(".", 1)[-1]
            if not ob_event.file.model_extra["url"].startswith("http"):
                logger.warning(f"上传文件无法获取到直链: {ob_event.file.model_extra['url']}")
                return ret_list, False, ""
            ret_list.append(
                await ChatMessageSegmentFile.create_from_url(
                    url=ob_event.file.model_extra["url"],
                    from_chat_key=db_chat_channel.chat_key,
                ),
            )
        elif ob_event.file.id:
            file_data = await bot.get_file(file_id=ob_event.file.id)
            logger.debug(f"获取文件: {file_data}")
            # TODO: 获取文件: {'file': '/app/.config/QQ/NapCat/temp/XXXXXX.csv', 'url': '/app/.config/QQ/NapCat/temp/XXXXXX.csv', 'file_size': '1079', 'file_name': 'XXXXXX.csv'}
            # napcat 挂载目录 ${NEKRO_DATA_DIR}/napcat_data/QQ:/app/.config/QQ
            target_file_path = str(Path(NAPCAT_TEMPFILE_DIR) / file_data["file_name"])
            if Path(target_file_path).exists():
                ret_list.append(
                    await ChatMessageSegmentFile.create_form_local_path(
                        local_path=target_file_path,
                        from_chat_key=db_chat_channel.chat_key,
                        file_name=file_data["file_name"],
                    ),
                )
            else:
                logger.warning(f"文件不存在: {target_file_path}")
        else:
            logger.debug(f"无法处理的文件消息: {ob_event.file}")

        return ret_list, False, ""

    ob_message: Message = ob_event.message
    message_id: str = str(ob_event.message_id)

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
                if "filename" in seg.data:
                    suffix = "." + seg.data["filename"].split(".")[-1].lower()
                elif "file_id" in seg.data:
                    suffix = "." + seg.data["file_id"].split(".")[-1].lower()
                else:
                    suffix = "." + seg.data["file"].split(".")[-1].lower()
                if len(suffix) > 10:
                    logger.warning(f"文件后缀过长: {suffix}; from: {seg=}; 取消后缀")
                    suffix = ""
            except Exception:
                suffix = ""
            if "url" in seg.data:
                remote_url: str = seg.data["url"]
                ret_list.append(
                    await ChatMessageSegmentImage.create_from_url(
                        url=remote_url,
                        from_chat_key=db_chat_channel.chat_key,
                        use_suffix=suffix,
                    ),
                )
            elif "file" in seg.data:
                seg_local_path = seg.data["file"]
                if seg_local_path.startswith("file:"):
                    seg_local_path = seg_local_path[len("file:") :]
                ret_list.append(
                    await ChatMessageSegmentImage.create_form_local_path(
                        local_path=seg_local_path,
                        from_chat_key=db_chat_channel.chat_key,
                        use_suffix=suffix,
                    ),
                )
            else:
                logger.warning(f"OneBot image message without url: {seg}")
                continue

        elif seg.type == "at":
            assert isinstance(ob_event, GroupMessageEvent)
            at_qq = str(seg.data["qq"])
            bot_qq = (await adapter.get_self_info()).user_id
            if at_qq == bot_qq:
                at_qq = bot_qq
                is_tome = True
                nick_name = (await db_chat_channel.get_preset()).name
            else:
                nick_name = await get_user_group_card_name(
                    group_id=ob_event.group_id,
                    user_id=at_qq,
                    db_chat_channel=db_chat_channel,
                )
            logger.info(f"OneBot at message: {at_qq=} {nick_name=}")
            if not adapter.config.SESSION_ENABLE_AT:
                ret_list.append(
                    ChatMessageSegment(
                        type=ChatMessageSegmentType.TEXT,
                        text=f"@{nick_name}",
                    ),
                )
            else:
                logger.info(f"Session Allow At: {nick_name}")
                ret_list.append(
                    ChatMessageSegmentAt(
                        type=ChatMessageSegmentType.AT,
                        text="",
                        target_platform_userid=at_qq,
                        target_nickname=nick_name,
                    ),
                )

        elif seg.type == "file":
            if "size" in seg.data and seg.data["size"] > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                file_name = seg.data.get("name", "unknown")
                logger.warning(f"文件过大，跳过处理: {file_name}")
                continue
            if "url" in seg.data:
                ret_list.append(
                    await ChatMessageSegmentFile.create_from_url(
                        url=seg.data["url"],
                        from_chat_key=db_chat_channel.chat_key,
                    ),
                )
            elif "file" in seg.data:
                file_path = seg.data["file"]
                if file_path.startswith("file:"):
                    file_path = file_path[len("file:") :]
                ret_list.append(
                    await ChatMessageSegmentFile.create_form_local_path(
                        local_path=file_path,
                        from_chat_key=db_chat_channel.chat_key,
                        file_name=seg.data.get("name", ""),
                    ),
                )
            else:
                logger.warning(f"OneBot file message without url or file: {seg}")
                continue

        elif seg.type == "json":
            try:
                text_summary, card_info, json_data = parse_onebot_json_segment(seg.data)

                ret_list.append(
                    ChatMessageSegmentJsonCard(
                        type=ChatMessageSegmentType.JSON_CARD,
                        text=text_summary,
                        json_data=json_data,
                        card_title=card_info.get("title"),
                        card_desc=card_info.get("desc"),
                        card_icon=card_info.get("icon"),
                        card_preview=card_info.get("preview"),
                        card_url=card_info.get("url"),
                        share_from_nick=card_info.get("share_from_nick"),
                    ),
                )
            except json.JSONDecodeError as e:
                logger.warning(f"JSON卡片解析失败（格式错误）: {e}")
                # 降级为纯文本
                ret_list.append(
                    ChatMessageSegment(
                        type=ChatMessageSegmentType.TEXT,
                        text=JSON_CARD_FALLBACK_TEXT,
                    ),
                )
            except Exception as e:
                logger.error(f"处理JSON卡片时发生意外错误: {e}", exc_info=True)
                # 降级为纯文本
                ret_list.append(
                    ChatMessageSegment(
                        type=ChatMessageSegmentType.TEXT,
                        text=JSON_CARD_FALLBACK_TEXT,
                    ),
                )

    if msg_to_me and not is_tome:
        is_tome = True
        ret_list.insert(
            0,
            ChatMessageSegmentAt(
                type=ChatMessageSegmentType.AT,
                text="",
                target_platform_userid=(await adapter.get_self_info()).user_id,
                target_nickname=(await db_chat_channel.get_preset()).name,
            ),
        )

    return ret_list, is_tome, message_id


def get_channel_type(channel_id: str) -> ChatType:
    try:
        chat_type, _ = channel_id.split("_")
        return ChatType(chat_type)
    except ValueError as e:
        raise ValueError(f"Invalid channel id: {channel_id}") from e
