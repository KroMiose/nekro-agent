"""命令组 - 支持子命令结构（如 config.set, config.show）"""

from typing import Any, Callable, Optional


class CommandGroup:
    """命令组 - 将多个子命令组织在一个前缀下

    子命令在注册表中展平为 `group.sub` 的形式，
    带命名空间则为 `namespace:group.sub`。

    Example:
        ```python
        config_group = plugin.mount_command_group(
            name="config",
            description="配置管理",
            permission=CommandPermission.ADVANCED,
        )

        @config_group.command(name="set", description="设置配置项")
        async def config_set(context, key, value):
            return CmdCtl.success(f"已设置 {key} = {value}")
        ```

        调用: `/config.set key:"model" value:"gpt-4"`
    """

    def __init__(
        self,
        group_name: str,
        description: str,
        commands_list: list,
        source: str,
        namespace: str,
        permission: Any = None,
        category: str = "plugin",
        tags: Optional[list[str]] = None,
    ):
        self._group_name = group_name
        self._description = description
        self._commands_list = commands_list  # reference to plugin._commands
        self._source = source
        self._namespace = namespace
        self._default_permission = permission
        self._default_category = category
        self._default_tags = tags or []

    def command(
        self,
        name: str,
        description: str,
        aliases: Optional[list[str]] = None,
        permission: Any = None,
        usage: str = "",
        category: str = "",
        tags: Optional[list[str]] = None,
        internal: bool = False,
    ) -> Callable[[Callable], Callable]:
        """注册子命令

        Args:
            name: 子命令名（将生成 `group.name` 的完整名）
            description: 子命令描述
            aliases: 别名列表（将自动添加 group 前缀）
            permission: 权限级别（默认继承组级别）
            usage: 使用说明
            category: 分类（默认继承组级别）
            tags: 标签
            internal: 是否为内部命令
        """

        def decorator(func: Callable) -> Callable:
            from nekro_agent.services.command.base import CommandPermission, PluginCommand

            full_name = f"{self._group_name}.{name}"
            full_aliases = [f"{self._group_name}.{a}" for a in (aliases or [])]

            perm = permission or self._default_permission or CommandPermission.PUBLIC
            if isinstance(perm, str):
                perm = CommandPermission(perm)

            cmd = PluginCommand(
                name=full_name,
                description=description,
                aliases=full_aliases,
                permission=perm,
                usage=usage or f"{full_name}",
                category=category or self._default_category,
                source=self._source,
                namespace=self._namespace,
                tags=tags or self._default_tags,
                internal=internal,
                execute_func=func,
            )
            self._commands_list.append(cmd)
            return func

        return decorator
