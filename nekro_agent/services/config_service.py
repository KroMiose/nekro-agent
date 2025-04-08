"""配置服务

提供通用的配置管理功能，可以应用于系统配置和插件配置。
"""

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
    Type,
    TypeVar,
    Union,
    get_args,
)

from nekro_agent.core import logger
from nekro_agent.core.core_utils import ConfigBase

T = TypeVar("T", bound=ConfigBase)


class ConfigType(str, Enum):
    """配置类型"""

    SYSTEM = "system"
    PLUGIN = "plugin"


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

            # 基础类型
            base_type = _get_field_type(value)

            # 处理列表类型，获取元素类型
            element_type = None
            if isinstance(value, list) and value:
                element_type = _get_field_type(value[0])

            # 构建配置项
            config_item = {
                "key": key,
                "value": value,
                "type": base_type,
                "element_type": element_type,
                "title": config_obj.__class__.get_field_title(key) or key,
                "description": field.description,
                "placeholder": config_obj.__class__.get_field_placeholder(key),
            }

            # 添加特殊字段标记
            if hasattr(field, "json_schema_extra") and isinstance(field.json_schema_extra, dict):
                if field.json_schema_extra.get("is_secret"):
                    config_item["is_secret"] = True
                if field.json_schema_extra.get("is_textarea"):
                    config_item["is_textarea"] = True
                if field.json_schema_extra.get("required"):
                    config_item["required"] = True
                if field.json_schema_extra.get("is_hidden"):
                    config_item["is_hidden"] = True
                if field.json_schema_extra.get("ref_model_groups"):
                    config_item["ref_model_groups"] = True

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

        # 构建配置项
        config_item = {
            "key": key,
            "value": value,
            "type": _get_field_type(value),
            "title": config_obj.__class__.get_field_title(key) or key,
            "description": field.description,
            "placeholder": config_obj.__class__.get_field_placeholder(key),
        }

        # 添加特殊字段标记
        if hasattr(field, "json_schema_extra") and isinstance(field.json_schema_extra, dict):
            if field.json_schema_extra.get("is_secret"):
                config_item["is_secret"] = True
            if field.json_schema_extra.get("is_textarea"):
                config_item["is_textarea"] = True
            if field.json_schema_extra.get("required"):
                config_item["required"] = True
            if field.json_schema_extra.get("is_hidden"):
                config_item["is_hidden"] = True
            if field.json_schema_extra.get("ref_model_groups"):
                config_item["ref_model_groups"] = True

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
            elif isinstance(current_value, list):
                try:
                    parsed_value = json.loads(value)
                    if not isinstance(parsed_value, list):
                        return False, "输入必须是有效的列表格式"

                    # 如果是空列表，直接设置
                    if not current_value:
                        setattr(config_obj, key, parsed_value)
                        return True, ""

                    # 尝试转换列表中的每个元素为正确的类型
                    converted_list = []
                    for item in parsed_value:
                        if isinstance(current_value[0], bool):
                            if isinstance(item, str):
                                if item.lower() in ["true", "1", "yes"]:
                                    converted_list.append(True)
                                elif item.lower() in ["false", "0", "no"]:
                                    converted_list.append(False)
                                else:
                                    return False, f"列表中的布尔值格式错误: {item}"
                            else:
                                converted_list.append(bool(item))
                        else:
                            converted_list.append(type(current_value[0])(item))

                    setattr(config_obj, key, converted_list)
                except json.JSONDecodeError:
                    return False, "输入必须是有效的 JSON 列表格式"
                except (ValueError, TypeError) as e:
                    return False, f"列表元素类型转换失败: {e}"
            else:
                return False, f"不支持的配置类型: {type(current_value)}"

        except ValueError as e:
            return False, f"配置值类型错误: {e}"
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
    def save_config(config_obj: ConfigBase, file_path: Path) -> Tuple[bool, Optional[str]]:
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
