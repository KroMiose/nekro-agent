"""配置服务

提供通用的配置管理功能，可以应用于系统配置和插件配置。
"""

import inspect
import json
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    get_args,
    get_origin,
)

from pydantic import BaseModel

from nekro_agent.core import logger
from nekro_agent.core.config import CHANNEL_CONFIG_DIR
from nekro_agent.core.core_utils import ConfigBase, ConfigManager
from nekro_agent.core.os_env import OsEnv

T = TypeVar("T", bound=ConfigBase)


class ConfigType(str, Enum):
    """配置类型"""

    SYSTEM = "system"
    PLUGIN = "plugin"
    MODEL_GROUPS = "model_groups"
    ADAPTER = "adapter"
    SESSION = "session"


def _analyze_field_type(field_type: Any, value: Any = None) -> Dict[str, Any]:
    """分析字段类型

    Args:
        field_type: 字段类型注解
        value: 字段值

    Returns:
        Dict[str, Any]: 包含类型分析结果的字典
    """
    origin = get_origin(field_type)
    args = get_args(field_type)

    result = {
        "base_type": "str",
        "is_complex": False,
        "element_type": None,
        "key_type": None,
        "value_type": None,
        "field_schema": None,  # 新增：字段模式信息
    }

    # 检查是否是Pydantic模型
    if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
        result.update(
            {
                "base_type": "object",
                "is_complex": True,
                "field_schema": _get_model_schema(field_type),
            },
        )
        return result

    # 处理泛型类型
    if origin is list:
        result["base_type"] = "list"
        if args and len(args) > 0:
            element_type = args[0]
            if inspect.isclass(element_type) and issubclass(element_type, BaseModel):
                # List[CustomModel]
                result.update(
                    {
                        "is_complex": True,
                        "element_type": "object",
                        "field_schema": _get_model_schema(element_type),
                    },
                )
            else:
                # List[简单类型]
                result.update(
                    {
                        "element_type": _get_simple_type_name(element_type),
                    },
                )
        else:
            # 无类型参数的list，根据值推断
            element_type = _get_field_type(value[0]) if value and len(value) > 0 else "str"
            result.update(
                {
                    "element_type": element_type,
                },
            )

    elif origin is dict:
        result["base_type"] = "dict"
        if len(args) >= 2:
            key_type, value_type = args[0], args[1]
            if inspect.isclass(value_type) and issubclass(value_type, BaseModel):
                # Dict[str, CustomModel]
                result.update(
                    {
                        "is_complex": True,
                        "key_type": _get_simple_type_name(key_type),
                        "value_type": "object",
                        "field_schema": _get_model_schema(value_type),
                    },
                )
            else:
                # Dict[str, 简单类型]
                result.update(
                    {
                        "key_type": _get_simple_type_name(key_type),
                        "value_type": _get_simple_type_name(value_type),
                    },
                )
        else:
            # 无类型参数的dict
            result.update(
                {
                    "key_type": "str",
                    "value_type": "str",
                },
            )

    else:
        # 简单类型
        result.update(
            {
                "base_type": _get_field_type(value) if value is not None else _get_simple_type_name(field_type),
            },
        )

    return result


def _get_simple_type_name(type_annotation: Any) -> str:
    """获取简单类型的名称"""
    if type_annotation is str:
        return "str"
    if type_annotation is int:
        return "int"
    if type_annotation is float:
        return "float"
    if type_annotation is bool:
        return "bool"
    return "str"


def _get_model_schema(model_class: Any) -> Dict[str, Any]:
    """获取Pydantic模型的字段模式信息

    Args:
        model_class: Pydantic模型类

    Returns:
        Dict[str, Any]: 字段模式信息
    """
    if not inspect.isclass(model_class) or not issubclass(model_class, BaseModel):
        return {}

    schema = {}
    for field_name, field in model_class.model_fields.items():
        # 获取字段的默认值来辅助类型分析
        default_value = field.default if field.default is not ... else None

        # 使用更强大的类型分析函数
        type_info = _analyze_field_type(field.annotation, default_value)

        field_info = {
            "type": type_info["base_type"],
            "title": field.title or field_name,
            "description": field.description or "",
            "default": default_value,
            "required": field.is_required(),
        }

        # 如果是复杂类型，添加额外的类型信息
        if type_info.get("is_complex"):
            field_info["is_complex"] = True
            if type_info.get("element_type"):
                field_info["element_type"] = type_info["element_type"]
            if type_info.get("key_type"):
                field_info["key_type"] = type_info["key_type"]
            if type_info.get("value_type"):
                field_info["value_type"] = type_info["value_type"]
            if type_info.get("field_schema"):
                field_info["field_schema"] = type_info["field_schema"]

        # 添加特殊字段标记
        if hasattr(field, "json_schema_extra") and isinstance(field.json_schema_extra, dict):
            extra_fields = ["is_secret", "is_textarea", "placeholder"]
            for extra_field in extra_fields:
                if field.json_schema_extra.get(extra_field):
                    field_info[extra_field] = field.json_schema_extra.get(extra_field)

        schema[field_name] = field_info

    return schema


class UnifiedConfigService:
    """统一配置服务

    提供基于配置键的统一配置管理功能，支持多种类型的配置实例。
    """

    @staticmethod
    def _get_config_instance(config_key: str) -> Optional[ConfigBase]:
        """获取或动态加载配置实例"""
        # 1. 检查缓存
        instance = ConfigManager.get_config(config_key)
        if instance:
            return instance

        # 2. 尝试动态加载
        try:
            from nekro_agent.core.overridable_config import OverridableConfig

            path: Optional[Path] = None

            if config_key.startswith("adapter_override_"):
                adapter_key = config_key.replace("adapter_override_", "")
                path = Path(OsEnv.DATA_DIR) / "configs" / adapter_key / "overrides.yaml"
                instance = OverridableConfig.load_from_path(path)

            elif config_key.startswith("channel_config_"):
                chat_key = config_key.replace("channel_config_", "")
                adapter_key = chat_key.split("-")[0]
                path = CHANNEL_CONFIG_DIR / adapter_key / f"{chat_key}.yaml"
                instance = OverridableConfig.load_from_path(path)

            if instance:
                ConfigManager.register_config(config_key, instance)
                instance.dump_config()  # 确保文件存在
                return instance

        except Exception as e:
            logger.error(f"动态加载配置失败: {config_key}, 错误: {e}")
            return None

        # 3. 降级到静态注册的配置
        return ConfigManager.get_config(config_key)

    @staticmethod
    def get_config_list(config_key: str) -> List[Dict[str, Any]]:
        """获取指定配置的配置列表

        Args:
            config_key: 配置键

        Returns:
            List[Dict[str, Any]]: 配置项列表
        """
        config_obj = UnifiedConfigService._get_config_instance(config_key)
        if not config_obj:
            raise ValueError(f"配置实例不存在: {config_key}")

        return ConfigService.get_config_list(config_obj)

    @staticmethod
    def get_config_item(config_key: str, item_key: str) -> Optional[Dict[str, Any]]:
        """获取指定配置的单个配置项

        Args:
            config_key: 配置键
            item_key: 配置项键名

        Returns:
            Optional[Dict[str, Any]]: 配置项信息，如果不存在则返回 None
        """
        config_obj = UnifiedConfigService._get_config_instance(config_key)
        if not config_obj:
            return None

        return ConfigService.get_config_item(config_obj, item_key)

    @staticmethod
    def set_config_value(config_key: str, item_key: str, value: str) -> Tuple[bool, str]:
        """设置指定配置的配置项值

        Args:
            config_key: 配置键
            item_key: 配置项键名
            value: 配置项值（字符串形式）

        Returns:
            Tuple[bool, str]: (是否成功, 错误消息)
        """
        config_obj = UnifiedConfigService._get_config_instance(config_key)
        if not config_obj:
            return False, f"配置实例不存在: {config_key}"

        return ConfigService.set_config_value(config_obj, item_key, value)

    @staticmethod
    def batch_update_config(config_key: str, configs: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """批量更新指定配置

        Args:
            config_key: 配置键
            configs: 配置字典，键为配置项名称，值为配置项值

        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误消息)
        """
        config_obj = UnifiedConfigService._get_config_instance(config_key)
        if not config_obj:
            return False, f"配置实例不存在: {config_key}"

        return ConfigService.batch_update_config(config_obj, configs)

    @staticmethod
    def save_config(config_key: str, file_path: Optional[Path] = None) -> Tuple[bool, Optional[str]]:
        """保存指定配置到文件

        Args:
            config_key: 配置键
            file_path: 配置文件路径（可选，使用配置实例的默认路径）

        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误消息)
        """
        config_obj = UnifiedConfigService._get_config_instance(config_key)
        if not config_obj:
            return False, f"配置实例不存在: {config_key}"

        return ConfigService.save_config(config_obj, file_path)

    @staticmethod
    def reload_config(config_key: str, file_path: Optional[Path] = None) -> Tuple[bool, Optional[str]]:
        """重新加载指定配置

        Args:
            config_key: 配置键
            file_path: 配置文件路径（可选）

        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误消息)
        """
        try:
            config_obj = UnifiedConfigService._get_config_instance(config_key)
            if not config_obj:
                return False, f"配置实例不存在: {config_key}"

            # 获取要重载的路径
            reload_path = file_path or config_obj.get_config_file_path()
            if not reload_path:
                return False, f"重载失败: 配置文件路径未知: {config_key}"

            # 获取配置类并从路径加载
            config_class = config_obj.__class__
            new_config = config_class.load_from_path(reload_path)

            # 注册新实例并加载到env
            ConfigManager.register_config(config_key, new_config)
            new_config.load_config_to_env()

        except Exception as e:
            logger.error(f"重新加载配置失败: {config_key}, 错误: {e}")
            return False, str(e)
        else:
            return True, None

    @staticmethod
    def get_all_config_keys() -> List[str]:
        """获取所有已注册的配置键"""
        return ConfigManager.get_all_config_keys()

    @staticmethod
    def get_config_info(config_key: str) -> Optional[Dict[str, Any]]:
        """获取配置基本信息

        Args:
            config_key: 配置键

        Returns:
            Optional[Dict[str, Any]]: 配置信息
        """
        config_obj = UnifiedConfigService._get_config_instance(config_key)
        if not config_obj:
            return None

        return {
            "config_key": config_key,
            "config_class": config_obj.__class__.__name__,
            "config_file_path": (str(config_obj.get_config_file_path()) if config_obj.get_config_file_path() else None),
            "config_type": _get_config_type(config_key),
            "field_count": len(config_obj.__class__.model_fields),
        }


class ConfigService:
    """配置服务

    提供统一的配置管理功能，支持系统配置和插件配置。
    """

    @staticmethod
    def get_config_list(config_obj: ConfigBase) -> List[Dict[str, Any]]:
        """获取配置列表

        Args:
            config_obj: 配置对象实例

        Returns:
            List[Dict[str, Any]]: 配置项列表
        """
        result = []

        for key, field in config_obj.__class__.model_fields.items():
            # 获取字段值
            value = getattr(config_obj, key, None)

            # 分析字段类型
            type_info = _analyze_field_type(field.annotation, value)

            # 构建配置项
            config_item = {
                "key": key,
                "value": value,
                "type": type_info["base_type"],
                "is_complex": type_info.get("is_complex", False),
                "element_type": type_info.get("element_type"),
                "key_type": type_info.get("key_type"),
                "value_type": type_info.get("value_type"),
                "field_schema": type_info.get("field_schema"),
                "title": config_obj.__class__.get_field_title(key) or key,
                "description": field.description,
                "placeholder": config_obj.__class__.get_field_placeholder(key),
            }

            # 添加特殊字段标记
            if hasattr(field, "json_schema_extra") and isinstance(field.json_schema_extra, dict):
                extra_fields = [
                    "is_secret",
                    "is_textarea",
                    "required",
                    "is_hidden",
                    "ref_model_groups",
                    "model_type",
                    "sub_item_name",
                    "enable_toggle",
                    "overridable",
                    "load_to_sysenv",
                    "load_sysenv_as",
                    "load_to_nonebot_env",
                    "load_nbenv_as",
                ]
                for extra_field in extra_fields:
                    if field.json_schema_extra.get(extra_field):
                        config_item[extra_field] = field.json_schema_extra.get(extra_field)

            # 添加枚举选项
            enum_values = _get_field_enum(field.annotation)
            if enum_values:
                config_item["enum"] = enum_values

            result.append(config_item)

        return result

    @staticmethod
    def get_config_item(config_obj: ConfigBase, key: str) -> Optional[Dict[str, Any]]:
        """获取单个配置项

        Args:
            config_obj: 配置对象实例
            key: 配置项键名

        Returns:
            Optional[Dict[str, Any]]: 配置项信息，如果不存在则返回 None
        """
        if key not in config_obj.model_dump():
            return None

        field = config_obj.__class__.model_fields.get(key)
        if not field:
            return None

        # 获取字段值
        value = getattr(config_obj, key)

        # 分析字段类型
        type_info = _analyze_field_type(field.annotation, value)

        # 构建配置项
        config_item = {
            "key": key,
            "value": value,
            "type": type_info["base_type"],
            "is_complex": type_info.get("is_complex", False),
            "element_type": type_info.get("element_type"),
            "title": config_obj.__class__.get_field_title(key) or key,
            "description": field.description,
            "placeholder": config_obj.__class__.get_field_placeholder(key),
        }

        # 添加特殊字段标记
        if hasattr(field, "json_schema_extra") and isinstance(field.json_schema_extra, dict):
            extra_fields = [
                "is_secret",
                "is_textarea",
                "required",
                "is_hidden",
                "ref_model_groups",
                "model_type",
                "sub_item_name",
                "enable_toggle",
                "overridable",
                "load_to_sysenv",
                "load_sysenv_as",
                "load_to_nonebot_env",
                "load_nbenv_as",
            ]
            for extra_field in extra_fields:
                if field.json_schema_extra.get(extra_field):
                    config_item[extra_field] = field.json_schema_extra.get(extra_field)

        # 添加枚举选项
        enum_values = _get_field_enum(field.annotation)
        if enum_values:
            config_item["enum"] = enum_values

        return config_item

    @staticmethod
    def set_config_value(config_obj: ConfigBase, key: str, value: str) -> Tuple[bool, str]:
        """设置配置项值

        Args:
            config_obj: 配置对象实例
            key: 配置项键名
            value: 配置项值（字符串形式）

        Returns:
            Tuple[bool, str]: (是否成功, 错误消息)
        """
        if key not in config_obj.model_dump():
            return False, f"配置项 {key} 不存在"

        try:
            current_value = getattr(config_obj, key)

            # 根据类型转换值
            if isinstance(current_value, bool):
                if value.lower() in ["true", "1", "yes", "t", "y"]:
                    setattr(config_obj, key, True)
                elif value.lower() in ["false", "0", "no", "f", "n"]:
                    setattr(config_obj, key, False)
                else:
                    return False, "布尔值只能是 true 或 false"
            elif isinstance(current_value, (int, float)):
                setattr(config_obj, key, type(current_value)(value))
            elif isinstance(current_value, str):
                setattr(config_obj, key, value)
            elif isinstance(current_value, (list, dict)):
                try:
                    parsed_value = json.loads(value)
                    # 简单类型检查
                    if isinstance(current_value, list) and not isinstance(parsed_value, list):
                        return False, "输入必须是有效的列表格式"
                    if isinstance(current_value, dict) and not isinstance(parsed_value, dict):
                        return False, "输入必须是有效的对象格式"

                    # 对于复杂类型（如 List[Pydantic模型]），尝试使用 Pydantic 验证
                    field_info = config_obj.__class__.model_fields.get(key)
                    if field_info:
                        test_data = {key: parsed_value}
                        config_obj.__class__.model_validate(test_data)
                        setattr(config_obj, key, parsed_value)
                    else:
                        setattr(config_obj, key, parsed_value)

                except json.JSONDecodeError:
                    return False, "输入必须是有效的 JSON 格式"
                except (ValueError, TypeError) as e:
                    return False, f"数据格式转换失败: {e}"
            else:
                return False, f"不支持的配置类型: {type(current_value)}"

        except ValueError as e:
            return False, f"配置值类型错误: {e}"
        except Exception as e:
            return False, f"设置配置值时发生错误: {e}"
        else:
            return True, ""

    @staticmethod
    def batch_update_config(config_obj: ConfigBase, configs: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """批量更新配置

        Args:
            config_obj: 配置对象实例
            configs: 配置字典，键为配置项名称，值为配置项值

        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误消息)
        """
        for key, value in configs.items():
            if key not in config_obj.model_dump():
                return False, f"配置项不存在: {key}"

            success, message = ConfigService.set_config_value(config_obj, key, value)
            if not success:
                return False, message

        return True, None

    @staticmethod
    def save_config(config_obj: ConfigBase, file_path: Optional[Path] = None) -> Tuple[bool, Optional[str]]:
        """保存配置到文件

        Args:
            config_obj: 配置对象实例
            file_path: 配置文件路径

        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误消息)
        """
        try:
            config_obj.dump_config(file_path)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False, str(e)
        else:
            return True, None


def _get_field_type(value: Any) -> str:
    """根据值获取字段类型

    Args:
        value: 字段值

    Returns:
        str: 字段类型名称
    """
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return "str"


def _get_field_enum(field_type: Any) -> Optional[List[str]]:
    """获取字段的枚举选项

    Args:
        field_type: 字段类型

    Returns:
        Optional[List[str]]: 枚举选项列表，如果不是枚举类型则返回 None
    """
    try:
        if hasattr(field_type, "__origin__") and field_type.__origin__ is Literal:
            return list(get_args(field_type))
    except Exception:
        pass
    return None


def _get_config_type(config_key: str) -> str:
    """根据配置键获取配置类型

    Args:
        config_key: 配置键

    Returns:
        str: 配置类型
    """
    if config_key == "system":
        return ConfigType.SYSTEM.value
    if config_key.startswith("plugin."):
        return ConfigType.PLUGIN.value
    if config_key == "model_groups":
        return ConfigType.MODEL_GROUPS.value
    if config_key.startswith("adapter."):
        return ConfigType.ADAPTER.value
    if config_key.startswith("session."):
        return ConfigType.SESSION.value
    return "unknown"
