from typing import Any, Dict, List, Literal, get_args

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.core.config import (
    ModelConfigGroup,
    PluginConfig,
    config,
    reload_config,
    save_config,
)
from nekro_agent.schemas.message import Ret
from nekro_agent.systems.user.deps import get_current_active_user


class BatchUpdateConfig(BaseModel):
    """批量更新配置请求体"""
    configs: Dict[str, str]


class ModelGroupConfig(BaseModel):
    """模型组配置"""
    CHAT_MODEL: str
    CHAT_PROXY: str
    BASE_URL: str
    API_KEY: str


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
async def get_config_list(_=Depends(get_current_active_user)) -> Ret:
    """获取可修改的配置列表"""
    modifiable_configs: List[Dict[str, Any]] = []
    for key, value in config.model_dump().items():
        if isinstance(value, (int, float, bool, str)):
            field = PluginConfig.model_fields.get(key)
            if field:
                config_item = {
                    "key": key,
                    "value": value,
                    "type": str(type(value).__name__),
                    "title": PluginConfig.get_field_title(key),
                    "placeholder": PluginConfig.get_field_placeholder(key),
                }
                # 添加枚举选项
                enum_values = get_field_enum(field.annotation)
                if enum_values:
                    config_item["enum"] = enum_values
                # 添加模型组引用标识
                if get_field_extra(field, "ref_model_groups"):
                    config_item["ref_model_groups"] = True
                # 添加隐藏标识
                if get_field_extra(field, "is_hidden"):
                    config_item["is_hidden"] = True
                # 添加密钥标识
                if get_field_extra(field, "is_secret"):
                    config_item["is_secret"] = True
                modifiable_configs.append(config_item)
    return Ret.success(msg="获取成功", data=modifiable_configs)


@router.get("/model-groups", summary="获取模型组列表")
async def get_model_groups(_=Depends(get_current_active_user)) -> Ret:
    """获取所有模型组配置"""
    return Ret.success(msg="获取成功", data=config.MODEL_GROUPS)


@router.post("/model-groups/{group_name}", summary="更新模型组")
async def update_model_group(
    group_name: str,
    model_config: ModelGroupConfig,
    _=Depends(get_current_active_user),
) -> Ret:
    """更新或添加模型组配置"""
    try:
        config.MODEL_GROUPS[group_name] = model_config.model_dump()
        return Ret.success(msg="更新成功")
    except Exception as e:
        return Ret.fail(msg=f"更新失败: {e!s}")


@router.delete("/model-groups/{group_name}", summary="删除模型组")
async def delete_model_group(
    group_name: str,
    _=Depends(get_current_active_user),
) -> Ret:
    """删除模型组配置"""
    try:
        if group_name not in config.MODEL_GROUPS:
            return Ret.fail(msg="模型组不存在")
        if group_name == "default":
            return Ret.fail(msg="默认模型组不能删除")
        del config.MODEL_GROUPS[group_name]
        return Ret.success(msg="删除成功")
    except Exception as e:
        return Ret.fail(msg=f"删除失败: {e!s}")


@router.get("/get", summary="获取配置值")
async def get_config(key: str, _=Depends(get_current_active_user)) -> Ret:
    """获取配置值"""
    if key not in config.model_dump():
        return Ret.fail(msg="配置项不存在")
    
    field = PluginConfig.model_fields.get(key)
    if not field:
        return Ret.fail(msg="配置项不存在")
    
    config_item = {
        "key": key,
        "value": getattr(config, key),
        "type": str(type(getattr(config, key)).__name__),
        "title": PluginConfig.get_field_title(key),
    }
    
    # 添加枚举选项
    enum_values = get_field_enum(field.annotation)
    if enum_values:
        config_item["enum"] = enum_values
    
    # 添加模型组引用标识
    if get_field_extra(field, "ref_model_groups"):
        config_item["ref_model_groups"] = True
    
    # 添加隐藏标识
    if get_field_extra(field, "is_hidden"):
        config_item["is_hidden"] = True
    
    # 添加密钥标识
    if get_field_extra(field, "is_secret"):
        config_item["is_secret"] = True
    
    return Ret.success(msg="获取成功", data=config_item)


@router.post("/set", summary="设置配置值")
async def set_config(key: str, value: str, _=Depends(get_current_active_user)) -> Ret:
    """设置配置值"""
    if key not in config.model_dump():
        return Ret.fail(msg="配置项不存在")
    
    try:
        _c_value = getattr(config, key)
        if isinstance(_c_value, (int, float)):
            setattr(config, key, type(_c_value)(value))
        elif isinstance(_c_value, bool):
            if value.lower() in ["true", "1", "yes"]:
                setattr(config, key, True)
            elif value.lower() in ["false", "0", "no"]:
                setattr(config, key, False)
            else:
                return Ret.fail(msg="布尔值只能是 true 或 false")
        elif isinstance(_c_value, str):
            setattr(config, key, value)
        else:
            return Ret.fail(msg=f"不支持的配置类型: {type(_c_value)}")
    except ValueError:
        return Ret.fail(msg="配置值类型错误")
    
    return Ret.success(msg="设置成功")


@router.post("/batch", summary="批量更新配置")
async def batch_update_config(
    body: BatchUpdateConfig,
    _=Depends(get_current_active_user),
) -> Ret:
    """批量更新配置值"""
    try:
        for key, value in body.configs.items():
            if key not in config.model_dump():
                return Ret.fail(msg=f"配置项不存在: {key}")
            
            _c_value = getattr(config, key)
            if isinstance(_c_value, (int, float)):
                setattr(config, key, type(_c_value)(value))
            elif isinstance(_c_value, bool):
                if value.lower() in ["true", "1", "yes"]:
                    setattr(config, key, True)
                elif value.lower() in ["false", "0", "no"]:
                    setattr(config, key, False)
                else:
                    return Ret.fail(msg=f"布尔值只能是 true 或 false: {key}")
            elif isinstance(_c_value, str):
                setattr(config, key, value)
            else:
                return Ret.fail(msg=f"不支持的配置类型: {type(_c_value)} ({key})")
    except ValueError as e:
        return Ret.fail(msg=f"配置值类型错误: {e!s}")
    
    return Ret.success(msg="批量更新成功")


@router.post("/reload", summary="重载配置")
async def reload_config_api(_=Depends(get_current_active_user)) -> Ret:
    """重载配置"""
    try:
        reload_config()
    except Exception as e:
        return Ret.fail(msg=f"重载失败: {e!s}")
    return Ret.success(msg="重载成功")


@router.post("/save", summary="保存配置")
async def save_config_api(_=Depends(get_current_active_user)) -> Ret:
    """保存配置"""
    try:
        save_config()
    except Exception as e:
        return Ret.fail(msg=f"保存失败: {e!s}")
    return Ret.success(msg="保存成功")


@router.get("/configs")
async def get_config_list_with_placeholder() -> List[Dict[str, Any]]:
    """获取配置列表（包含占位符）"""
    config_list = []
    for key in PluginConfig.model_fields:
        config_list.append({
            "key": key,
            "value": getattr(config, key),
            "title": PluginConfig.get_field_title(key),
            "placeholder": PluginConfig.get_field_placeholder(key),
        })
    return config_list 