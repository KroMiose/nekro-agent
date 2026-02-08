import base64
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, UploadFile
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from tortoise.expressions import Q

from nekro_agent.models.db_preset import DBPreset
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import (
    CloudServiceError,
    NotFoundError,
    ValidationError,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.systems.cloud.api.preset import (
    create_preset as cloud_create_preset,
)
from nekro_agent.systems.cloud.api.preset import (
    delete_preset as cloud_delete_preset,
)
from nekro_agent.systems.cloud.api.preset import (
    get_preset,
    list_user_presets,
)
from nekro_agent.systems.cloud.api.preset import (
    update_preset as cloud_update_preset,
)
from nekro_agent.systems.cloud.exceptions import NekroCloudDisabled
from nekro_agent.systems.cloud.schemas.preset import PresetCreate, PresetUpdate
from nekro_agent.tools.image_utils import process_image_data_url
from nekro_agent.tools.telemetry_util import generate_instance_id

router = APIRouter(prefix="/presets", tags=["Presets"])


class TagInfo(BaseModel):
    tag: str
    count: int


class PresetSummary(BaseModel):
    id: int
    remote_id: str | None
    on_shared: bool
    name: str
    title: str
    avatar: str
    description: str
    tags: str
    author: str
    is_remote: bool
    create_time: str
    update_time: str


class PresetDetail(PresetSummary):
    content: str


class PresetListResponse(BaseModel):
    total: int
    items: List[PresetSummary]


class ActionResponse(BaseModel):
    ok: bool = True


class ShareResponse(BaseModel):
    remote_id: str


class RefreshStatusResponse(BaseModel):
    updated_count: int
    total_cloud_presets: int


class AvatarUploadResponse(BaseModel):
    avatar: str


def _preset_summary(preset: DBPreset) -> PresetSummary:
    return PresetSummary(
        id=preset.id,
        remote_id=preset.remote_id,
        on_shared=preset.on_shared,
        name=preset.name,
        title=preset.title or preset.name,
        avatar=preset.avatar,
        description=preset.description,
        tags=preset.tags,
        author=preset.author,
        is_remote=preset.remote_id is not None,
        create_time=preset.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        update_time=preset.update_time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def _preset_detail(preset: DBPreset) -> PresetDetail:
    base = _preset_summary(preset)
    return PresetDetail(**base.model_dump(), content=preset.content)


@router.get("/tags", summary="获取所有可用的人设标签", response_model=List[TagInfo])
@require_role(Role.Admin)
async def get_all_preset_tags(
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[TagInfo]:
    all_presets = await DBPreset.all().values("tags")

    tag_counts = Counter()
    for preset in all_presets:
        tags_str = preset.get("tags")
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            tag_counts.update(tags)

    sorted_tags = sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))

    return [TagInfo(tag=tag, count=count) for tag, count in sorted_tags]


@router.get("/list", summary="获取人设列表", response_model=PresetListResponse)
@require_role(Role.Admin)
async def get_preset_list(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    tags: Optional[str] = None,
    remote_only: Optional[bool] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> PresetListResponse:
    query = DBPreset.all()

    if search:
        query = query.filter(Q(name__contains=search) | Q(title__contains=search) | Q(description__contains=search))

    selected_tags: List[str] = []
    if tags:
        selected_tags.extend([t.strip() for t in tags.split(",") if t.strip()])
    if tag:
        selected_tags.append(tag.strip())

    if selected_tags:
        for t in selected_tags:
            query = query.filter(tags__contains=t)
    if remote_only is not None:
        query = query.filter(remote_id__not_isnull=True) if remote_only else query.filter(remote_id__isnull=True)

    total = await query.count()

    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by("-remote_id", "-update_time")

    presets = await query

    return PresetListResponse(total=total, items=[_preset_summary(p) for p in presets])


@router.get("/{preset_id}", summary="获取人设详情", response_model=PresetDetail)
@require_role(Role.Admin)
async def get_preset_detail(
    preset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> PresetDetail:
    preset = await DBPreset.get_or_none(id=preset_id)
    if not preset:
        raise NotFoundError(resource="人设")

    return _preset_detail(preset)


@router.post("", summary="创建人设", response_model=ActionResponse)
@require_role(Role.Admin)
async def create_preset(
    name: str = Body(...),
    title: str = Body(None),
    avatar: str = Body(...),
    content: str = Body(...),
    description: str = Body(""),
    tags: str = Body(""),
    author: str = Body(""),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    await DBPreset.create(
        name=name,
        title=title or name,
        avatar=avatar,
        content=content,
        description=description,
        tags=tags,
        author=author or _current_user.username,
        on_shared=False,
    )

    return ActionResponse(ok=True)


@router.put("/{preset_id}", summary="更新人设", response_model=ActionResponse)
@require_role(Role.Admin)
async def update_preset(
    preset_id: int,
    name: str = Body(...),
    title: str = Body(None),
    avatar: str = Body(...),
    content: str = Body(...),
    description: str = Body(""),
    tags: str = Body(""),
    author: str = Body(""),
    remove_remote: bool = Body(False),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    preset = await DBPreset.get_or_none(id=preset_id)
    if not preset:
        raise NotFoundError(resource="人设")

    preset.name = name
    preset.title = title or name
    preset.avatar = avatar
    preset.content = content
    preset.description = description
    preset.tags = tags
    preset.author = author or _current_user.username

    if remove_remote and preset.remote_id and not preset.on_shared:
        preset.remote_id = ""
        preset.on_shared = False

    await preset.save()

    return ActionResponse(ok=True)


@router.delete("/{preset_id}", summary="删除人设", response_model=ActionResponse)
@require_role(Role.Admin)
async def delete_preset(
    preset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    preset = await DBPreset.get_or_none(id=preset_id)
    if not preset:
        raise NotFoundError(resource="人设")

    await preset.delete()
    return ActionResponse(ok=True)


@router.post("/{preset_id}/sync", summary="同步云端人设", response_model=ActionResponse)
@require_role(Role.Admin)
async def sync_preset(
    preset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    preset = await DBPreset.get_or_none(id=preset_id)
    if not preset:
        raise NotFoundError(resource="人设")

    if not preset.remote_id:
        raise ValidationError(reason="此人设不是云端人设")

    response = await get_preset(preset.remote_id)
    if not response.success or not response.data:
        raise CloudServiceError(reason=str(response.message))

    preset.name = response.data.name
    preset.title = response.data.title
    preset.avatar = response.data.avatar
    preset.content = response.data.content
    preset.description = response.data.description
    preset.tags = response.data.tags
    preset.author = response.data.author
    await preset.save()

    return ActionResponse(ok=True)


@router.post("/upload-avatar", summary="上传头像", response_model=AvatarUploadResponse)
@require_role(Role.Admin)
async def upload_avatar(
    file: UploadFile = File(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> AvatarUploadResponse:
    contents = await file.read()

    base64_encoded = base64.b64encode(contents).decode("utf-8")

    mime_type = file.content_type or "image/jpeg"

    data_url = f"data:{mime_type};base64,{base64_encoded}"

    processed_data_url = await process_image_data_url(data_url)

    return AvatarUploadResponse(avatar=processed_data_url)


@router.post("/{preset_id}/share", summary="共享人设到云端", response_model=ShareResponse)
@require_role(Role.Admin)
async def share_preset(
    preset_id: int,
    is_sfw: bool = True,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ShareResponse:
    preset = await DBPreset.get_or_none(id=preset_id)
    if not preset:
        raise NotFoundError(resource="人设")

    if preset.on_shared and preset.remote_id:
        raise ValidationError(reason="此人设已经共享到云端")

    if not preset.name:
        raise ValidationError(reason="人设名称不能为空")
    if not preset.content:
        raise ValidationError(reason="人设内容不能为空")
    if not preset.avatar:
        raise ValidationError(reason="人设头像不能为空")
    if not preset.description:
        raise ValidationError(reason="人设描述不能为空，请先编辑人设添加描述")

    instance_id = generate_instance_id()

    try:
        preset_data = PresetCreate(
            name=preset.name,
            title=preset.title or preset.name,
            avatar=preset.avatar,
            content=preset.content,
            description=preset.description,
            tags=preset.tags,
            author=preset.author,
            ext_data=preset.ext_data or "",
            is_sfw=is_sfw,
            instance_id=instance_id,
        )
    except PydanticValidationError as e:
        raise ValidationError(reason=str(e)) from e

    response = await cloud_create_preset(preset_data)

    if not response.success or not response.data:
        raise CloudServiceError(reason=str(response.message))

    preset.remote_id = response.data.id
    preset.on_shared = True
    await preset.save()

    return ShareResponse(remote_id=response.data.id)


@router.post("/{preset_id}/unshare", summary="撤回共享人设", response_model=ActionResponse)
@require_role(Role.Admin)
async def unshare_preset(
    preset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    preset = await DBPreset.get_or_none(id=preset_id)
    if not preset:
        raise NotFoundError(resource="人设")

    if not preset.on_shared or not preset.remote_id:
        raise ValidationError(reason="此人设未共享到云端")

    instance_id = generate_instance_id()
    remote_id = str(preset.remote_id) if preset.remote_id else ""
    response = await cloud_delete_preset(remote_id, instance_id)

    preset.on_shared = False

    if response.success:
        preset.remote_id = ""

    await preset.save()

    if not response.success:
        raise CloudServiceError(reason=str(response.message))

    return ActionResponse(ok=True)


@router.post("/{preset_id}/sync-to-cloud", summary="同步人设到云端", response_model=ActionResponse)
@require_role(Role.Admin)
async def sync_to_cloud(
    preset_id: int,
    is_sfw: bool = True,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    preset = await DBPreset.get_or_none(id=preset_id)
    if not preset:
        raise NotFoundError(resource="人设")

    if not preset.on_shared or not preset.remote_id:
        raise ValidationError(reason="此人设未共享到云端")

    if not preset.name:
        raise ValidationError(reason="人设名称不能为空")
    if not preset.content:
        raise ValidationError(reason="人设内容不能为空")
    if not preset.avatar:
        raise ValidationError(reason="人设头像不能为空")
    if not preset.description:
        raise ValidationError(reason="人设描述不能为空，请先编辑人设添加描述")

    instance_id = generate_instance_id()
    try:
        preset_data = PresetUpdate(
            name=preset.name,
            title=preset.title or preset.name,
            avatar=preset.avatar,
            content=preset.content,
            description=preset.description,
            tags=preset.tags,
            author=preset.author,
            ext_data=preset.ext_data or "",
            is_sfw=is_sfw,
            instance_id=instance_id,
        )
    except PydanticValidationError as e:
        raise ValidationError(reason=str(e)) from e

    remote_id = str(preset.remote_id) if preset.remote_id else ""

    response = await cloud_update_preset(remote_id, preset_data)

    if not response.success:
        raise CloudServiceError(reason=str(response.message))

    return ActionResponse(ok=True)


@router.post("/refresh-shared-status", summary="刷新人设共享状态", response_model=RefreshStatusResponse)
@require_role(Role.Admin)
async def refresh_shared_status(
    _current_user: DBUser = Depends(get_current_active_user),
) -> RefreshStatusResponse:
    """刷新人设共享状态"""
    try:
        response = await list_user_presets()

        if not response.success:
            raise CloudServiceError(reason=f"获取云端人设列表失败: {response.error}")

        if not response.data or not response.data.items:
            await DBPreset.filter(on_shared=True).update(on_shared=False)
            return RefreshStatusResponse(updated_count=0, total_cloud_presets=0)

        cloud_preset_ids = [item.id for item in response.data.items]
        local_presets = await DBPreset.filter(remote_id__not_isnull=True).all()

        updated_count = 0
        for preset in local_presets:
            if not preset.remote_id:
                continue

            is_in_cloud = preset.remote_id in cloud_preset_ids

            if preset.on_shared != is_in_cloud:
                preset.on_shared = is_in_cloud
                await preset.save()
                updated_count += 1

        return RefreshStatusResponse(
            updated_count=updated_count,
            total_cloud_presets=len(cloud_preset_ids),
        )
    except NekroCloudDisabled:
        raise CloudServiceError(reason="Nekro Cloud 未启用") from None
