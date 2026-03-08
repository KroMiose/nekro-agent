"""命令管理 API 路由"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from nekro_agent.models.db_user import DBUser
from nekro_agent.services.user.deps import get_current_active_user
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
    _current_user: DBUser = Depends(get_current_active_user),
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
async def set_command_state(
    req: SetCommandStateRequest,
    _current_user: DBUser = Depends(get_current_active_user),
):
    """设置命令启用/禁用状态"""
    from nekro_agent.services.command.manager import command_manager

    await command_manager.set_command_enabled(req.command_name, req.enabled, req.chat_key)
    return {"ok": True}


class ResetCommandStateRequest(BaseModel):
    command_name: str
    chat_key: Optional[str] = None


@router.post("/reset-state", summary="重置命令状态")
@require_role(Role.Admin)
async def reset_command_state(
    req: ResetCommandStateRequest,
    _current_user: DBUser = Depends(get_current_active_user),
):
    """重置命令状态（回退到上级配置）"""
    from nekro_agent.services.command.manager import command_manager

    await command_manager.reset_command_state(req.command_name, req.chat_key)
    return {"ok": True}


class BatchSetCommandStateRequest(BaseModel):
    commands: list[SetCommandStateRequest]


@router.post("/batch-set-state", summary="批量设置命令状态")
@require_role(Role.Admin)
async def batch_set_command_state(
    req: BatchSetCommandStateRequest,
    _current_user: DBUser = Depends(get_current_active_user),
):
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


# region 命令输出流


@router.get("/{chat_key}/output/stream", summary="获取命令输出实时流")
@require_role(Role.Admin)
async def stream_command_output(
    chat_key: str,
    request: Request,
    _current_user: DBUser = Depends(get_current_active_user),
):
    """获取指定频道命令输出的实时流，使用 Server-Sent Events (SSE)

    Args:
        chat_key: 聊天频道唯一标识

    Returns:
        StreamingResponse: SSE 流，每条命令输出作为一个事件
    """
    import json

    from fastapi.responses import StreamingResponse

    from nekro_agent.services.command_output_broadcaster import command_output_broadcaster
    from nekro_agent.services.runtime_state import is_shutting_down

    async def event_generator():
        """生成 SSE 事件流"""
        subscription = command_output_broadcaster.subscribe(chat_key)
        try:
            while not is_shutting_down():
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(anext(subscription), timeout=1.0)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue

                yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
        finally:
            await subscription.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# endregion


# region WebUI 命令执行


class WebUIExecuteRequest(BaseModel):
    command_name: str
    chat_key: str
    raw_args: str = ""


class WebUIExecuteResponse(BaseModel):
    ok: bool = True
    responses: list[dict] = []


@router.post("/webui-execute", summary="WebUI 执行命令（不转发到平台）")
@require_role(Role.Admin)
async def webui_execute_command(
    req: WebUIExecuteRequest,
    _current_user: DBUser = Depends(get_current_active_user),
):
    """从 WebUI 直接执行命令，结果仅通过 SSE 广播到 WebUI，不发送到聊天平台"""
    from nekro_agent.services.command.registry import command_registry
    from nekro_agent.services.command.schemas import CommandExecutionContext, CommandRequest
    from nekro_agent.services.command_output_broadcaster import command_output_broadcaster

    context = CommandExecutionContext(
        user_id=str(_current_user.id),
        chat_key=req.chat_key,
        username=_current_user.username,
        adapter_key="webui",
        is_super_user=True,
        is_advanced_user=True,
    )
    request = CommandRequest(context=context, command_name=req.command_name, raw_args=req.raw_args)

    results: list[dict] = []
    async for response in command_registry.execute(request):
        await command_output_broadcaster.publish(
            chat_key=req.chat_key,
            command_name=req.command_name,
            status=response.status.value,
            message=response.message,
        )
        results.append({"status": response.status.value, "message": response.message})

    return WebUIExecuteResponse(ok=True, responses=results)


# endregion


# region Agent Tool-Use


@router.get("/tools", summary="获取 Agent Tool 列表")
async def get_agent_tools(
    chat_key: Optional[str] = Query(None),
):
    """导出命令为 Agent Tool-Use 格式（OpenAI Function Calling）"""
    from nekro_agent.services.command.tool_export import agent_tool_exporter

    return agent_tool_exporter.export_tools(chat_key)


class ExecuteToolRequest(BaseModel):
    command_name: str
    chat_key: str
    raw_args: str = ""
    user_id: str = "agent"
    username: str = "AI Agent"


@router.post("/execute", summary="AI 调用命令")
@require_role(Role.Admin)
async def execute_command_tool(
    req: ExecuteToolRequest,
    _current_user: DBUser = Depends(get_current_active_user),
):
    """AI Agent 调用命令并获取合并响应

    将命令流式输出合并为单一响应:
    - process_log: 所有中间消息拼接
    - message: 最终状态消息
    - data: 结构化数据
    """
    from nekro_agent.services.command.tool_export import agent_tool_exporter

    return await agent_tool_exporter.execute_tool(
        command_name=req.command_name,
        chat_key=req.chat_key,
        raw_args=req.raw_args,
        user_id=req.user_id,
        username=req.username,
    )


# endregion
