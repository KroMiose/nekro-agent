import asyncio
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.core.cc_model_presets import cc_presets_store
from nekro_agent.models.db_user import DBUser
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.cc_model_preset import (
    CCModelPresetCreate,
    CCModelPresetInfo,
    CCModelPresetListResponse,
    CCModelPresetUpdate,
)
from nekro_agent.schemas.errors import ConflictError, NotFoundError, OperationFailedError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.services.workspace.manager import WorkspaceService

router = APIRouter(prefix="/cc-model-presets", tags=["CC Model Presets"])


class CCModelPresetTestItem(BaseModel):
    preset_id: int
    preset_name: str
    model_name: str
    success: bool
    latency_ms: int
    used_model: str | None = None
    response_text: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: str | None = None


class CCModelPresetTestRequest(BaseModel):
    preset_ids: list[int]


class CCModelPresetTestResponse(BaseModel):
    items: list[CCModelPresetTestItem]


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


@router.post("/test", response_model=CCModelPresetTestResponse)
@require_role(Role.Admin)
async def test_presets(
    body: CCModelPresetTestRequest,
    _current_user: DBUser = Depends(get_current_active_user),
):
    from nekro_agent.services.agent.anthropic import resolve_cc_test_model, test_anthropic_messages

    async def run_single(preset_id: int) -> CCModelPresetTestItem:
        preset = cc_presets_store.get_by_id(preset_id)
        if not preset:
            return CCModelPresetTestItem(
                preset_id=preset_id,
                preset_name="",
                model_name="",
                success=False,
                latency_ms=0,
                error_message=f"CC 模型组不存在: {preset_id}",
            )

        model_name = resolve_cc_test_model(
            model_type=preset.model_type,
            preset_model=preset.preset_model,
            anthropic_model=preset.anthropic_model,
            small_fast_model=preset.small_fast_model,
            default_sonnet=preset.default_sonnet,
            default_opus=preset.default_opus,
            default_haiku=preset.default_haiku,
        )
        if not preset.base_url.strip():
            return CCModelPresetTestItem(
                preset_id=preset.id,
                preset_name=preset.name,
                model_name=model_name,
                success=False,
                latency_ms=0,
                error_message="Base URL 不能为空",
            )
        if not preset.auth_token.strip():
            return CCModelPresetTestItem(
                preset_id=preset.id,
                preset_name=preset.name,
                model_name=model_name,
                success=False,
                latency_ms=0,
                error_message="Auth Token 不能为空",
            )
        if not model_name:
            return CCModelPresetTestItem(
                preset_id=preset.id,
                preset_name=preset.name,
                model_name="",
                success=False,
                latency_ms=0,
                error_message="缺少可用于测试的模型名称",
            )

        started = time.perf_counter()
        try:
            result = await test_anthropic_messages(
                base_url=preset.base_url,
                auth_token=preset.auth_token,
                model=model_name,
                api_timeout_ms=preset.api_timeout_ms,
            )
            latency_ms = max(1, int((time.perf_counter() - started) * 1000))
            return CCModelPresetTestItem(
                preset_id=preset.id,
                preset_name=preset.name,
                model_name=model_name,
                success=True,
                latency_ms=latency_ms,
                used_model=result.model,
                response_text=result.response_text,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
        except Exception as e:
            latency_ms = max(1, int((time.perf_counter() - started) * 1000))
            return CCModelPresetTestItem(
                preset_id=preset.id,
                preset_name=preset.name,
                model_name=model_name,
                success=False,
                latency_ms=latency_ms,
                error_message=str(e),
            )

    items = await asyncio.gather(*(run_single(preset_id) for preset_id in body.preset_ids))
    return CCModelPresetTestResponse(items=items)


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
    if updated is None:
        raise OperationFailedError(operation="更新 CC 模型预设", detail=f"预设 {preset_id} 更新失败")
    await WorkspaceService.sync_workspace_settings_for_preset(updated.id, updated)
    return _to_info(updated)


@router.delete("/{preset_id}")
@require_role(Role.Admin)
async def delete_preset(preset_id: int, _current_user: DBUser = Depends(get_current_active_user)):
    bound_workspaces = []
    for workspace in await DBWorkspace.all():
        raw_preset_id = (workspace.metadata or {}).get("cc_model_preset_id")
        try:
            if raw_preset_id is not None and int(raw_preset_id) == preset_id:
                bound_workspaces.append(workspace.name)
        except (TypeError, ValueError):
            continue

    if bound_workspaces:
        raise ConflictError(
            resource=f"CC 模型组 {preset_id}",
            detail=f"仍被工作区引用: {', '.join(bound_workspaces[:10])}",
            data={"workspaces": bound_workspaces},
        )

    result = cc_presets_store.delete(preset_id)
    if result == "not_found":
        raise NotFoundError(resource=f"CC 模型预设 {preset_id}")
    if result == "protected":
        raise OperationFailedError(operation="删除 CC 模型预设", detail="默认预设不可删除")
    return {"ok": True}
