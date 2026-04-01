"""动态头像工具 - 供 Agent 调用"""

from typing import Optional

from nekro_agent.api.plugin import SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.avatar_manager import get_avatar_manager

from .plugin import config


@AgentCtx.register_tool(
    namespace="avatar",
    description="切换机器人在合并转发消息中显示的头像和名称",
)
async def switch_avatar(
    ctx: AgentCtx,
    profile_name: str,
    reason: str = "",
) -> str:
    """切换头像配置

    Args:
        profile_name: 头像配置名称（如 "NekroAgent 😊"）
        reason: 切换原因（可选，用于日志记录）

    Returns:
        操作结果描述

    Examples:
        switch_avatar("NekroAgent 😊", "用户很开心")
        switch_avatar("NekroAgent 🤔", "正在思考问题")
    """
    if not config.ENABLE_DYNAMIC_AVATAR:
        return "动态头像功能已禁用"

    manager = get_avatar_manager()
    profile = await manager.switch_avatar(profile_name, reason or "agent_request")

    if profile:
        return f"头像已切换为: {profile.name}"
    else:
        available = await manager.list_profiles()
        names = [p.name for p in available]
        return f"切换失败，未找到配置: {profile_name}。可用配置: {', '.join(names)}"


@AgentCtx.register_tool(
    namespace="avatar",
    description="根据情绪自动切换到匹配的头像",
)
async def set_avatar_emotion(
    ctx: AgentCtx,
    emotion: str,
) -> str:
    """根据情绪设置头像

    Args:
        emotion: 情绪类型 (happy, sad, thinking, sleeping, neutral 等)

    Returns:
        操作结果描述

    Examples:
        set_avatar_emotion("happy")
        set_avatar_emotion("thinking")
    """
    if not config.ENABLE_DYNAMIC_AVATAR:
        return "动态头像功能已禁用"

    manager = get_avatar_manager()
    profile = await manager.set_emotion(emotion)
    return f"情绪已设置为: {emotion}, 头像: {profile.name}"


@AgentCtx.register_tool(
    namespace="avatar",
    description="获取当前头像状态",
)
async def get_avatar_status(
    ctx: AgentCtx,
) -> str:
    """获取当前头像状态

    Returns:
        当前头像状态信息

    Examples:
        get_avatar_status()
    """
    if not config.ENABLE_DYNAMIC_AVATAR:
        return "动态头像功能已禁用"

    manager = get_avatar_manager()
    state = await manager.get_state_info()

    lines = [
        f"当前头像: {state['current_profile']['name']}",
        f"当前情绪: {state['emotion']}",
        f"上次切换: {state['last_changed']}",
        f"切换原因: {state['change_reason']}",
        f"可用配置: {', '.join(state['available_profiles'])}",
    ]
    return "\n".join(lines)


@AgentCtx.register_tool(
    namespace="avatar",
    description="获取所有可用的头像配置列表",
)
async def list_avatar_profiles(
    ctx: AgentCtx,
) -> str:
    """列出所有可用的头像配置

    Returns:
        头像配置列表

    Examples:
        list_avatar_profiles()
    """
    if not config.ENABLE_DYNAMIC_AVATAR:
        return "动态头像功能已禁用"

    manager = get_avatar_manager()
    profiles = await manager.list_profiles()

    if not profiles:
        return "暂无头像配置"

    lines = ["可用头像配置:"]
    for p in profiles:
        lines.append(f"  - {p.name} (情绪标签: {p.emotion_tag})")

    return "\n".join(lines)
