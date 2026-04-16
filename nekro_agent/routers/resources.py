from fastapi import APIRouter, Depends

from nekro_agent.models.db_user import DBUser
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.errors import NotFoundError
from nekro_agent.schemas.workspace_resource import (
    ActionOkResponse,
    WorkspaceResourceBindBody,
    WorkspaceResourceBindingsResponse,
    WorkspaceResourceCheckBindBody,
    WorkspaceResourceCheckBindResponse,
    WorkspaceResourceCreate,
    WorkspaceResourceDetailResponse,
    WorkspaceResourceListResponse,
    WorkspaceResourceReorderBody,
    WorkspaceResourceTemplatesResponse,
    WorkspaceResourceUpdate,
)
from nekro_agent.services.resources import get_resource_templates, workspace_resource_service
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.services.workspace.manager import WorkspaceService

router = APIRouter(tags=["Workspace Resources"])


async def _refresh_workspace_claude_md(workspace_id: int) -> None:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    WorkspaceService.update_claude_md(workspace)


@router.get("/resources/templates", summary="获取工作区资源预置模板", response_model=WorkspaceResourceTemplatesResponse)
@require_role(Role.Admin)
async def list_resource_templates(
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceResourceTemplatesResponse:
    return WorkspaceResourceTemplatesResponse(items=get_resource_templates())


@router.get("/resources", summary="获取全局工作区资源列表", response_model=WorkspaceResourceListResponse)
@require_role(Role.Admin)
async def list_resources(
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceResourceListResponse:
    return WorkspaceResourceListResponse(items=await workspace_resource_service.list_resources())


@router.post("/resources", summary="创建工作区资源", response_model=WorkspaceResourceDetailResponse)
@require_role(Role.Admin)
async def create_resource(
    body: WorkspaceResourceCreate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceResourceDetailResponse:
    return WorkspaceResourceDetailResponse(item=await workspace_resource_service.create_resource(body))


@router.get("/resources/{resource_id}", summary="获取工作区资源详情", response_model=WorkspaceResourceDetailResponse)
@require_role(Role.Admin)
async def get_resource(
    resource_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceResourceDetailResponse:
    return WorkspaceResourceDetailResponse(item=await workspace_resource_service.get_resource_detail(resource_id))


@router.patch("/resources/{resource_id}", summary="更新工作区资源", response_model=WorkspaceResourceDetailResponse)
@require_role(Role.Admin)
async def update_resource(
    resource_id: int,
    body: WorkspaceResourceUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceResourceDetailResponse:
    detail = await workspace_resource_service.update_resource(resource_id, body)
    return WorkspaceResourceDetailResponse(item=detail)


@router.delete("/resources/{resource_id}", summary="删除工作区资源", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def delete_resource(
    resource_id: int,
    remove_bindings: bool = False,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    await workspace_resource_service.delete_resource(resource_id, remove_bindings=remove_bindings)
    return ActionOkResponse()


@router.get("/workspaces/{workspace_id}/resources", summary="获取工作区已绑定资源", response_model=WorkspaceResourceBindingsResponse)
@require_role(Role.Admin)
async def list_workspace_resources(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceResourceBindingsResponse:
    return WorkspaceResourceBindingsResponse(items=await workspace_resource_service.list_workspace_bindings(workspace_id))


@router.post("/workspaces/{workspace_id}/resources/check-bind", summary="检查资源绑定冲突", response_model=WorkspaceResourceCheckBindResponse)
@require_role(Role.Admin)
async def check_workspace_resource_bind(
    workspace_id: int,
    body: WorkspaceResourceCheckBindBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceResourceCheckBindResponse:
    conflicts = await workspace_resource_service.check_bind_conflicts(workspace_id, body.resource_id)
    return WorkspaceResourceCheckBindResponse(ok=not conflicts, conflicts=conflicts)


@router.post("/workspaces/{workspace_id}/resources/{resource_id}", summary="绑定资源到工作区", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def bind_workspace_resource(
    workspace_id: int,
    resource_id: int,
    body: WorkspaceResourceBindBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    await workspace_resource_service.bind_resource(workspace_id, resource_id, note=body.note)
    await _refresh_workspace_claude_md(workspace_id)
    return ActionOkResponse()


@router.delete("/workspaces/{workspace_id}/resources/{resource_id}", summary="解绑工作区资源", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def unbind_workspace_resource(
    workspace_id: int,
    resource_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    await workspace_resource_service.unbind_resource(workspace_id, resource_id)
    await _refresh_workspace_claude_md(workspace_id)
    return ActionOkResponse()


@router.put("/workspaces/{workspace_id}/resources/reorder", summary="重排工作区资源", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def reorder_workspace_resources(
    workspace_id: int,
    body: WorkspaceResourceReorderBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ordered_binding_ids = [item.binding_id for item in sorted(body.items, key=lambda item: item.sort_order)]
    await workspace_resource_service.reorder_bindings(workspace_id, ordered_binding_ids)
    await _refresh_workspace_claude_md(workspace_id)
    return ActionOkResponse()
