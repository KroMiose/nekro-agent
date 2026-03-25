"""全局 MCP 路由 — 注册表等不依赖 workspace 的端点"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.core.auto_inject_mcp import get_auto_inject_mcp_servers, set_auto_inject_mcp_servers
from nekro_agent.models.db_user import DBUser
from nekro_agent.services.mcp.registry import get_registry
from nekro_agent.services.mcp.schemas import McpRegistryItem
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/mcp", tags=["MCP"])


class _ActionOk(BaseModel):
    ok: bool = True


class _AutoInjectMcpResponse(BaseModel):
    servers: List[Dict[str, Any]]


class _AutoInjectMcpUpdate(BaseModel):
    servers: List[Dict[str, Any]]


@router.get("/registry", summary="获取内置 MCP 服务注册表", response_model=List[McpRegistryItem])
@require_role(Role.Admin)
async def get_mcp_registry(
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[McpRegistryItem]:
    return get_registry()


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
    set_auto_inject_mcp_servers(body.servers)
    return _ActionOk()
