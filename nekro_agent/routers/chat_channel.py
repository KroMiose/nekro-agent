from pathlib import Path
from typing import Any, Dict, List, Optional

import json5
from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from tortoise.expressions import Q

from nekro_agent.adapters import get_adapter
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import USER_UPLOAD_DIR
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.agent_message import AgentMessageSegment, AgentMessageSegmentType
from nekro_agent.schemas.errors import NotFoundError
from nekro_agent.services.config_resolver import config_resolver
from nekro_agent.services.message_service import message_service
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/chat-channel", tags=["ChatChannel"])

logger = get_sub_logger("chat_channel_api")


class ChatChannelItem(BaseModel):
    id: int
    chat_key: str
    channel_name: Optional[str]
    is_active: bool
    chat_type: str
    message_count: int
    create_time: str
    update_time: str
    last_message_time: Optional[str]


class ChatChannelListResponse(BaseModel):
    total: int
    items: List[ChatChannelItem]


class ChatChannelDetail(ChatChannelItem):
    unique_users: int
    conversation_start_time: str
    preset_id: Optional[int]
    can_send: bool = False
    ai_always_include_msg_id: bool = False


class ChatMessage(BaseModel):
    id: int
    sender_id: str
    sender_name: str
    sender_nickname: str
    platform_userid: str
    content: str
    content_data: List[Dict[str, Any]]
    chat_key: str
    create_time: str
    message_id: str = ""
    ref_msg_id: str = ""


class ChatMessageListResponse(BaseModel):
    total: int
    items: List[ChatMessage]


class ActionResponse(BaseModel):
    ok: bool = True


@router.get("/list", summary="获取聊天频道列表")
@require_role(Role.Admin)
async def get_chat_channel_list(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    chat_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ChatChannelListResponse:
    """获取聊天频道列表"""
    query = DBChatChannel

    if search:
        query = query.filter(
            Q(chat_key__contains=search) | Q(channel_name__contains=search),
        )
    if chat_type:
        query = query.filter(chat_key__contains=f"{chat_type}_")
    if is_active is not None:
        query = query.filter(is_active=is_active)

    channels = await query.all()

    channel_info_list = []
    for channel in channels:
        message_count = await DBChatMessage.filter(
            chat_key=channel.chat_key,
            create_time__gte=channel.conversation_start_time,
        ).count()

        last_message = await DBChatMessage.filter(chat_key=channel.chat_key).order_by("-create_time").first()

        conversation_start_time = channel.conversation_start_time
        if conversation_start_time.tzinfo is not None:
            conversation_start_time = conversation_start_time.replace(tzinfo=None)

        if last_message:
            last_message_time = last_message.create_time
            if last_message_time.tzinfo is not None:
                last_message_time = last_message_time.replace(tzinfo=None)
            last_active_time = max(conversation_start_time, last_message_time)
        else:
            last_active_time = conversation_start_time

        channel_info_list.append(
            {
                "channel": channel,
                "message_count": message_count,
                "last_active_time": last_active_time,
                "last_message_time": last_message_time if last_message else None,
            },
        )

    channel_info_list.sort(key=lambda x: x["last_active_time"], reverse=True)

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_channels = channel_info_list[start_idx:end_idx]

    result: List[ChatChannelItem] = []
    for info in paged_channels:
        channel = info["channel"]
        result.append(
            ChatChannelItem(
                id=channel.id,
                chat_key=channel.chat_key,
                channel_name=channel.channel_name,
                is_active=channel.is_active,
                chat_type=channel.chat_type.value,
                message_count=info["message_count"],
                create_time=channel.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                update_time=channel.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                last_message_time=(
                    info["last_message_time"].strftime("%Y-%m-%d %H:%M:%S") if info["last_message_time"] is not None else None
                ),
            ),
        )

    return ChatChannelListResponse(
        total=len(channels),
        items=result,
    )


@router.get("/list/stream", summary="获取聊天频道列表实时流")
@require_role(Role.Admin)
async def stream_chat_channel_list(
    _current_user: DBUser = Depends(get_current_active_user),
):
    """获取聊天频道列表的实时更新流，使用 Server-Sent Events (SSE)

    Returns:
        StreamingResponse: SSE 流，每条频道事件作为一个数据

    Events:
        - created: 新频道创建
        - updated: 频道信息更新
        - deleted: 频道被删除
        - activated: 频道被激活
        - deactivated: 频道被停用
    """
    import json

    from fastapi.responses import StreamingResponse

    from nekro_agent.services.channel_broadcaster import channel_broadcaster

    async def event_generator():
        """生成 SSE 事件流"""
        async for event in channel_broadcaster.subscribe():
            # 以 SSE 事件格式发送
            yield f"data: {json.dumps(event.model_dump())}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/detail/{chat_key}", summary="获取聊天频道详情")
@require_role(Role.Admin)
async def get_chat_channel_detail(chat_key: str, _current_user: DBUser = Depends(get_current_active_user)) -> ChatChannelDetail:
    """获取聊天频道详情"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        raise NotFoundError(resource="聊天频道")

    message_count = await DBChatMessage.filter(chat_key=chat_key, create_time__gte=channel.conversation_start_time).count()
    last_message = await DBChatMessage.filter(chat_key=chat_key).order_by("-create_time").first()
    last_message_time = last_message.create_time if last_message else None
    unique_users = await DBChatMessage.filter(chat_key=chat_key).distinct().values_list("sender_id", flat=True)

    # 检测适配器是否支持 WebUI 发送
    can_send = False
    try:
        adapter = get_adapter(channel.adapter_key)
        can_send = adapter.supports_webui_send
    except Exception:
        pass

    # 获取频道有效配置
    ai_always_include_msg_id = False
    try:
        effective_config = await config_resolver.get_effective_config(chat_key)
        ai_always_include_msg_id = effective_config.AI_ALWAYS_INCLUDE_MSG_ID
    except Exception:
        pass

    return ChatChannelDetail(
        id=channel.id,
        chat_key=channel.chat_key,
        channel_name=channel.channel_name,
        is_active=channel.is_active,
        chat_type=channel.chat_type.value,
        message_count=message_count,
        unique_users=len(unique_users),
        create_time=channel.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        update_time=channel.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        last_message_time=last_message_time.strftime("%Y-%m-%d %H:%M:%S") if last_message_time else None,
        conversation_start_time=channel.conversation_start_time.strftime("%Y-%m-%d %H:%M:%S"),
        preset_id=channel.preset_id,
        can_send=can_send,
        ai_always_include_msg_id=ai_always_include_msg_id,
    )


@router.post("/{chat_key}/active", summary="设置聊天频道激活状态")
@require_role(Role.Admin)
async def set_chat_channel_active(
    chat_key: str,
    is_active: bool,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """设置聊天频道激活状态"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        raise NotFoundError(resource="聊天频道")

    await channel.set_active(is_active)
    return ActionResponse(ok=True)


@router.post("/{chat_key}/reset", summary="重置聊天频道状态")
@require_role(Role.Admin)
async def reset_chat_channel(
    chat_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """重置聊天频道状态"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        raise NotFoundError(resource="聊天频道")

    await channel.reset_channel()
    return ActionResponse(ok=True)


@router.get("/{chat_key}/messages", summary="获取聊天频道消息列表")
@require_role(Role.Admin)
async def get_chat_channel_messages(
    chat_key: str,
    before_id: Optional[int] = None,
    page_size: int = 32,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ChatMessageListResponse:
    """获取聊天频道消息列表"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        raise NotFoundError(resource="聊天频道")

    query = DBChatMessage.filter(chat_key=chat_key, create_time__gte=channel.conversation_start_time)
    if before_id:
        query = query.filter(id__lt=before_id)

    total = await query.count()
    messages = await query.order_by("-id").limit(page_size)

    def _parse_content_data(raw: str) -> List[Dict[str, Any]]:
        try:
            return json5.loads(raw) if raw else []
        except Exception:
            return []

    def _safe_ref_msg_id(msg: DBChatMessage) -> str:
        try:
            return msg.ext_data_obj.ref_msg_id or ""
        except (AttributeError, KeyError, ValueError) as e:
            logger.debug(f"Failed to parse ref_msg_id for msg {msg.id}: {e}")
            return ""

    items: List[ChatMessage] = []
    for msg in messages:
        try:
            items.append(
                ChatMessage(
                    id=msg.id,
                    sender_id=str(msg.sender_id),
                    sender_name=msg.sender_name,
                    sender_nickname=msg.sender_nickname or msg.sender_name,
                    platform_userid=msg.platform_userid or "",
                    content=msg.content_text,
                    content_data=_parse_content_data(msg.content_data),
                    chat_key=msg.chat_key,
                    create_time=msg.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    message_id=getattr(msg, "message_id", "") or "",
                    ref_msg_id=_safe_ref_msg_id(msg),
                )
            )
        except Exception:
            logger.warning(f"构建消息响应失败, msg_id={msg.id}, 跳过")

    return ChatMessageListResponse(total=total, items=items)


@router.post("/{chat_key}/preset", summary="设置聊天频道人设")
@require_role(Role.Admin)
async def set_chat_channel_preset(
    chat_key: str,
    preset_id: Optional[int] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """设置聊天频道人设，传入 preset_id=None 则使用默认人设"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        raise NotFoundError(resource="聊天频道")

    await channel.set_preset(preset_id)
    return ActionResponse(ok=True)


class ChatChannelUser(BaseModel):
    """聊天频道用户"""

    platform_userid: str
    nickname: str


class ChatChannelUsersResponse(BaseModel):
    """聊天频道用户列表"""

    total: int
    items: List[ChatChannelUser]


@router.get("/{chat_key}/users", summary="获取聊天频道用户列表")
async def get_chat_channel_users(
    chat_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ChatChannelUsersResponse:
    """获取聊天频道内的所有用户（按昵称）"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        raise NotFoundError(resource="聊天频道")

    # 从消息表查询该频道的所有独特用户
    messages = await DBChatMessage.filter(chat_key=chat_key).distinct().values_list('platform_userid', 'sender_nickname')

    # 去重并排序
    users_dict: Dict[str, str] = {}
    for userid, nickname in messages:
        if userid and userid != '-1' and nickname and nickname != 'SYSTEM':
            users_dict[userid] = nickname

    # 按昵称排序
    items = [
        ChatChannelUser(platform_userid=uid, nickname=nickname)
        for uid, nickname in sorted(users_dict.items(), key=lambda x: x[1])
    ]

    return ChatChannelUsersResponse(total=len(items), items=items)


class PokeRequest(BaseModel):
    target_user_id: str


@router.post("/{chat_key}/poke", summary="发送戳一戳")
@require_role(Role.Admin)
async def send_poke(
    chat_key: str,
    req: PokeRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """双击头像触发戳一戳"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        raise NotFoundError(resource="聊天频道")

    try:
        adapter = get_adapter(channel.adapter_key)
    except KeyError:
        return ActionResponse(ok=False)

    if not hasattr(adapter, "send_poke"):
        return ActionResponse(ok=False)

    ok = await adapter.send_poke(chat_key, req.target_user_id)
    return ActionResponse(ok=ok)


class SendMessageRequest(BaseModel):
    message: str


class SendMessageResponse(BaseModel):
    ok: bool = True
    error: str = ""


@router.post("/{chat_key}/send", summary="向聊天频道发送消息")
@require_role(Role.Admin)
async def send_message_to_channel(
    chat_key: str,
    message: str = Form(default=""),
    file: Optional[UploadFile] = File(default=None),
    sender_type: str = Form(default="bot"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> SendMessageResponse:
    """从 WebUI 向聊天频道发送消息（支持文本和/或文件）

    sender_type:
        - bot: 以机器人身份发送（默认）
        - system: 以 SYSTEM 身份发送，类似节日祝福触发
        - none: 消息带 ≡NA≡ 前缀，不进入上下文
    """
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        raise NotFoundError(resource="聊天频道")

    # system 类型不需要适配器转发，直接写入数据库
    if sender_type == "system":
        text = message.strip()
        if not text:
            return SendMessageResponse(ok=False, error="SYSTEM 消息内容不能为空")
        try:
            await message_service.push_system_message(
                chat_key=chat_key,
                agent_messages=text,
                trigger_agent=True,
                db_chat_channel=channel,
            )
            return SendMessageResponse(ok=True)
        except Exception as e:
            logger.error(f"WebUI 发送 SYSTEM 消息到 {chat_key} 失败: {e}")
            return SendMessageResponse(ok=False, error=str(e))

    # bot / none 类型需要适配器转发
    try:
        adapter = get_adapter(channel.adapter_key)
        if not adapter.supports_webui_send:
            return SendMessageResponse(ok=False, error="当前适配器不支持从 WebUI 发送消息")
    except KeyError:
        return SendMessageResponse(ok=False, error="适配器未加载")

    text = message.strip()

    # none 类型：添加命令输出前缀，确保不进入上下文
    if sender_type == "none" and text:
        effective_config = await config_resolver.get_effective_config(chat_key)
        text = f"{effective_config.AI_COMMAND_OUTPUT_PREFIX}{text}"

    if not text and not file:
        return SendMessageResponse(ok=False, error="消息内容不能为空")

    try:
        from nekro_agent.services.chat.universal_chat_service import universal_chat_service

        segments: list[AgentMessageSegment] = []

        # 文本段
        if text:
            segments.append(AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=text))

        # 文件段
        is_file_mode = False
        if file and file.filename:
            safe_chat_key = Path(chat_key).name
            safe_filename = Path(file.filename).name
            upload_dir = Path(USER_UPLOAD_DIR) / safe_chat_key
            upload_dir.mkdir(parents=True, exist_ok=True)
            save_path = upload_dir / safe_filename
            # 分块写入，避免大文件一次性占满内存；同时检查文件大小上限
            max_upload_size = 100 * 1024 * 1024  # 100 MB
            total_size = 0
            with save_path.open("wb") as f:
                while chunk := await file.read(1024 * 1024):
                    total_size += len(chunk)
                    if total_size > max_upload_size:
                        save_path.unlink(missing_ok=True)
                        return SendMessageResponse(ok=False, error="文件大小超过 100MB 限制")
                    f.write(chunk)
            # 使用沙盒风格路径（/app/uploads/filename），让 _preprocess_messages 的 convert_to_host_path 正确转换
            segments.append(AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=f"/app/uploads/{safe_filename}"))
            # 非图片文件使用 FILE 模式发送
            is_file_mode = not (file.content_type or "").startswith("image/")

        await universal_chat_service.send_agent_message(
            chat_key=chat_key,
            messages=segments,
            adapter=adapter,
            record=sender_type != "none",
            file_mode=is_file_mode,
        )
        return SendMessageResponse(ok=True)
    except Exception as e:
        logger.error(f"WebUI 发送消息到 {chat_key} 失败: {e}")
        return SendMessageResponse(ok=False, error=str(e))


@router.get("/{chat_key}/stream", summary="获取聊天频道消息实时流")
@require_role(Role.Admin)
async def stream_chat_channel_messages(
    chat_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
):
    """获取聊天频道消息的实时流，使用 Server-Sent Events (SSE)

    Args:
        chat_key: 聊天频道唯一标识

    Returns:
        StreamingResponse: SSE 流，每条新消息作为一个事件

    Raises:
        NotFoundError: 当频道不存在时
    """
    import json

    from fastapi.responses import StreamingResponse

    from nekro_agent.services.message_broadcaster import message_broadcaster

    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        raise NotFoundError(resource="聊天频道")

    async def event_generator():
        """生成 SSE 事件流"""
        async for message in message_broadcaster.subscribe(chat_key):
            # 直接使用广播的消息对象，转换为可序列化的字典格式
            try:
                # 将content_data转换为可序列化的格式
                content_data = []
                if message.content_data:
                    if isinstance(message.content_data, str):
                        try:
                            content_data = json5.loads(message.content_data)
                        except Exception:
                            content_data = []
                    elif isinstance(message.content_data, list):
                        # 将ChatMessageSegment对象转换为字典
                        for item in message.content_data:
                            if hasattr(item, 'model_dump'):
                                content_data.append(item.model_dump())
                            elif isinstance(item, dict):
                                content_data.append(item)
                            else:
                                content_data.append(str(item))

                # 构建消息字典格式，用于SSE发送
                message_dict = {
                    "id": 0,  # 实时消息没有数据库ID
                    "sender_id": str(message.sender_id),
                    "sender_name": message.sender_name,
                    "sender_nickname": message.sender_nickname or message.sender_name,
                    "platform_userid": message.platform_userid or "",
                    "content": message.content_text,
                    "content_data": content_data,
                    "chat_key": message.chat_key,
                    "create_time": "",  # 前端可使用当前时间
                    "message_id": message.message_id or "",
                    "ref_msg_id": getattr(message, "ref_msg_id", "") or "",
                }

                # 以 SSE 事件格式发送
                yield f"data: {json.dumps(message_dict, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"SSE消息序列化失败: {e}")
                continue

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
