"""
# CC 工作区协作插件 (cc_workspace)

将 CC Sandbox（claude-code）工作区能力接入 NekroAgent 主 Agent，
实现任务委托、文件双向传递与实时状态查询。

## 功能一览

- **Prompt 注入**：自动在系统提示词中注入当前频道绑定的 CC Workspace 状态与可用工具列表
- **delegate_to_cc**（AGENT）：将复杂任务委托给 CC Sandbox 执行，CC 完成后主 Agent 继续处理结果
- **get_cc_status**（TOOL）：查询 CC Sandbox 工作区实时状态（容器状态、工具列表、健康检查）
- **upload_file_to_cc**（TOOL）：将主沙盒文件复制到 CC Workspace `data/` 目录
- **download_file_from_cc**（TOOL）：将 CC Workspace `data/` 目录中的文件引入主沙盒共享目录

## 使用前提

需在「工作区管理」页面创建 CC Workspace 并将目标频道绑定到对应工作区，且工作区状态为 `active`。
"""

from . import main
from .plugin import plugin

__all__ = ["plugin", "main"]
