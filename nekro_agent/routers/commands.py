"""命令管理 API 路由"""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/commands", tags=["Commands"])


# region 响应模型


class CommandStateResponse(BaseModel):
    name: str
    namespace: str
    aliases: list[str]
    description: str
    usage: str
    permission: str
    category: str
    source: str  # "built_in" | 插件 key
    enabled: bool
    has_channel_override: bool
    params_schema: Optional[dict] = None


# endregion


# region 命令列表与状态管理


@router.get("/list", response_model=list[CommandStateResponse], summary="获取命令列表")
@require_role(Role.Admin)
async def list_commands(
    chat_key: Optional[str] = Query(None, description="频道标识，不传则返回系统级状态"),
):
    """获取所有命令列表及其启用状态"""
    from nekro_agent.services.command.manager import command_manager

    return await command_manager.get_all_command_states(chat_key)


class SetCommandStateRequest(BaseModel):
    command_name: str
    enabled: bool
    chat_key: Optional[str] = None


@router.post("/set-state", summary="设置命令状态")
@require_role(Role.Admin)
async def set_command_state(req: SetCommandStateRequest):
    """设置命令启用/禁用状态"""
    from nekro_agent.services.command.manager import command_manager

    await command_manager.set_command_enabled(req.command_name, req.enabled, req.chat_key)
    return {"ok": True}


class ResetCommandStateRequest(BaseModel):
    command_name: str
    chat_key: Optional[str] = None


@router.post("/reset-state", summary="重置命令状态")
@require_role(Role.Admin)
async def reset_command_state(req: ResetCommandStateRequest):
    """重置命令状态（回退到上级配置）"""
    from nekro_agent.services.command.manager import command_manager

    await command_manager.reset_command_state(req.command_name, req.chat_key)
    return {"ok": True}


class BatchSetCommandStateRequest(BaseModel):
    commands: list[SetCommandStateRequest]


@router.post("/batch-set-state", summary="批量设置命令状态")
@require_role(Role.Admin)
async def batch_set_command_state(req: BatchSetCommandStateRequest):
    """批量设置命令状态"""
    from nekro_agent.services.command.manager import command_manager

    for item in req.commands:
        await command_manager.set_command_enabled(item.command_name, item.enabled, item.chat_key)
    return {"ok": True}


# endregion


# region 命令补全


@router.get("/completions", summary="获取命令补全列表")
async def get_command_completions(
    chat_key: Optional[str] = Query(None),
    prefix: Optional[str] = Query(None, description="输入前缀过滤"),
):
    """获取命令补全列表（供前端输入框使用）"""
    from nekro_agent.services.command.completion import completion_provider

    entries = await completion_provider.get_completion_entries(chat_key)

    if prefix:
        entries = [e for e in entries if e.name.startswith(prefix)]

    return entries


# endregion


# region Agent Tool-Use


@router.get("/tools", summary="获取 Agent Tool 列表")
async def get_agent_tools(
    chat_key: Optional[str] = Query(None),
):
    """导出命令为 Agent Tool-Use 格式（OpenAI Function Calling）"""
    from nekro_agent.services.command.tool_export import agent_tool_exporter

    return agent_tool_exporter.export_tools(chat_key)


# endregion
