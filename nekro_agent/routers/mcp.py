"""全局 MCP 路由 — 注册表、约束、自动注入"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.core.auto_inject_mcp import get_auto_inject_mcp_servers, set_auto_inject_mcp_servers
from nekro_agent.models.db_user import DBUser
from nekro_agent.services.mcp.registry import get_registry
from nekro_agent.services.mcp.schemas import (
    STDIO_COMMAND_ALLOWLIST,
    McpConstraints,
    McpRegistryItem,
    McpServerConfig,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/mcp", tags=["MCP"])


class _ActionOk(BaseModel):
    ok: bool = True


class _AutoInjectMcpResponse(BaseModel):
    servers: List[Dict[str, Any]]


class _AutoInjectMcpUpdate(BaseModel):
    servers: List[Dict[str, Any]]


class _McpValidationResponse(BaseModel):
    ok: bool
    server_info: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    latency_ms: float
    error: Optional[str] = None
    error_kind: Optional[str] = None


@router.get("/registry", summary="获取内置 MCP 服务注册表", response_model=List[McpRegistryItem])
@require_role(Role.Admin)
async def get_mcp_registry(
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[McpRegistryItem]:
    return get_registry()


@router.get("/constraints", summary="获取 MCP 配置约束（前端校验复用）", response_model=McpConstraints)
@require_role(Role.Admin)
async def get_mcp_constraints(
    _current_user: DBUser = Depends(get_current_active_user),
) -> McpConstraints:
    return McpConstraints(
        stdio_command_allowlist=sorted(STDIO_COMMAND_ALLOWLIST),
        name_pattern=r"^[A-Za-z0-9_-]{1,64}$",
    )


@router.get("/auto-inject", summary="获取自动注入 MCP 服务列表", response_model=_AutoInjectMcpResponse)
@require_role(Role.Admin)
async def get_auto_inject_mcp(
    _current_user: DBUser = Depends(get_current_active_user),
) -> _AutoInjectMcpResponse:
    return _AutoInjectMcpResponse(servers=get_auto_inject_mcp_servers())


@router.put("/auto-inject", summary="更新自动注入 MCP 服务列表", response_model=_ActionOk)
@require_role(Role.Admin)
async def update_auto_inject_mcp(
    body: _AutoInjectMcpUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> _ActionOk:
    from nekro_agent.schemas.errors import ValidationError

    # 逐项校验，避免任意 dict 直接落盘
    for raw in body.servers:
        if not isinstance(raw, dict):
            raise ValidationError(reason="servers 必须是对象数组")
        try:
            McpServerConfig.model_validate(raw)
        except Exception as e:  # noqa: BLE001
            raise ValidationError(reason=f"自动注入项 {raw.get('name', '?')} 配置无效: {e}") from e
    set_auto_inject_mcp_servers(body.servers)
    return _ActionOk()


@router.post(
    "/auto-inject/test",
    summary="临时验证一个自动注入 MCP 服务器（不保存）",
    response_model=_McpValidationResponse,
)
@require_role(Role.Admin)
async def test_auto_inject_server(
    server: McpServerConfig,
    _current_user: DBUser = Depends(get_current_active_user),
) -> _McpValidationResponse:
    """对未保存到自动注入列表的配置预先做一次握手验证。

    注意：stdio 类型会尝试在任意一个正在运行的工作区容器内 exec；都没在跑就返回
    container_not_running，提示用户启动一个工作区后再试。
    """
    from nekro_agent.services.mcp.validator import validate_server

    result = await validate_server(None, server)
    return _McpValidationResponse(**result.model_dump())


@router.post(
    "/auto-inject/servers/{server_name}/test",
    summary="验证自动注入清单中已存在的某个服务器，并持久化状态",
    response_model=_McpValidationResponse,
)
@require_role(Role.Admin)
async def test_saved_auto_inject_server(
    server_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> _McpValidationResponse:
    """从 auto-inject-mcp.json 读取指定服务器配置，跑握手并写回 validation 字段"""
    from datetime import datetime, timezone

    from nekro_agent.core.auto_inject_mcp import update_auto_inject_validation
    from nekro_agent.schemas.errors import NotFoundError
    from nekro_agent.services.mcp.validator import validate_server

    servers = get_auto_inject_mcp_servers()
    target_raw = next((s for s in servers if (s or {}).get("name") == server_name), None)
    if target_raw is None:
        raise NotFoundError(resource=f"自动注入 MCP 服务器 {server_name}")

    try:
        server_config = McpServerConfig.model_validate(target_raw)
    except Exception as e:  # noqa: BLE001
        from nekro_agent.schemas.errors import ValidationError

        raise ValidationError(reason=f"自动注入项配置无效: {e}") from e

    result = await validate_server(None, server_config)

    if result.ok:
        validation_state: Dict[str, Any] = {
            "status": "validated",
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "server_name": (result.server_info or {}).get("name") if result.server_info else None,
            "server_version": (result.server_info or {}).get("version") if result.server_info else None,
            "tools_count": len(result.tools or []),
            "latency_ms": result.latency_ms,
        }
    else:
        validation_state = {
            "status": "failed",
            "last_error": result.error,
            "last_error_kind": result.error_kind,
            "latency_ms": result.latency_ms,
        }
    update_auto_inject_validation(server_name, validation_state)
    return _McpValidationResponse(**result.model_dump())
