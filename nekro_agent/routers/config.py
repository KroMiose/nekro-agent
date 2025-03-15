import json
from typing import Any, Dict, List, Literal, get_args

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.core import logger
from nekro_agent.core.config import (
    ModelConfigGroup,
    PluginConfig,
    config,
    reload_config,
    save_config,
)
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.systems.user.deps import get_current_active_user
from nekro_agent.systems.user.perm import Role, require_role
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
    modifiable_configs: List[Dict[str, Any]] = []
    for key, value in config.model_dump().items():
        field = PluginConfig.model_fields.get(key)
        if field:
            # 获取基础类型
            base_type = str(type(value).__name__)

            # 处理列表类型，获取元素类型
            element_type = None
            if isinstance(value, list):
                element_type = str(type(value[0]).__name__) if value else "str"

            config_item = {
                "key": key,
                "value": value,
                "type": base_type,
                "element_type": element_type,  # 添加元素类型信息
                "title": PluginConfig.get_field_title(key),
                "description": field.description,  # 添加描述信息
                "placeholder": PluginConfig.get_field_placeholder(key),
                "required": get_field_extra(field, "required") or False,  # 添加必填标记
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

            # 添加文本域标识
            if get_field_extra(field, "is_textarea"):
                config_item["is_textarea"] = True

            modifiable_configs.append(config_item)

    return Ret.success(msg="获取成功", data=modifiable_configs)


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
async def get_config(key: str, _current_user: DBUser = Depends(get_current_active_user)) -> Ret:
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

    # 添加文本域标识
    if get_field_extra(field, "is_textarea"):
        config_item["is_textarea"] = True

    return Ret.success(msg="获取成功", data=config_item)


@router.post("/set", summary="设置配置值")
@require_role(Role.Admin)
async def set_config(key: str, value: str, _current_user: DBUser = Depends(get_current_active_user)) -> Ret:
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
        elif isinstance(_c_value, list):
            # 处理列表类型
            try:
                # 将字符串转换为 Python 列表
                import json

                parsed_value = json.loads(value)
                if not isinstance(parsed_value, list):
                    return Ret.fail(msg="输入必须是有效的列表格式")

                # 获取列表元素的类型
                if _c_value and len(_c_value) > 0:
                    # 尝试转换列表中的每个元素为正确的类型
                    converted_list = []
                    for item in parsed_value:
                        if isinstance(_c_value[0], bool):
                            if isinstance(item, str):
                                if item.lower() in ["true", "1", "yes"]:
                                    converted_list.append(True)
                                elif item.lower() in ["false", "0", "no"]:
                                    converted_list.append(False)
                                else:
                                    return Ret.fail(msg=f"列表中的布尔值格式错误: {item}")
                            else:
                                converted_list.append(bool(item))
                        else:
                            converted_list.append(type(_c_value[0])(item))
                    setattr(config, key, converted_list)
                else:
                    # 如果是空列表，直接设置
                    setattr(config, key, parsed_value)
            except json.JSONDecodeError:
                return Ret.fail(msg="输入必须是有效的 JSON 列表格式")
            except (ValueError, TypeError) as e:
                return Ret.fail(msg=f"列表元素类型转换失败: {e!s}")
        else:
            return Ret.fail(msg=f"不支持的配置类型: {type(_c_value)}")
    except ValueError as e:
        return Ret.fail(msg=f"配置值类型错误: {e!s}")

    return Ret.success(msg="设置成功")


@router.post("/batch", summary="批量更新配置")
@require_role(Role.Admin)
async def batch_update_config(
    body: BatchUpdateConfig,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """批量更新配置值"""
    try:
        for key, value in body.configs.items():
            if key not in config.model_dump():
                return Ret.fail(msg=f"配置项不存在: {key}")

            _c_value = getattr(config, key)
            logger.debug(f"更新配置: {key} = {value} | {_c_value=} | {type(_c_value)=}")
            logger.debug(f"检查类型: isinstance(_c_value, bool) = {isinstance(_c_value, bool)}")
            if isinstance(_c_value, bool):
                if value.lower() in ["true", "1", "yes"]:
                    setattr(config, key, True)
                elif value.lower() in ["false", "0", "no"]:
                    setattr(config, key, False)
                else:
                    return Ret.fail(msg=f"布尔值只能是 true 或 false: {key}")
            elif isinstance(_c_value, (int, float)):
                setattr(config, key, type(_c_value)(value))
            elif isinstance(_c_value, str):
                setattr(config, key, value)
            elif isinstance(_c_value, list):
                try:
                    # 将字符串转换为 Python 列表
                    parsed_value = json.loads(value)
                    if not isinstance(parsed_value, list):
                        return Ret.fail(msg=f"输入必须是有效的列表格式: {key}")

                    # 获取列表元素的类型
                    if _c_value and len(_c_value) > 0:
                        # 尝试转换列表中的每个元素为正确的类型
                        converted_list = []
                        for item in parsed_value:
                            if isinstance(_c_value[0], bool):
                                if isinstance(item, str):
                                    if item.lower() in ["true", "1", "yes"]:
                                        converted_list.append(True)
                                    elif item.lower() in ["false", "0", "no"]:
                                        converted_list.append(False)
                                    else:
                                        return Ret.fail(msg=f"列表中的布尔值格式错误: {item}")
                                else:
                                    converted_list.append(bool(item))
                            else:
                                converted_list.append(type(_c_value[0])(item))
                        setattr(config, key, converted_list)
                    else:
                        # 如果是空列表，直接设置
                        setattr(config, key, parsed_value)
                except json.JSONDecodeError:
                    return Ret.fail(msg=f"输入必须是有效的 JSON 列表格式: {key}")
                except (ValueError, TypeError) as e:
                    return Ret.fail(msg=f"列表元素类型转换失败: {e!s}")
            else:
                return Ret.fail(msg=f"不支持的配置类型: {type(_c_value)} ({key})")

        # 立即保存配置到文件
        save_config()
    except ValueError as e:
        return Ret.fail(msg=f"配置值类型错误: {e!s}")

    return Ret.success(msg="批量更新成功")


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
        save_config()
    except Exception as e:
        return Ret.fail(msg=f"保存失败: {e!s}")
    return Ret.success(msg="保存成功")


@router.get("/configs")
@require_role(Role.Admin)
async def get_config_list_with_placeholder(_current_user: DBUser = Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    """获取配置列表（包含占位符）"""
    config_list = []
    for key in PluginConfig.model_fields:
        config_list.append(
            {
                "key": key,
                "value": getattr(config, key),
                "title": PluginConfig.get_field_title(key),
                "placeholder": PluginConfig.get_field_placeholder(key),
            },
        )
    return config_list


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
            "label": "向量嵌入",
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
