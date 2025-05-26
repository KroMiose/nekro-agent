import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional, Union
from urllib.parse import quote_plus

import nonebot
import yaml
from pydantic import BaseModel, Field


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
    is_secret: bool = Field(default=False, title="敏感信息保护", description="设置为True时，输入内容将以密码形式('••••')显示，用于保护API密钥等敏感数据")
    placeholder: str = Field(default="", title="输入提示文本", description="当字段未填写时在输入框中显示的提示文本")
    is_textarea: bool = Field(default=False, title="多行文本支持", description="设置为True时，将使用多行文本区域而非单行输入框")
    ref_model_groups: bool = Field(default=False, title="模型组引用标识", description="设置为True时，表示该字段需要从系统中已配置的模型组中选择")
    model_type: str = Field(default="", title="模型类型规范", description="指定引用的模型类型标识符，仅在ref_model_groups为True时生效")
    required: bool = Field(default=False, title="必填字段标识", description="设置为True时，前端将验证该字段必须填写才能提交表单")
    load_to_sysenv: bool = Field(default=False, title="环境变量加载控制", description="设置为True时，该配置项的值将被加载到系统环境变量中")
    load_sysenv_as: str = Field(default="", title="环境变量名称定义", description="指定将配置项加载为环境变量时使用的变量名，仅在load_to_env为True时生效")
    load_to_nonebot_env: bool = Field(default=False, title="nonebot环境变量加载控制", description="设置为True时，该配置项的值将被加载到nonebot的环境变量中")
    load_nbenv_as: str = Field(default="", title="nonebot环境变量名称定义", description="指定将配置项加载到nonebot的环境变量时使用的变量名，仅在load_to_nbenv_as为True时生效")

class ConfigBase(BaseModel):

    @classmethod
    def load_config(cls, file_path: Path):
        """加载配置文件"""
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            return cls()
        content: str = file_path.read_text(encoding="utf-8")
        if file_path.suffix == ".json":
            return cls.model_validate_json(content)
        if file_path.suffix in [".yaml", ".yml"]:
            return cls.model_validate(yaml.safe_load(content))
        raise ValueError(f"Unsupported file type: {file_path}")

    def dump_config(self, file_path: Path) -> None:
        """保存配置文件"""
        if file_path.suffix == ".json":
            file_path.write_text(self.model_dump_json(), encoding="utf-8")
        elif file_path.suffix in [".yaml", ".yml"]:
            yaml_str = yaml.dump(
                data=self.model_dump(),
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            file_path.write_text(yaml_str, encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file type: {file_path}")

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
