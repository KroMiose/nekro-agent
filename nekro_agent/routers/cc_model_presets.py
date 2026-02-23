from fastapi import APIRouter, Depends

from nekro_agent.core.cc_model_presets import cc_presets_store
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.cc_model_preset import (
    CCModelPresetCreate,
    CCModelPresetInfo,
    CCModelPresetListResponse,
    CCModelPresetUpdate,
)
from nekro_agent.schemas.errors import ConflictError, NotFoundError, OperationFailedError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/cc-model-presets", tags=["CC Model Presets"])


def _to_info(item) -> CCModelPresetInfo:
    return CCModelPresetInfo(
        id=item.id,
        name=item.name,
        description=item.description,
        base_url=item.base_url,
        auth_token=item.auth_token,
        api_timeout_ms=item.api_timeout_ms,
        model_type=item.model_type,
        preset_model=item.preset_model,
        anthropic_model=item.anthropic_model,
        small_fast_model=item.small_fast_model,
        default_sonnet=item.default_sonnet,
        default_opus=item.default_opus,
        default_haiku=item.default_haiku,
        extra_env=item.extra_env,
        is_default=item.is_default,
        create_time=item.create_time,
        update_time=item.update_time,
        config_json=item.to_config_json(),
    )


@router.get("/list", response_model=CCModelPresetListResponse)
async def list_presets(_current_user: DBUser = Depends(get_current_active_user)):
    items = cc_presets_store.list_all()
    return CCModelPresetListResponse(total=len(items), items=[_to_info(p) for p in items])


@router.post("", response_model=CCModelPresetInfo)
@require_role(Role.Admin)
async def create_preset(body: CCModelPresetCreate, _current_user: DBUser = Depends(get_current_active_user)):
    if cc_presets_store.name_exists(body.name):
        raise ConflictError(resource=f"CC 模型预设 '{body.name}'")
    item = cc_presets_store.create(**body.model_dump())
    return _to_info(item)


@router.get("/{preset_id}", response_model=CCModelPresetInfo)
async def get_preset(preset_id: int, _current_user: DBUser = Depends(get_current_active_user)):
    item = cc_presets_store.get_by_id(preset_id)
    if not item:
        raise NotFoundError(resource=f"CC 模型预设 {preset_id}")
    return _to_info(item)


@router.patch("/{preset_id}", response_model=CCModelPresetInfo)
@require_role(Role.Admin)
async def update_preset(
    preset_id: int,
    body: CCModelPresetUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
):
    item = cc_presets_store.get_by_id(preset_id)
    if not item:
        raise NotFoundError(resource=f"CC 模型预设 {preset_id}")
    data = body.model_dump(exclude_none=True)
    if "name" in data and data["name"] != item.name:
        if cc_presets_store.name_exists(data["name"], exclude_id=preset_id):
            raise ConflictError(resource=f"CC 模型预设 '{data['name']}'")
    updated = cc_presets_store.update(preset_id, **data)
    return _to_info(updated)


@router.delete("/{preset_id}")
@require_role(Role.Admin)
async def delete_preset(preset_id: int, _current_user: DBUser = Depends(get_current_active_user)):
    result = cc_presets_store.delete(preset_id)
    if result == "not_found":
        raise NotFoundError(resource=f"CC 模型预设 {preset_id}")
    if result == "protected":
        raise OperationFailedError(operation="删除 CC 模型预设", detail="默认预设不可删除")
    return {"ok": True}
