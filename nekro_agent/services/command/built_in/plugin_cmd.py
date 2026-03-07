"""内置命令 - 插件类: na_plugins, plugin_info, reset_plugin"""

from typing import Annotated, Any

from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class NaPluginsCommand(BaseCommand):
    """列出所有已加载插件"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_plugins",
            aliases=["na-plugins", "nps"],
            description="列出所有已加载插件",
            permission=CommandPermission.SUPER_USER,
            category="插件",
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.services.plugin.collector import plugin_collector

        plugins = plugin_collector.get_all_plugins()

        if not plugins:
            return CmdCtl.success("当前没有已加载的插件")

        plugin_info_parts = []
        for plugin in plugins:
            plugin_status = "已启用" if plugin.is_enabled else "已禁用"
            sandbox_methods_count = len(plugin.sandbox_methods)
            has_prompt_inject = "是" if plugin.prompt_inject_method else "否"
            webhook_methods_count = len(plugin.webhook_methods)

            info = (
                f"* {plugin.name} - v{plugin.version} ({plugin_status})\n"
                f"作者: {plugin.author}\n"
                f"说明: {plugin.description}\n"
                f"链接: {plugin.url}\n"
                f"功能: 沙盒方法({sandbox_methods_count}), 提示注入({has_prompt_inject}), Webhook({webhook_methods_count})"
            )
            plugin_info_parts.append(info)

        all_plugin_info = "\n\n".join(plugin_info_parts)
        stats = f"共加载 {len(plugins)} 个插件"

        return CmdCtl.success(f"当前已加载的插件: \n{all_plugin_info}\n\n{stats}")


class PluginInfoCommand(BaseCommand):
    """查询单个插件详情"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="plugin_info",
            aliases=["plugin-info", "npi"],
            description="查询插件详情",
            usage="plugin_info <plugin_name/key>",
            permission=CommandPermission.SUPER_USER,
            category="插件",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        search_term: Annotated[str, Arg("插件名或插件键名", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.services.plugin.collector import plugin_collector
        from nekro_agent.services.plugin.schema import SandboxMethodType

        if not search_term:
            return CmdCtl.failed("请指定要查询的插件名或插件键名 (plugin_info <plugin_name/key>)")

        plugins = plugin_collector.get_all_plugins()
        target_plugin = _find_plugin(plugins, search_term)

        if not target_plugin:
            suggestions = []
            for plugin in plugins:
                if any(
                    c.lower() in plugin.key.lower() or c.lower() in plugin.name.lower()
                    for c in search_term.lower()
                    if c.isalnum()
                ):
                    suggestions.append(f"- {plugin.name} (键名: {plugin.key})")

            suggestion_text = ""
            if suggestions:
                suggestion_text = "\n\n您可能想查找的插件:\n" + "\n".join(suggestions[:3])
                if len(suggestions) > 3:
                    suggestion_text += f"\n...等共 {len(suggestions)} 个可能的匹配"

            return CmdCtl.failed(
                f"未找到插件: {search_term}\n提示: 使用 `na_plugins` 命令查看所有已加载的插件{suggestion_text}"
            )

        info = [
            f"[{target_plugin.name}] 插件详情",
            f"版本: v{target_plugin.version} ({'已启用' if target_plugin.is_enabled else '已禁用'})",
            f"键名: {target_plugin.key}",
            f"作者: {target_plugin.author}",
            f"说明: {target_plugin.description}",
            f"链接: {target_plugin.url}",
            "",
            "===== 功能统计 =====",
            f"沙盒方法: {len(target_plugin.sandbox_methods)}",
            f"提示注入: {'有' if target_plugin.prompt_inject_method else '无'}",
            f"Webhook: {len(target_plugin.webhook_methods)}",
        ]

        try:
            plugin_config = target_plugin.get_config()
            config_items = plugin_config.model_dump()
            if config_items:
                info.append("")
                info.append("===== 配置信息 =====")
                for key, value in config_items.items():
                    info.append(f"{key}: {value}")
        except Exception as e:
            info.append("")
            info.append(f"获取配置失败: {e}")

        if target_plugin.sandbox_methods:
            info.append("")
            info.append("===== 方法列表 =====")
            for method in target_plugin.sandbox_methods:
                method_type_str = {
                    SandboxMethodType.AGENT: "代理方法",
                    SandboxMethodType.MULTIMODAL_AGENT: "多模态代理",
                    SandboxMethodType.TOOL: "工具方法",
                    SandboxMethodType.BEHAVIOR: "行为方法",
                }.get(method.method_type, "未知类型")
                info.append(f"- {method.func.__name__} ({method_type_str}): {method.name}")

        return CmdCtl.success("\n".join(info))


class ResetPluginCommand(BaseCommand):
    """重置插件配置"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="reset_plugin",
            aliases=["reset-plugin"],
            description="重置插件配置",
            usage="reset_plugin <plugin_name/key>",
            permission=CommandPermission.SUPER_USER,
            category="插件",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        search_term: Annotated[str, Arg("插件名或插件键名", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.services.plugin.collector import plugin_collector

        if not search_term:
            return CmdCtl.failed("请指定要重置的插件名或插件键名 (reset_plugin <plugin_name/key>)")

        plugins = plugin_collector.get_all_plugins()
        target_plugin = _find_plugin(plugins, search_term)

        if not target_plugin:
            return CmdCtl.failed(f"未找到插件: {search_term}")

        config_path = target_plugin._plugin_config_path  # noqa: SLF001
        if config_path.exists():
            config_path.unlink()
            return CmdCtl.success(f"插件 {target_plugin.name} 配置文件已删除")
        else:
            return CmdCtl.success(f"插件 {target_plugin.name} 配置文件不存在")


def _find_plugin(plugins: list[Any], search_term: str) -> Any:
    """按优先级查找插件

    查找优先级：键名精确 > 键名精确(忽略大小写) > 插件名精确 > 插件名精确(忽略大小写) > 键名部分匹配 > 插件名部分匹配
    """
    for plugin in plugins:
        if plugin.key == search_term:
            return plugin
    for plugin in plugins:
        if plugin.key.lower() == search_term.lower():
            return plugin
    for plugin in plugins:
        if plugin.name == search_term:
            return plugin
    for plugin in plugins:
        if plugin.name.lower() == search_term.lower():
            return plugin
    for plugin in plugins:
        if search_term.lower() in plugin.key.lower():
            return plugin
    for plugin in plugins:
        if search_term.lower() in plugin.name.lower():
            return plugin
    return None
