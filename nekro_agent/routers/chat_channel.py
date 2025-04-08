from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from tortoise.expressions import Q

from nekro_agent.core.config import config
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/chat-channel", tags=["ChatChannel"])


@router.get("/list", summary="获取会话列表")
@require_role(Role.Admin)
async def get_chat_channel_list(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    chat_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取会话列表"""
    query = DBChatChannel.all()

    # 搜索条件
    if search:
        query = query.filter(
            Q(chat_key__contains=search) | Q(channel_name__contains=search),
        )
    if chat_type:
        query = query.filter(chat_key__startswith=f"{chat_type}_")
    if is_active is not None:
        query = query.filter(is_active=is_active)

    # 获取所有符合条件的频道
    channels = await query.all()

    # 获取每个频道的最后消息时间和其他信息
    channel_info_list = []
    for channel in channels:
        message_count = await DBChatMessage.filter(chat_key=channel.chat_key).count()
        last_message = await DBChatMessage.filter(chat_key=channel.chat_key).order_by("-create_time").first()
        # 确保时间是 naive 的
        last_message_time = last_message.create_time.replace(tzinfo=None) if last_message else datetime.min

        channel_info_list.append(
            {
                "channel": channel,
                "message_count": message_count,
                "last_message_time": last_message_time,
            },
        )

    # 按最后消息时间排序
    channel_info_list.sort(key=lambda x: x["last_message_time"], reverse=True)

    # 分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_channels = channel_info_list[start_idx:end_idx]

    # 构建返回结果
    result = []
    for info in paged_channels:
        channel = info["channel"]
        result.append(
            {
                "id": channel.id,
                "chat_key": channel.chat_key,
                "channel_name": channel.channel_name,
                "is_active": channel.is_active,
                "chat_type": channel.chat_type.value,
                "message_count": info["message_count"],
                "create_time": channel.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": channel.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_message_time": (
                    info["last_message_time"].strftime("%Y-%m-%d %H:%M:%S")
                    if info["last_message_time"] != datetime.min
                    else None
                ),
            },
        )

    return Ret.success(
        msg="获取成功",
        data={
            "total": len(result),
            "items": result,
        },
    )


@router.get("/detail/{chat_key}", summary="获取会话详情")
@require_role(Role.Admin)
async def get_chat_channel_detail(chat_key: str, _current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取会话详情"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        return Ret.fail(msg="会话不存在")

    # 获取会话数据
    message_count = await DBChatMessage.filter(chat_key=chat_key).count()

    # 获取最近一条消息的时间
    last_message = await DBChatMessage.filter(chat_key=chat_key).order_by("-create_time").first()
    last_message_time = last_message.create_time if last_message else None

    # 获取参与用户数
    unique_users = await DBChatMessage.filter(chat_key=chat_key).distinct().values_list("sender_id", flat=True)

    return Ret.success(
        msg="获取成功",
        data={
            "id": channel.id,
            "chat_key": channel.chat_key,
            "channel_name": channel.channel_name,
            "is_active": channel.is_active,
            "chat_type": channel.chat_type.value,
            "message_count": message_count,
            "unique_users": len(unique_users),
            "create_time": channel.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": channel.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_message_time": last_message_time.strftime("%Y-%m-%d %H:%M:%S") if last_message_time else None,
            "conversation_start_time": channel.conversation_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "preset_id": channel.preset_id,
        },
    )


@router.post("/{chat_key}/active", summary="设置会话激活状态")
@require_role(Role.Admin)
async def set_chat_channel_active(
    chat_key: str,
    is_active: bool,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """设置会话激活状态"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        return Ret.fail(msg="会话不存在")

    await channel.set_active(is_active)
    return Ret.success(msg="设置成功")


@router.post("/{chat_key}/reset", summary="重置会话状态")
@require_role(Role.Admin)
async def reset_chat_channel(
    chat_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """重置会话状态"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        return Ret.fail(msg="会话不存在")

    await channel.reset_channel()
    return Ret.success(msg="重置成功")


@router.get("/{chat_key}/messages", summary="获取会话消息列表")
@require_role(Role.Admin)
async def get_chat_channel_messages(
    chat_key: str,
    before_id: Optional[int] = None,
    page_size: int = 32,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取会话消息列表"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        return Ret.fail(msg="会话不存在")

    # 查询消息
    query = DBChatMessage.filter(chat_key=chat_key)
    if before_id:
        query = query.filter(id__lt=before_id)

    # 统计总数
    total = await query.count()

    # 查询消息
    messages = await query.order_by("-id").limit(page_size)

    return Ret.success(
        msg="获取成功",
        data={
            "total": total,
            "items": [
                {
                    "id": msg.id,
                    "sender_id": msg.sender_id,
                    "sender_name": msg.sender_real_nickname,
                    "content": msg.content_text,
                    "create_time": msg.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for msg in messages
            ],
        },
    )


@router.post("/{chat_key}/preset", summary="设置会话人设")
@require_role(Role.Admin)
async def set_chat_channel_preset(
    chat_key: str,
    preset_id: Optional[int] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """设置会话人设，传入 preset_id=None 则使用默认人设"""
    channel = await DBChatChannel.get_or_none(chat_key=chat_key)
    if not channel:
        return Ret.fail(msg="会话不存在")

    # 设置人设ID，None需要作为null处理
    if preset_id is None:
        channel.preset_id = None  # type: ignore  # 在数据库模型中允许为null
    else:
        channel.preset_id = preset_id
    await channel.save()

    # 获取人设信息
    preset = await channel.get_preset()
    preset_name = preset.name if hasattr(preset, "name") else "默认人设"

    return Ret.success(msg=f"设置成功，当前人设: {preset_name}")
