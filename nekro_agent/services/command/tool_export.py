"""Agent Tool-Use Schema 导出器

将命令注册表导出为 Agent Tool-Use 格式 (OpenAI Function Calling)，
并提供 AI 调用命令时的响应合并逻辑。
"""

from typing import Any, Optional

from nekro_agent.services.command.schemas import CommandResponse, CommandResponseStatus


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

    @staticmethod
    def merge_responses(responses: list[CommandResponse]) -> dict[str, Any]:
        """将命令流式输出合并为 AI 友好的单一响应

        合并规则:
        - PROCESSING 消息拼接为 process_log
        - 最终 SUCCESS/ERROR 的 message 和 data 保留
        - WAITING 状态转为特殊提示（AI 场景不支持交互等待）
        - 其他终态 (NOT_FOUND/DISABLED/UNAUTHORIZED/INVALID_ARGS) 直接返回

        返回格式:
        {
            "status": "success",
            "process_log": "正在扫描...\\n已抓取 3 个页面...\\n",
            "message": "分析完成！",
            "data": {"url": "...", "pages_scanned": 3}
        }
        """
        if not responses:
            return {"status": "error", "message": "命令无响应"}

        process_lines: list[str] = []
        final_status = "error"
        final_message = ""
        final_data: Optional[dict[str, Any]] = None

        for resp in responses:
            if resp.status == CommandResponseStatus.PROCESSING:
                process_lines.append(resp.message)
            elif resp.status == CommandResponseStatus.WAITING:
                # AI 场景不支持交互等待，将 wait 提示作为消息返回
                final_status = "waiting"
                final_message = resp.message
                if resp.wait_options:
                    final_message += f"\n可选: {' / '.join(resp.wait_options)}"
            elif resp.status in (
                CommandResponseStatus.SUCCESS,
                CommandResponseStatus.ERROR,
                CommandResponseStatus.NOT_FOUND,
                CommandResponseStatus.DISABLED,
                CommandResponseStatus.UNAUTHORIZED,
                CommandResponseStatus.INVALID_ARGS,
            ):
                final_status = resp.status.value
                final_message = resp.message
                final_data = resp.data

        result: dict[str, Any] = {"status": final_status}
        if process_lines:
            result["process_log"] = "\n".join(process_lines)
        result["message"] = final_message
        if final_data is not None:
            result["data"] = final_data

        return result

    async def execute_tool(
        self,
        command_name: str,
        chat_key: str,
        raw_args: str = "",
        user_id: str = "agent",
        username: str = "AI Agent",
    ) -> dict[str, Any]:
        """AI 调用命令并获取合并响应

        Args:
            command_name: 命令名（支持短名和完整名）
            chat_key: 频道标识
            raw_args: 原始参数字符串
            user_id: 调用者 ID
            username: 调用者名称

        Returns:
            合并后的响应字典
        """
        from nekro_agent.services.command.registry import command_registry
        from nekro_agent.services.command.schemas import CommandExecutionContext, CommandRequest

        context = CommandExecutionContext(
            user_id=user_id,
            chat_key=chat_key,
            username=username,
            adapter_key="agent",
            is_super_user=True,  # AI 调用默认拥有最高权限
        )
        request = CommandRequest(context=context, command_name=command_name, raw_args=raw_args)

        responses: list[CommandResponse] = []
        async for resp in command_registry.execute(request):
            responses.append(resp)

        return self.merge_responses(responses)


agent_tool_exporter = AgentToolExporter()
