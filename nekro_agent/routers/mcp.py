"""全局 MCP 路由 — 注册表等不依赖 workspace 的端点"""

from typing import List

from fastapi import APIRouter, Depends

from nekro_agent.models.db_user import DBUser
from nekro_agent.services.mcp.registry import get_registry
from nekro_agent.services.mcp.schemas import McpRegistryItem
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.get("/registry", summary="获取内置 MCP 服务注册表", response_model=List[McpRegistryItem])
@require_role(Role.Admin)
async def get_mcp_registry(
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[McpRegistryItem]:
    return get_registry()
