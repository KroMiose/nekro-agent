import json
from typing import Any, Dict, List, Literal, get_args

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.core import logger
from nekro_agent.core.config import (
    CONFIG_PATH,
    ModelConfigGroup,
    PluginConfig,
    config,
    reload_config,
    save_config,
)
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.config_service import ConfigService
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.tools.common_util import get_app_version


class BatchUpdateConfig(BaseModel):
    """批量更新配置请求体"""

    configs: Dict[str, str]


router = APIRouter(prefix="/config", tags=["Config"])


def get_field_enum(field_type: Any) -> List[str] | None:
    """获取字段的枚举选项"""
    try:
        if hasattr(field_type, "__origin__") and field_type.__origin__ is Literal:
            return list(get_args(field_type))
    except Exception:
        pass
    return None


def get_field_extra(field: Any, key: str) -> Any:
    """获取字段的额外信息"""
    if hasattr(field, "json_schema_extra") and isinstance(field.json_schema_extra, dict):
        return field.json_schema_extra.get(key)
    return None


@router.get("/list", summary="获取可修改的配置列表")
@require_role(Role.Admin)
async def get_config_list(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取可修改的配置列表"""
    try:
        # 使用配置服务获取配置列表
        modifiable_configs = ConfigService.get_config_list(config)
        return Ret.success(msg="获取成功", data=modifiable_configs)
    except Exception as e:
        logger.error(f"获取配置列表失败: {e}")
        return Ret.error(msg=f"获取失败: {e!s}")


@router.get("/model-groups", summary="获取模型组列表")
@require_role(Role.Admin)
async def get_model_groups(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取所有模型组配置"""
    return Ret.success(msg="获取成功", data=config.MODEL_GROUPS)


@router.post("/model-groups/{group_name}", summary="更新模型组")
@require_role(Role.Admin)
async def update_model_group(
    group_name: str,
    model_config: ModelConfigGroup,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """更新或添加模型组配置"""
    try:
        # 直接使用整个model_config对象
        config.MODEL_GROUPS[group_name] = model_config
        save_config()
        return Ret.success(msg="更新成功")
    except Exception as e:
        return Ret.fail(msg=f"更新失败: {e!s}")


@router.delete("/model-groups/{group_name}", summary="删除模型组")
@require_role(Role.Admin)
async def delete_model_group(
    group_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """删除模型组配置"""
    try:
        if group_name not in config.MODEL_GROUPS:
            return Ret.fail(msg="模型组不存在")
        if group_name == "default":
            return Ret.fail(msg="默认模型组不能删除")
        del config.MODEL_GROUPS[group_name]
        save_config()
        return Ret.success(msg="删除成功")
    except Exception as e:
        return Ret.fail(msg=f"删除失败: {e!s}")


@router.get("/get", summary="获取配置值")
@require_role(Role.Admin)
async def get_config_item(key: str, _current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取配置值"""
    try:
        # 使用配置服务获取配置项
        config_item = ConfigService.get_config_item(config, key)
        if not config_item:
            return Ret.fail(msg="配置项不存在")
        return Ret.success(msg="获取成功", data=config_item)
    except Exception as e:
        logger.error(f"获取配置项失败: {e}")
        return Ret.error(msg=f"获取失败: {e!s}")


@router.post("/set", summary="设置配置值")
@require_role(Role.Admin)
async def set_config_value(key: str, value: str, _current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """设置配置值"""
    try:
        # 使用配置服务设置配置值
        success, error_msg = ConfigService.set_config_value(config, key, value)
        if not success:
            return Ret.fail(msg=error_msg)
        return Ret.success(msg="设置成功")
    except Exception as e:
        logger.error(f"设置配置值失败: {e}")
        return Ret.error(msg=f"设置失败: {e!s}")


@router.post("/batch", summary="批量更新配置")
@require_role(Role.Admin)
async def batch_update_config(
    body: BatchUpdateConfig,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """批量更新配置值"""
    try:
        # 使用配置服务批量更新配置
        success, error_msg = ConfigService.batch_update_config(config, body.configs)
        if not success:
            return Ret.fail(msg=error_msg or "批量更新失败")
        
        # 立即保存配置到文件
        success, error_msg = ConfigService.save_config(config, CONFIG_PATH)
        if not success:
            return Ret.fail(msg=f"保存配置失败: {error_msg or '未知错误'}")
            
        return Ret.success(msg="批量更新成功")
    except Exception as e:
        logger.error(f"批量更新配置失败: {e}")
        return Ret.error(msg=f"更新失败: {e!s}")


@router.post("/reload", summary="重载配置")
@require_role(Role.Admin)
async def reload_config_api(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """重载配置"""
    try:
        reload_config()
    except Exception as e:
        return Ret.fail(msg=f"重载失败: {e!s}")
    return Ret.success(msg="重载成功")


@router.post("/save", summary="保存配置")
@require_role(Role.Admin)
async def save_config_api(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """保存配置"""
    try:
        success, error_msg = ConfigService.save_config(config, CONFIG_PATH)
        if not success:
            return Ret.fail(msg=f"保存失败: {error_msg or '未知错误'}")
        return Ret.success(msg="保存成功")
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return Ret.error(msg=f"保存失败: {e!s}")


@router.get("/version", summary="获取应用版本")
@require_role(Role.User)
async def get_version(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取应用版本"""
    return Ret.success(msg="获取成功", data=get_app_version())


@router.get("/model-types", summary="获取支持的模型类型列表")
@require_role(Role.Admin)
async def get_model_types(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取支持的模型类型列表"""
    # 从 ModelConfigGroup 的 MODEL_TYPE 字段定义中获取所有类型
    model_types = get_args(ModelConfigGroup.model_fields["MODEL_TYPE"].annotation)
    
    # 构建类型与描述的映射
    type_info = {
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
    
    # 返回类型和描述
    model_type_info = [
        {
            "value": t, 
            "label": type_info.get(t, {}).get("label", t),
            "description": type_info.get(t, {}).get("description", ""),
            "color": type_info.get(t, {}).get("color", "default"),
            "icon": type_info.get(t, {}).get("icon", "EmojiObjects"),
        } 
        for t in model_types
    ]
    
    return Ret.success(msg="获取成功", data=model_type_info)
