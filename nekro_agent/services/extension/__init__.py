"""扩展服务模块

提供扩展的加载、管理、代码生成等功能。
"""

from .generator import (
    apply_extension_code,
    generate_extension_code,
    generate_extension_code_stream,
    generate_extension_template,
)
from .loader import init_extensions, reload_ext_workdir
from .manager import (
    delete_ext_file,
    get_all_ext_meta_data,
    get_ext_workdir_files,
    read_ext_file,
    save_ext_file,
)
from .models import ExtMetaData

__all__ = [
    "ExtMetaData",
    "apply_extension_code",
    "delete_ext_file",
    "generate_extension_code",
    "generate_extension_code_stream",
    "generate_extension_template",
    "get_all_ext_meta_data",
    "get_ext_workdir_files",
    "init_extensions",
    "read_ext_file",
    "reload_ext_workdir",
    "save_ext_file",
]
