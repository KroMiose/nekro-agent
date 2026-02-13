from typing import Any, Dict, List, Optional, get_args

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from nekro_agent.core.config import ModelConfigGroup, config, save_config
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import (
    ConfigInvalidError,
    ConfigNotFoundError,
    DefaultModelGroupDeleteError,
    ModelGroupNotFoundError,
    OperationFailedError,
)
from nekro_agent.services.config_service import UnifiedConfigService
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.tools.common_util import get_app_version


class BatchUpdateConfig(BaseModel):
    """批量更新配置请求体"""

    configs: Dict[str, str]


class ActionResponse(BaseModel):
    """简单操作响应"""

    ok: bool = True


class ConfigInfo(BaseModel):
    """配置基本信息"""

    config_key: str
    config_class: str
    config_file_path: Optional[str] = None
    config_type: str
    field_count: int


class ConfigItem(BaseModel):
    """配置项信息"""

    model_config = ConfigDict(extra="allow")

    key: str
    value: Any
    title: str
    description: Optional[str] = None
    placeholder: Optional[str] = None
    type: str
    is_complex: Optional[bool] = None
    element_type: Optional[str] = None
    key_type: Optional[str] = None
    value_type: Optional[str] = None
    field_schema: Optional[Dict[str, Any]] = None
    enum: Optional[List[str]] = None
    is_secret: Optional[bool] = None
    is_textarea: Optional[bool] = None
    ref_model_groups: Optional[bool] = None
    ref_presets: Optional[bool] = None
    ref_presets_multiple: Optional[bool] = None
    is_hidden: Optional[bool] = None
    required: Optional[bool] = None
    model_type: Optional[str] = None
    sub_item_name: Optional[str] = None
    enable_toggle: Optional[str] = None
    overridable: Optional[bool] = None
    is_need_restart: Optional[bool] = None
    i18n_title: Optional[Dict[str, str]] = None
    i18n_description: Optional[Dict[str, str]] = None


class ModelTypeOption(BaseModel):
    """模型类型描述"""

    value: str
    label: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


router = APIRouter(prefix="/config", tags=["Config"])


def _raise_config_error(
    *,
    config_key: str,
    item_key: Optional[str],
    error_msg: Optional[str],
    operation: str,
) -> None:
    if not error_msg:
        raise OperationFailedError(operation=operation)

    if "配置实例不存在" in error_msg:
        raise ConfigNotFoundError(key=config_key)

    if "配置项不存在" in error_msg:
        key = f"{config_key}.{item_key}" if item_key else config_key
        raise ConfigNotFoundError(key=key)

    if "无效" in error_msg or "invalid" in error_msg.lower():
        key = item_key or config_key
        raise ConfigInvalidError(key=key, reason=error_msg)

    raise OperationFailedError(operation=operation)


@router.get("/keys", summary="获取所有配置键列表", response_model=List[str])
@require_role(Role.Admin)
async def get_config_keys(_current_user: DBUser = Depends(get_current_active_user)) -> List[str]:
    """获取所有已注册的配置键列表"""
    return UnifiedConfigService.get_all_config_keys()


@router.get("/info/{config_key}", summary="获取配置基本信息", response_model=ConfigInfo)
@require_role(Role.Admin)
async def get_config_info(
    config_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ConfigInfo:
    """获取指定配置的基本信息"""
    config_info = UnifiedConfigService.get_config_info(config_key)
    if not config_info:
        raise ConfigNotFoundError(key=config_key)
    return ConfigInfo(**config_info)


@router.get("/list/{config_key}", summary="获取指定配置的配置列表", response_model=List[ConfigItem])
@require_role(Role.Admin)
async def get_config_list(
    config_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[ConfigItem]:
    """获取指定配置的配置列表"""
    try:
        config_list = UnifiedConfigService.get_config_list(config_key)
    except ValueError:
        raise ConfigNotFoundError(key=config_key) from None
    return [ConfigItem(**item) for item in config_list]


@router.get("/get/{config_key}/{item_key}", summary="获取配置项值", response_model=ConfigItem)
@require_role(Role.Admin)
async def get_config_item(
    config_key: str,
    item_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ConfigItem:
    """获取指定配置的配置项值"""
    config_item = UnifiedConfigService.get_config_item(config_key, item_key)
    if not config_item:
        raise ConfigNotFoundError(key=f"{config_key}.{item_key}")
    return ConfigItem(**config_item)


@router.post("/set/{config_key}/{item_key}", summary="设置配置项值", response_model=ActionResponse)
@require_role(Role.Admin)
async def set_config_value(
    config_key: str,
    item_key: str,
    value: str = Query(..., description="配置项值"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """设置指定配置的配置项值"""
    success, error_msg = UnifiedConfigService.set_config_value(config_key, item_key, value)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=item_key,
            error_msg=error_msg,
            operation="设置配置",
        )
    return ActionResponse(ok=True)


@router.post("/batch/{config_key}", summary="批量更新配置", response_model=ActionResponse)
@require_role(Role.Admin)
async def batch_update_config(
    config_key: str,
    body: BatchUpdateConfig,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """批量更新指定配置"""
    success, error_msg = UnifiedConfigService.batch_update_config(config_key, body.configs)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=None,
            error_msg=error_msg,
            operation="批量更新配置",
        )

    success, error_msg = UnifiedConfigService.save_config(config_key)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=None,
            error_msg=error_msg,
            operation="保存配置",
        )

    return ActionResponse(ok=True)


@router.post("/save/{config_key}", summary="保存配置", response_model=ActionResponse)
@require_role(Role.Admin)
async def save_config_api(
    config_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """保存指定配置到文件"""
    success, error_msg = UnifiedConfigService.save_config(config_key)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=None,
            error_msg=error_msg,
            operation="保存配置",
        )
    return ActionResponse(ok=True)


@router.post("/reload/{config_key}", summary="重置配置", response_model=ActionResponse)
@require_role(Role.Admin)
async def reload_config_api(
    config_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """重置指定配置"""
    success, error_msg = UnifiedConfigService.reload_config(config_key)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=None,
            error_msg=error_msg,
            operation="重置配置",
        )
    return ActionResponse(ok=True)


# ==================== 模型组管理API ====================


@router.get("/model-groups", summary="获取模型组列表", response_model=Dict[str, ModelConfigGroup])
@require_role(Role.Admin)
async def get_model_groups(_current_user: DBUser = Depends(get_current_active_user)) -> Dict[str, ModelConfigGroup]:
    """获取所有模型组配置"""
    return config.MODEL_GROUPS


@router.post("/model-groups/{group_name}", summary="更新模型组", response_model=ActionResponse)
@require_role(Role.Admin)
async def update_model_group(
    group_name: str,
    model_config: ModelConfigGroup,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """更新或添加模型组配置"""
    config.MODEL_GROUPS[group_name] = model_config
    save_config()
    return ActionResponse(ok=True)


@router.delete("/model-groups/{group_name}", summary="删除模型组", response_model=ActionResponse)
@require_role(Role.Admin)
async def delete_model_group(
    group_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """删除模型组配置"""
    if group_name not in config.MODEL_GROUPS:
        raise ModelGroupNotFoundError(name=group_name)
    if group_name == "default":
        raise DefaultModelGroupDeleteError

    del config.MODEL_GROUPS[group_name]
    save_config()
    return ActionResponse(ok=True)


@router.get("/model-types", summary="获取支持的模型类型列表", response_model=List[ModelTypeOption])
@require_role(Role.Admin)
async def get_model_types(_current_user: DBUser = Depends(get_current_active_user)) -> List[ModelTypeOption]:
    """获取支持的模型类型列表"""
    model_types = get_args(ModelConfigGroup.model_fields["MODEL_TYPE"].annotation)

    type_info: Dict[str, Dict[str, str]] = {
        "chat": {
            "label": "聊天",
            "description": "用于对话的模型",
            "color": "primary",
            "icon": "Chat",
        },
        "embedding": {
            "label": "嵌入",
            "description": "用于将文本转换为向量的模型",
            "color": "secondary",
            "icon": "Code",
        },
        "draw": {
            "label": "绘图",
            "description": "用于生成图像的模型",
            "color": "warning",
            "icon": "Brush",
        },
    }

    return [
        ModelTypeOption(
            value=type_name,
            label=type_info.get(type_name, {}).get("label") or type_name,
            description=type_info.get(type_name, {}).get("description") or "",
            color=type_info.get(type_name, {}).get("color") or "default",
            icon=type_info.get(type_name, {}).get("icon") or "EmojiObjects",
        )
        for type_name in model_types
    ]


@router.get("/version", summary="获取应用版本", response_model=str)
@require_role(Role.User)
async def get_version(_current_user: DBUser = Depends(get_current_active_user)) -> str:
    """获取应用版本"""
    return get_app_version()
