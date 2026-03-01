"""Agent Tool-Use Schema 导出器"""

from typing import Optional


class AgentToolExporter:
    """将命令注册表导出为 Agent Tool-Use 格式"""

    def export_tools(self, chat_key: Optional[str] = None) -> list[dict]:
        """导出已启用命令为 Tool 列表 (OpenAI Function Calling 格式)"""
        from nekro_agent.services.command.manager import command_manager
        from nekro_agent.services.command.registry import command_registry

        tools = []
        for meta in command_registry.list_all_commands():
            if meta.internal:
                continue
            if not command_manager.is_command_enabled(meta.name, chat_key):
                continue
            tools.append({
                "type": "function",
                "function": {
                    "name": meta.name,
                    "description": meta.description,
                    "parameters": meta.params_schema or {"type": "object", "properties": {}},
                },
            })
        return tools


agent_tool_exporter = AgentToolExporter()
