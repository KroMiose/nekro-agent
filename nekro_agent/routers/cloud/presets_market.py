from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from nekro_agent.models.db_preset import DBPreset
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import CloudServiceError, ConflictError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.systems.cloud.api.preset import get_preset, list_presets

router = APIRouter(prefix="/cloud/presets-market", tags=["Cloud Presets Market"])


class CloudPreset(BaseModel):
    remote_id: str
    is_local: bool
    name: str
    title: str
    avatar: str
    content: str
    description: str
    tags: str
    author: str
    create_time: str
    update_time: str


class CloudPresetListResponse(BaseModel):
    total: int
    items: List[CloudPreset]
    page: int
    page_size: int
    total_pages: int


class ActionResponse(BaseModel):
    ok: bool = True


@router.get("/list", summary="获取云端人设列表")
@require_role(Role.Admin)
async def get_cloud_presets_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    keyword: Optional[str] = None,
    tag: Optional[str] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> CloudPresetListResponse:
    """获取云端人设列表"""
    response = await list_presets(page=page, page_size=page_size, keyword=keyword, tag=tag)

    if not response.success:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    if not response.data or not response.data.items:
        return CloudPresetListResponse(
            total=0,
            items=[],
            page=page,
            page_size=page_size,
            total_pages=0,
        )

    remote_ids = [item.id for item in response.data.items]
    local_presets = await DBPreset.filter(remote_id__in=remote_ids).values("remote_id")
    local_preset_remote_ids = {preset["remote_id"] for preset in local_presets}

    result: List[CloudPreset] = []
    for item in response.data.items:
        result.append(
            CloudPreset(
                remote_id=item.id,
                is_local=item.id in local_preset_remote_ids,
                name=item.name,
                title=item.title,
                avatar=item.avatar,
                content=item.content,
                description=item.description,
                tags=item.tags,
                author=item.author,
                create_time=item.created_at or "",
                update_time=item.updated_at or "",
            ),
        )

    return CloudPresetListResponse(
        total=response.data.total,
        items=result,
        page=page,
        page_size=page_size,
        total_pages=(response.data.total + page_size - 1) // page_size,
    )


@router.post("/download/{remote_id}", summary="下载云端人设到本地")
@require_role(Role.Admin)
async def download_preset(
    remote_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """下载云端人设到本地"""
    exists = await DBPreset.exists(remote_id=remote_id)
    if exists:
        raise ConflictError(resource="人设")

    response = await get_preset(remote_id)
    if not response.success or not response.data:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    preset_data = response.data
    ext_data = preset_data.ext_data if preset_data.ext_data not in [None, "", "''", '""'] else {}
    await DBPreset.create(
        remote_id=preset_data.id,
        on_shared=preset_data.is_owner or False,
        name=preset_data.name,
        title=preset_data.title,
        avatar=preset_data.avatar,
        content=preset_data.content,
        description=preset_data.description,
        tags=preset_data.tags,
        author=preset_data.author,
        ext_data=ext_data,
    )

    return ActionResponse(ok=True)
