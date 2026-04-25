from __future__ import annotations

from typing import List

from nekro_agent.api.plugin import SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.services.memory.feature_flags import is_memory_system_enabled
from nekro_agent.services.memory.query_service import (
    MemoryObjectType,
    get_workspace_memory_detail,
    search_workspace_memories,
    trace_workspace_memory_origin,
)

from .plugin import memory_tools_config, plugin

logger = get_sub_logger("memory_tools")


async def _require_bound_workspace(_ctx: AgentCtx) -> DBWorkspace:
    """获取当前频道绑定的工作区。"""
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定工作区，无法主动检索工作区记忆。")
    return workspace


@plugin.mount_prompt_inject_method("memory_tools_prompt")
async def memory_tools_prompt(_ctx: AgentCtx) -> str:
    try:
        if not is_memory_system_enabled():
            return ""

        workspace = await _ctx.get_bound_workspace()
        if workspace is None:
            return ""

        return (
            "[Memory Tools]\n"
            "Use workspace memory tools when you need prior decisions, earlier solutions, historical preferences, or earlier task context."
        )
    except Exception:
        logger.exception("构建主动记忆工具提示词失败")
        return ""


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "搜索工作区记忆",
    description="在当前绑定工作区中主动检索结构化记忆，适合处理“之前说过什么”“以前怎么解决”“历史偏好/决策/经验”等问题。",
)
async def search_workspace_memories_tool(
    _ctx: AgentCtx,
    query: str,
    limit: int = 0,
    cognitive_type: str = "",
    knowledge_type: str = "",
) -> str:
    """Search structured memories in the current bound workspace.

    Use this when the user asks about earlier discussions, previous solutions,
    historical preferences, recurring issues, or prior decisions in the same workspace.

    Args:
        query (str): Retrieval query describing the memory topic to search for.
        limit (int): Maximum number of results to return. Use `0` to apply the plugin default.
        cognitive_type (str): Optional memory cognitive type filter, such as `semantic` or `episodic`.
        knowledge_type (str): Optional knowledge type filter, such as `fact`, `preference`, or `experience`.

    Returns:
        str: JSON string containing the search query, total hit count, and result items.

    Example:
        ```python
        search_workspace_memories_tool(
            query="之前关于记忆重建卡死和恢复机制的讨论",
            limit=5,
            cognitive_type="semantic",
        )
        ```
    """
    workspace = await _require_bound_workspace(_ctx)
    if not is_memory_system_enabled():
        raise ValueError("记忆系统当前已关闭，无法主动检索记忆。")

    resolved_limit = limit if limit > 0 else int(memory_tools_config.DEFAULT_SEARCH_LIMIT)
    result = await search_workspace_memories(
        workspace_id=workspace.id,
        query=query,
        limit=resolved_limit,
        cognitive_type=cognitive_type,
        knowledge_type=knowledge_type,
    )
    return result.model_dump_json(indent=2)


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "查看记忆详情",
    description="查看某条记忆对象的完整详情。先通过搜索工作区记忆获得 target_id 和 source_type，再调用本工具展开。",
)
async def get_memory_detail_tool(
    _ctx: AgentCtx,
    memory_type: str,
    memory_id: int,
) -> str:
    """Get the full detail of a memory object by type and ID.

    Call this after search when you need the complete content, metadata, and related objects
    of a memory item.

    Args:
        memory_type (str): Memory object type. Supported values: `paragraph`, `relation`, `entity`, `episode`.
        memory_id (int): Target memory object ID.

    Returns:
        str: JSON string containing the detailed memory payload.

    Example:
        ```python
        get_memory_detail_tool(memory_type="paragraph", memory_id=128)
        ```
    """
    workspace = await _require_bound_workspace(_ctx)
    if not is_memory_system_enabled():
        raise ValueError("记忆系统当前已关闭，无法查看记忆详情。")

    result = await get_workspace_memory_detail(
        workspace_id=workspace.id,
        memory_type=MemoryObjectType(memory_type.strip().lower()),
        memory_id=memory_id,
    )
    return result.model_dump_json(indent=2)


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "追溯记忆来源",
    description="追溯某条记忆对象的来源锚点、原始消息范围和来源类型，适合回答“你为什么这么记得”。",
)
async def trace_memory_origin_tool(
    _ctx: AgentCtx,
    memory_type: str,
    memory_id: int,
) -> str:
    """Trace the origin of a memory object.

    Use this when you need to explain why a memory exists, where it came from,
    or which original messages anchor it.

    Args:
        memory_type (str): Memory object type. Supported values: `paragraph`, `relation`, `entity`, `episode`.
        memory_id (int): Target memory object ID.

    Returns:
        str: JSON string containing origin metadata and anchor message previews when available.

    Example:
        ```python
        trace_memory_origin_tool(memory_type="paragraph", memory_id=128)
        ```
    """
    workspace = await _require_bound_workspace(_ctx)
    if not is_memory_system_enabled():
        raise ValueError("记忆系统当前已关闭，无法追溯记忆来源。")

    result = await trace_workspace_memory_origin(
        workspace_id=workspace.id,
        memory_type=MemoryObjectType(memory_type.strip().lower()),
        memory_id=memory_id,
    )
    return result.model_dump_json(indent=2)


@plugin.mount_collect_methods()
async def collect_memory_methods(ctx: AgentCtx) -> List:
    if not is_memory_system_enabled():
        return []
    workspace = await ctx.get_bound_workspace()
    if workspace is None:
        return []
    return [
        search_workspace_memories_tool,
        get_memory_detail_tool,
        trace_memory_origin_tool,
    ]
