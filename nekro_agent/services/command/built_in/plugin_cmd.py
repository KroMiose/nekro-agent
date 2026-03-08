"""内置命令 - 插件类: na_plugins, plugin_info, reset_plugin"""

from typing import Annotated, Any

from nekro_agent.schemas.i18n import i18n_text
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.i18n_helper import t
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class NaPluginsCommand(BaseCommand):
    """列出所有已加载插件"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_plugins",
            aliases=["na-plugins", "nps"],
            description="列出所有已加载插件",
            i18n_description=i18n_text(zh_CN="列出所有已加载插件", en_US="List all loaded plugins"),
            permission=CommandPermission.SUPER_USER,
            category="插件",
            i18n_category=i18n_text(zh_CN="插件", en_US="Plugin"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.services.plugin.collector import plugin_collector

        plugins = plugin_collector.get_all_plugins()

        if not plugins:
            return CmdCtl.success(t(context.lang, zh_CN="当前没有已加载的插件", en_US="No plugins loaded"))

        plugin_info_parts = []
        for plugin in plugins:
            plugin_status = t(context.lang, zh_CN="已启用", en_US="Enabled") if plugin.is_enabled else t(context.lang, zh_CN="已禁用", en_US="Disabled")
            sandbox_methods_count = len(plugin.sandbox_methods)
            has_prompt_inject = t(context.lang, zh_CN="是", en_US="Yes") if plugin.prompt_inject_method else t(context.lang, zh_CN="否", en_US="No")
            webhook_methods_count = len(plugin.webhook_methods)

            author_label = t(context.lang, zh_CN="作者", en_US="Author")
            desc_label = t(context.lang, zh_CN="说明", en_US="Description")
            link_label = t(context.lang, zh_CN="链接", en_US="Link")
            func_label = t(context.lang, zh_CN="功能", en_US="Features")
            sandbox_label = t(context.lang, zh_CN="沙盒方法", en_US="Sandbox methods")
            prompt_label = t(context.lang, zh_CN="提示注入", en_US="Prompt inject")

            info = (
                f"* {plugin.name} - v{plugin.version} ({plugin_status})\n"
                f"{author_label}: {plugin.author}\n"
                f"{desc_label}: {plugin.description}\n"
                f"{link_label}: {plugin.url}\n"
                f"{func_label}: {sandbox_label}({sandbox_methods_count}), {prompt_label}({has_prompt_inject}), Webhook({webhook_methods_count})"
            )
            plugin_info_parts.append(info)

        all_plugin_info = "\n\n".join(plugin_info_parts)
        stats = t(context.lang, zh_CN=f"共加载 {len(plugins)} 个插件", en_US=f"Total {len(plugins)} plugins loaded")
        title = t(context.lang, zh_CN="当前已加载的插件:", en_US="Currently loaded plugins:")

        return CmdCtl.success(f"{title} \n{all_plugin_info}\n\n{stats}")


class PluginInfoCommand(BaseCommand):
    """查询单个插件详情"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="plugin_info",
            aliases=["plugin-info", "npi"],
            description="查询插件详情",
            i18n_description=i18n_text(zh_CN="查询插件详情", en_US="Query plugin details"),
            usage="plugin_info <plugin_name/key>",
            permission=CommandPermission.SUPER_USER,
            category="插件",
            i18n_category=i18n_text(zh_CN="插件", en_US="Plugin"),
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
            return CmdCtl.failed(
                t(
                    context.lang,
                    zh_CN="请指定要查询的插件名或插件键名 (plugin_info <plugin_name/key>)",
                    en_US="Please specify plugin name or key (plugin_info <plugin_name/key>)",
                )
            )

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
                    key_label = t(context.lang, zh_CN="键名", en_US="key")
                    suggestions.append(f"- {plugin.name} ({key_label}: {plugin.key})")

            suggestion_text = ""
            if suggestions:
                maybe_label = t(context.lang, zh_CN="您可能想查找的插件:", en_US="Plugins you might be looking for:")
                suggestion_text = f"\n\n{maybe_label}\n" + "\n".join(suggestions[:3])
                if len(suggestions) > 3:
                    more = t(context.lang, zh_CN=f"...等共 {len(suggestions)} 个可能的匹配", en_US=f"...and {len(suggestions)} more possible matches")
                    suggestion_text += f"\n{more}"

            not_found = t(context.lang, zh_CN=f"未找到插件: {search_term}", en_US=f"Plugin not found: {search_term}")
            tip = t(context.lang, zh_CN="提示: 使用 `na_plugins` 命令查看所有已加载的插件", en_US="Tip: use `na_plugins` to view all loaded plugins")
            return CmdCtl.failed(f"{not_found}\n{tip}{suggestion_text}")

        enabled_str = t(context.lang, zh_CN="已启用", en_US="Enabled") if target_plugin.is_enabled else t(context.lang, zh_CN="已禁用", en_US="Disabled")
        detail_label = t(context.lang, zh_CN="插件详情", en_US="Plugin Details")
        version_label = t(context.lang, zh_CN="版本", en_US="Version")
        key_label = t(context.lang, zh_CN="键名", en_US="Key")
        author_label = t(context.lang, zh_CN="作者", en_US="Author")
        desc_label = t(context.lang, zh_CN="说明", en_US="Description")
        link_label = t(context.lang, zh_CN="链接", en_US="Link")
        stats_title = t(context.lang, zh_CN="===== 功能统计 =====", en_US="===== Feature Stats =====")
        sandbox_label = t(context.lang, zh_CN="沙盒方法", en_US="Sandbox methods")
        prompt_label = t(context.lang, zh_CN="提示注入", en_US="Prompt inject")
        has_label = t(context.lang, zh_CN="有", en_US="Yes")
        no_label = t(context.lang, zh_CN="无", en_US="No")

        info = [
            f"[{target_plugin.name}] {detail_label}",
            f"{version_label}: v{target_plugin.version} ({enabled_str})",
            f"{key_label}: {target_plugin.key}",
            f"{author_label}: {target_plugin.author}",
            f"{desc_label}: {target_plugin.description}",
            f"{link_label}: {target_plugin.url}",
            "",
            stats_title,
            f"{sandbox_label}: {len(target_plugin.sandbox_methods)}",
            f"{prompt_label}: {has_label if target_plugin.prompt_inject_method else no_label}",
            f"Webhook: {len(target_plugin.webhook_methods)}",
        ]

        try:
            plugin_config = target_plugin.get_config()
            config_items = plugin_config.model_dump()
            if config_items:
                info.append("")
                config_title = t(context.lang, zh_CN="===== 配置信息 =====", en_US="===== Configuration =====")
                info.append(config_title)
                for key, value in config_items.items():
                    info.append(f"{key}: {value}")
        except Exception as e:
            info.append("")
            config_fail = t(context.lang, zh_CN=f"获取配置失败: {e}", en_US=f"Failed to get config: {e}")
            info.append(config_fail)

        if target_plugin.sandbox_methods:
            info.append("")
            methods_title = t(context.lang, zh_CN="===== 方法列表 =====", en_US="===== Method List =====")
            info.append(methods_title)
            for method in target_plugin.sandbox_methods:
                method_type_str = {
                    SandboxMethodType.AGENT: t(context.lang, zh_CN="代理方法", en_US="Agent"),
                    SandboxMethodType.MULTIMODAL_AGENT: t(context.lang, zh_CN="多模态代理", en_US="Multimodal Agent"),
                    SandboxMethodType.TOOL: t(context.lang, zh_CN="工具方法", en_US="Tool"),
                    SandboxMethodType.BEHAVIOR: t(context.lang, zh_CN="行为方法", en_US="Behavior"),
                }.get(method.method_type, t(context.lang, zh_CN="未知类型", en_US="Unknown"))
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
            i18n_description=i18n_text(zh_CN="重置插件配置", en_US="Reset plugin configuration"),
            usage="reset_plugin <plugin_name/key>",
            permission=CommandPermission.SUPER_USER,
            category="插件",
            i18n_category=i18n_text(zh_CN="插件", en_US="Plugin"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        search_term: Annotated[str, Arg("插件名或插件键名", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.services.plugin.collector import plugin_collector

        if not search_term:
            return CmdCtl.failed(
                t(
                    context.lang,
                    zh_CN="请指定要重置的插件名或插件键名 (reset_plugin <plugin_name/key>)",
                    en_US="Please specify plugin name or key (reset_plugin <plugin_name/key>)",
                )
            )

        plugins = plugin_collector.get_all_plugins()
        target_plugin = _find_plugin(plugins, search_term)

        if not target_plugin:
            return CmdCtl.failed(
                t(context.lang, zh_CN=f"未找到插件: {search_term}", en_US=f"Plugin not found: {search_term}")
            )

        config_path = target_plugin._plugin_config_path  # noqa: SLF001
        if config_path.exists():
            config_path.unlink()
            return CmdCtl.success(
                t(
                    context.lang,
                    zh_CN=f"插件 {target_plugin.name} 配置文件已删除",
                    en_US=f"Plugin {target_plugin.name} config file deleted",
                )
            )
        else:
            return CmdCtl.success(
                t(
                    context.lang,
                    zh_CN=f"插件 {target_plugin.name} 配置文件不存在",
                    en_US=f"Plugin {target_plugin.name} config file does not exist",
                )
            )


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
