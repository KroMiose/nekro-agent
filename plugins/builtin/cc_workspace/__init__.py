"""
# CC 工作区协作插件 (cc_workspace)

将 CC Sandbox（claude-code）工作区能力接入 NekroAgent 主 Agent，
实现任务委托、文件双向传递与实时状态查询。

## 功能一览

- **Prompt 注入**：自动在系统提示词中注入当前频道绑定的 CC Workspace 状态与可用工具列表
- **create_and_bind_workspace / start_cc_sandbox**：为当前频道创建并启动 CC 工作区
- **delegate_to_cc**（BEHAVIOR）：将复杂任务委托给 CC Sandbox 异步执行，完成后自动回传结果
- **cancel_cc_task / force_cancel_cc_workspace**：取消本频道任务或强制抢占当前工作区任务
- **get_cc_context**（AGENT）：查询当前频道的 CC 协作上下文
- **cc_help / cc_status / cc_context / cc_recent**：供用户直接查看帮助、工作区状态、上下文与近期协作记录
- **upload_file_to_cc**（TOOL）：将主沙盒文件复制到 CC Workspace `data/` 目录
- **download_file_from_cc**（TOOL）：将 CC Workspace `data/` 目录中的文件引入主沙盒共享目录

## 使用前提

需在「工作区管理」页面创建 CC Workspace 并将目标频道绑定到对应工作区，且工作区状态为 `active`。
"""

from . import main
from .plugin import plugin

__all__ = ["plugin", "main"]
