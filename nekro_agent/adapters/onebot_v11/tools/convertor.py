import json
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


def extract_json_card_details(json_data: dict) -> tuple[str, dict[str, str | None]]:
    """从JSON卡片数据中提取详细信息

    Returns:
        tuple: (text_summary, card_info_dict)
    """
    card_info: dict[str, str | None] = {
        "title": None,
        "desc": None,
        "icon": None,
        "preview": None,
        "url": None,
        "share_from_nick": None,
    }

    # 优先级1：从meta字段中查找detail信息
    detail = _extract_detail_from_meta(json_data)
    if detail:
        # 提取应用标题
        if "title" in detail and isinstance(detail["title"], str):
            card_info["title"] = detail["title"].strip()
        # 提取应用描述
        if "desc" in detail and isinstance(detail["desc"], str):
            card_info["desc"] = detail["desc"].strip()
        # 提取应用图标
        if "icon" in detail and isinstance(detail["icon"], str):
            card_info["icon"] = detail["icon"]
        # 提取预览图
        if "preview" in detail and isinstance(detail["preview"], str):
            card_info["preview"] = detail["preview"]
        # 提取卡片链接（优先qqdocurl）
        if "qqdocurl" in detail and isinstance(detail["qqdocurl"], str):
            card_info["url"] = detail["qqdocurl"]
        elif "url" in detail and isinstance(detail["url"], str):
            card_info["url"] = detail["url"]
        # 提取分享者信息
        if "host" in detail and isinstance(detail["host"], dict):
            host = detail["host"]
            if "nick" in host and isinstance(host["nick"], str):
                card_info["share_from_nick"] = host["nick"]

    # 优先级2：如果meta中没有找到或字段为空，尝试从prompt字段提取
    if (not card_info["title"] or not str(card_info["title"]).strip()) and "prompt" in json_data:
        prompt = json_data["prompt"]
        if isinstance(prompt, str) and prompt.strip():
            # 移除[QQ小程序]前缀
            if prompt.startswith("[QQ小程序]"):
                prompt = prompt[len("[QQ小程序]") :].strip()
            if prompt:
                card_info["desc"] = prompt[:100]  # 取前100个字符作为描述

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
        seg: OneBot MessageSegment，类型为 'json'

    Returns:
        tuple: (text_summary, card_info, json_data) 或异常时返回 (fallback_text, {}, {})

    Raises:
        json.JSONDecodeError: JSON格式错误（预期的错误）
        Exception: 其他异常
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
    formatted: dict[str, str | None] = {
        "标题": None,
        "跳转链接": None,
        "转发人": None,
        "应用": None,
    }

    detail = _extract_detail_from_meta(json_data)
    if detail:
        # 标题：使用 desc 字段（卡片显示的主内容）
        if "desc" in detail and isinstance(detail["desc"], str):
            formatted["标题"] = detail["desc"]

        # 跳转链接（优先qqdocurl）
        if "qqdocurl" in detail and isinstance(detail["qqdocurl"], str):
            formatted["跳转链接"] = detail["qqdocurl"]
        elif "url" in detail and isinstance(detail["url"], str):
            formatted["跳转链接"] = detail["url"]

        # 转发人昵称
        if "host" in detail and isinstance(detail["host"], dict) and "nick" in detail["host"]:
            formatted["转发人"] = detail["host"]["nick"]

        # 转发自哪个应用（使用 title 作为应用名称）
        if "title" in detail and isinstance(detail["title"], str):
            formatted["应用"] = detail["title"]

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
                        text="[JSON卡片]",
                    ),
                )
            except Exception as e:
                logger.error(f"处理JSON卡片时发生意外错误: {e}", exc_info=True)
                # 降级为纯文本
                ret_list.append(
                    ChatMessageSegment(
                        type=ChatMessageSegmentType.TEXT,
                        text="[JSON卡片]",
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
