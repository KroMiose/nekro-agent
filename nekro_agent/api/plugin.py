"""插件 API

用于管理 Nekro 插件的 API 接口。
"""

from nekro_agent.core.core_utils import ExtraField
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, PluginStore
from nekro_agent.services.plugin.packages import dynamic_import_pkg
from nekro_agent.services.plugin.schema import SandboxMethod, SandboxMethodType
from nekro_agent.services.plugin.task import (
    AsyncTaskHandle,
    TaskCtl,
    TaskRunner,
    TaskSignal,
    task,
)

__all__ = [
    "AsyncTaskHandle",
    "ConfigBase",
    "ExtraField",
    "NekroPlugin",
    "PluginStore",
    "SandboxMethod",
    "SandboxMethodType",
    "TaskCtl",
    "TaskRunner",
    "TaskSignal",
    "dynamic_import_pkg",
    "task",
]
