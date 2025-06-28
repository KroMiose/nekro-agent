import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, ClassVar, Dict, Optional, Type, TypeVar, Union
from urllib.parse import quote_plus

import nonebot
import yaml
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, PrivateAttr


class ArgTypes:

    @staticmethod
    def _use_arg(arg_key: str, default: Any = None) -> Any:
        if arg_key in sys.argv:
            index = sys.argv.index(arg_key)
            if index + 1 < len(sys.argv):
                return sys.argv[index + 1]
        return default

    @staticmethod
    def Str(key: str, default: str = "") -> str:
        return str(ArgTypes._use_arg(key, default))

    @staticmethod
    def Int(key: str, default: int = 0) -> int:
        return int(ArgTypes._use_arg(key, default))

    @staticmethod
    def Float(key: str, default: float = 0.0) -> float:
        return float(ArgTypes._use_arg(key, default))

    @staticmethod
    def Bool(key: str) -> bool:
        return key in sys.argv


class OsEnvTypes:

    @staticmethod
    def _use_env(env_key: str, default: Union[Any, Callable[[], Any]]) -> Any:
        if callable(default):
            return default()
        return os.environ.get(f"NEKRO_{env_key.upper()}", default)

    @staticmethod
    def Str(key: str, default: Union[str, Callable[[], str]] = "") -> str:
        if callable(default):
            return default()
        return str(OsEnvTypes._use_env(key, default))

    @staticmethod
    def Int(key: str, default: Union[int, Callable[[], int]] = 0) -> int:
        if callable(default):
            return default()
        return int(OsEnvTypes._use_env(key, default))

    @staticmethod
    def Float(key: str, default: Union[float, Callable[[], float]] = 0.0) -> float:
        if callable(default):
            return default()
        return float(OsEnvTypes._use_env(key, default))

    @staticmethod
    def Bool(key: str) -> bool:
        return str(OsEnvTypes._use_env(key, "false")).lower() == "true"


class ExtraField(BaseModel):
    is_hidden: bool = Field(default=False, title="配置项可见性控制", description="设置为True时，该配置项将在WebUI界面中被隐藏")
    is_secret: bool = Field(
        default=False,
        title="敏感信息保护",
        description="设置为True时，输入内容将以密码形式('••••')显示，用于保护API密钥等敏感数据",
    )
    placeholder: str = Field(default="", title="输入提示文本", description="当字段未填写时在输入框中显示的提示文本")
    is_textarea: bool = Field(default=False, title="多行文本支持", description="设置为True时，将使用多行文本区域而非单行输入框")
    ref_model_groups: bool = Field(
        default=False,
        title="模型组引用标识",
        description="设置为True时，表示该字段需要从系统中已配置的模型组中选择",
    )
    model_type: str = Field(
        default="",
        title="模型类型规范",
        description="指定引用的模型类型标识符，仅在ref_model_groups为True时生效",
    )
    required: bool = Field(
        default=False,
        title="必填字段标识",
        description="设置为True时，前端将验证该字段必须填写才能提交表单",
    )
    overridable: bool = Field(
        default=False,
        title="可覆盖字段标识",
        description="设置为True时，该配置项将可以在适配器或会话级进行独立覆盖",
    )
    sub_item_name: str = Field(
        default="项目",
        title="子项名称",
        description="指定该配置项为列表时，子项目的元素名称，默认值为'项目'",
    )
    load_to_sysenv: bool = Field(
        default=False,
        title="环境变量加载控制",
        description="设置为True时，该配置项的值将被加载到系统环境变量中",
    )
    load_sysenv_as: str = Field(
        default="",
        title="环境变量名称定义",
        description="指定将配置项加载为环境变量时使用的变量名，仅在load_to_env为True时生效",
    )
    load_to_nonebot_env: bool = Field(
        default=False,
        title="nonebot环境变量加载控制",
        description="设置为True时，该配置项的值将被加载到nonebot的环境变量中",
    )
    load_nbenv_as: str = Field(
        default="",
        title="nonebot环境变量名称定义",
        description="指定将配置项加载到nonebot的环境变量时使用的变量名，仅在load_to_nbenv_as为True时生效",
    )


class ConfigManager:
    """配置管理器 - 统一管理所有配置实例"""

    _configs: Dict[str, "ConfigBase"] = {}

    @classmethod
    def register_config(cls, config_key: str, config_instance: "ConfigBase") -> None:
        """注册配置实例"""
        cls._configs[config_key] = config_instance

    @classmethod
    def get_config(cls, config_key: str) -> Optional["ConfigBase"]:
        """获取配置实例"""
        return cls._configs.get(config_key)

    @classmethod
    def get_all_config_keys(cls) -> list[str]:
        """获取所有配置键"""
        return list(cls._configs.keys())

    @classmethod
    def unregister_config(cls, config_key: str) -> None:
        """注销配置实例"""
        cls._configs.pop(config_key, None)


T_ConfigBase = TypeVar("T_ConfigBase", bound="ConfigBase")


class ConfigBase(BaseModel):
    # 类变量用于存储配置元数据
    _config_key: ClassVar[Optional[str]] = None
    _config_file_path_class: ClassVar[Optional[Path]] = None

    # 实例变量，用于动态配置
    _config_file_path: Optional[Path] = PrivateAttr(default=None)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 自动生成配置键（如果没有手动设置）
        if cls._config_key is None:
            cls._config_key = cls._generate_config_key()

    @classmethod
    def _generate_config_key(cls) -> str:
        """生成默认的配置键"""
        # 从类名生成配置键，例如 PluginConfig -> plugin, ModelConfigGroup -> model_groups
        class_name = cls.__name__
        if class_name.endswith("Config"):
            base_name = class_name[:-6]  # 移除 "Config" 后缀
        elif class_name.endswith("Group"):
            base_name = class_name
        else:
            base_name = class_name

        # 转换为snake_case
        return re.sub(r"(?<!^)(?=[A-Z])", "_", base_name).lower()

    @classmethod
    def set_config_key(cls, config_key: str) -> None:
        """设置配置键"""
        cls._config_key = config_key

    @classmethod
    def get_config_key(cls) -> str:
        """获取配置键"""
        return cls._config_key or cls._generate_config_key()

    @classmethod
    def set_config_file_path(cls, file_path: Path) -> None:
        """设置配置文件路径"""
        cls._config_file_path_class = file_path

    def get_config_file_path(self) -> Optional[Path]:
        """获取配置文件路径"""
        return self._config_file_path or self.__class__._config_file_path_class  # noqa: SLF001

    def set_instance_config_file_path(self, file_path: Path) -> None:
        """设置实例的配置文件路径"""
        self._config_file_path = file_path

    @classmethod
    def load_config(cls: Type[T_ConfigBase], file_path: Optional[Path] = None, auto_register: bool = True) -> T_ConfigBase:
        """加载配置文件"""
        # 使用传入的路径或类默认路径
        target_path = file_path or cls._config_file_path_class
        if not target_path:
            raise ValueError(f"配置文件路径未设置，请调用 {cls.__name__}.set_config_file_path() 或提供 file_path 参数")

        instance = cls.load_from_path(target_path)

        # 自动注册到配置管理器
        if auto_register:
            ConfigManager.register_config(cls.get_config_key(), instance)

        instance.load_config_to_env()
        return instance

    @classmethod
    def load_from_path(cls: Type[T_ConfigBase], path: Path) -> T_ConfigBase:
        """从指定路径加载配置实例"""
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            instance = cls()
        else:
            content: str = path.read_text(encoding="utf-8")
            if path.suffix == ".json":
                instance = cls.model_validate_json(content)
            elif path.suffix in [".yaml", ".yml"]:
                instance = cls.model_validate(yaml.safe_load(content))
            else:
                raise ValueError(f"Unsupported file type: {path}")

        instance.set_instance_config_file_path(path)  # 存储路径
        return instance

    def load_config_to_env(self):
        """将标记了环境变量相关配置的配置项加载到对应环境中"""
        for field_name, value in self:
            field_info = self.model_fields[field_name]
            # 获取字段的元数据
            schema_extra = getattr(field_info, "json_schema_extra", None)
            if not schema_extra or not isinstance(schema_extra, dict):
                continue

            # 只处理有环境变量标记的字段
            load_to_sysenv = schema_extra.get("load_to_sysenv", False)
            load_to_nonebot_env = schema_extra.get("load_to_nonebot_env", False)

            # 如果没有任何环境变量标记，跳过
            if not (load_to_sysenv or load_to_nonebot_env):
                continue

            # 1. 处理系统环境变量
            if load_to_sysenv:
                # 获取环境变量名
                env_name = schema_extra.get("load_sysenv_as", field_name)
                # 序列化为 JSON 字符串
                os.environ[env_name] = json.dumps(
                    value,
                    default=jsonable_encoder,
                    ensure_ascii=False,
                )

            # 2. 处理 nonebot 环境变量
            if load_to_nonebot_env:
                try:
                    driver = nonebot.get_driver()

                    # 获取 nonebot 环境变量名
                    nb_env_name = schema_extra.get("load_nbenv_as", field_name)

                    final_value = value
                    # 尝试将字符串值解析为 JSON 对象
                    if isinstance(value, str):
                        try:
                            json_value = json.loads(value)
                            final_value = json_value  # 如果解析成功，使用解析后的值
                        except json.JSONDecodeError:
                            # 解析失败，保持原始字符串值
                            pass

                    # 设置 nonebot 环境变量
                    setattr(driver.config, nb_env_name, final_value)
                except ImportError:
                    pass  # nonebot 未安装，跳过
                except Exception as e:
                    print(f"ERROR: 加载配置到 nonebot 环境变量失败: {e}", file=sys.stderr)

    def dump_config(self, file_path: Optional[Path] = None) -> None:
        """保存配置文件"""
        # 使用传入的路径或类默认路径
        target_path = file_path or self.get_config_file_path()
        if not target_path:
            raise ValueError(
                f"配置文件路径未设置，请调用 {self.__class__.__name__}.set_config_file_path() 或提供 file_path 参数",
            )

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.suffix == ".json":
            target_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        elif target_path.suffix in [".yaml", ".yml"]:
            yaml_str = yaml.dump(
                data=self.model_dump(),
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            target_path.write_text(yaml_str, encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file type: {target_path}")

    @classmethod
    def get_field_title(cls, field_name: str) -> str:
        """获取字段的中文标题"""
        field = cls.model_fields.get(field_name)
        if field and field.title:
            return field.title
        return ""  # Return empty string if field or title is not found

    @classmethod
    def get_field_placeholder(cls, field_name: str) -> str:
        """获取字段的占位符文本"""
        field = cls.model_fields.get(field_name)
        if field and hasattr(field, "json_schema_extra") and isinstance(field.json_schema_extra, dict):
            placeholder = field.json_schema_extra.get("placeholder")
            return str(placeholder) if placeholder is not None else ""
        return ""


def gen_mysql_conn_str(
    host: str,
    port: int,
    user: str,
    password: str,
    db: str,
    proxy_host: Optional[str] = None,
    proxy_port: Optional[int] = None,
) -> str:
    """生成 MySQL 连接字符串，支持代理

    Args:
        host (str): 主机名或 IP 地址
        port (int): 端口号
        user (str): 用户名
        password (str): 密码
        db (str): 数据库名
        proxy_host (str): 代理服务器地址
        proxy_port (int): 代理服务器端口号

    Returns:
        str: 连接字符串
    """
    user = quote_plus(user)
    password = quote_plus(password)
    db = quote_plus(db)

    conn_str = f"mysql://{user}:{password}@{host}:{port}/{db}"

    if proxy_host and proxy_port:
        conn_str += f"?proxyhost={quote_plus(proxy_host)}&proxyport={proxy_port}"

    return conn_str


def gen_postgres_conn_str(
    host: str,
    port: int,
    user: str,
    password: str,
    db: str,
    sslrootcert: Optional[str] = None,
    sslcert: Optional[str] = None,
    sslkey: Optional[str] = None,
) -> str:
    """生成 PostgreSQL 连接字符串

    Args:
        host (str): 主机名或 IP 地址
        port (int): 端口号
        user (str): 用户名
        password (str): 密码
        db (str): 数据库名
        sslmode (str, optional): SSL 连接模式. Defaults to "require".
        sslrootcert (Optional[str], optional): 根证书路径. Defaults to None.
        sslcert (Optional[str], optional): 客户端证书路径. Defaults to None.
        sslkey (Optional[str], optional): 客户端密钥路径. Defaults to None.

    Returns:
        str: 连接字符串
    """
    user = quote_plus(user)
    password = quote_plus(password)
    db = quote_plus(db)

    conn_str = f"postgres://{user}:{password}@{host}:{port}/{db}?"

    if sslrootcert:
        conn_str += f"&sslrootcert={quote_plus(sslrootcert)}"
    if sslcert:
        conn_str += f"&sslcert={quote_plus(sslcert)}"
    if sslkey:
        conn_str += f"&sslkey={quote_plus(sslkey)}"

    return conn_str


def gen_sqlite_db_url(db_path: str) -> str:
    """生成 SQLite 数据库连接 URL"""

    if not db_path.startswith("/") and not db_path.startswith("./"):
        db_path = f"./{db_path}"

    return f"sqlite:///{db_path}"
