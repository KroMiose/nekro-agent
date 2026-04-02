"""动态头像工具 - 简化版"""

from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.avatar_manager import get_avatar_manager


@AgentCtx.register_tool(namespace="avatar", description="切换机器人头像名称")
async def switch_avatar(ctx: AgentCtx, name: str) -> str:
    """切换头像名称"""
    get_avatar_manager()._name = name
    return f"头像已切换为: {name}"


@AgentCtx.register_tool(namespace="avatar", description="根据情绪设置头像")
async def set_avatar_emotion(ctx: AgentCtx, emotion: str) -> str:
    """根据情绪设置头像"""
    name = get_avatar_manager().set_emotion(emotion)
    return f"情绪: {emotion}, 头像: {name}"
