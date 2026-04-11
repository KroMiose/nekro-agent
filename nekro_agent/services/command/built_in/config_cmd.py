"""内置命令 - 配置类: conf_show, conf_set, conf_reload, conf_save"""

from typing import Annotated

from nekro_agent.schemas.i18n import i18n_text, t
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class ConfShowCommand(BaseCommand):
    """查看配置"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="conf_show",
            aliases=[],
            description="查看配置项",
            i18n_description=i18n_text(zh_CN="查看配置项", en_US="Show configuration"),
            usage="conf_show [key]",
            permission=CommandPermission.ADVANCED,
            category="配置",
            i18n_category=i18n_text(zh_CN="配置", en_US="Configuration"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        key: Annotated[str, Arg("配置键名（留空列出所有可修改项）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.core.config import config

        if not key:
            modifiable_keys: list[str] = []
            for _key, _value in config.model_dump().items():
                if isinstance(_value, (int, float, bool, str)):
                    modifiable_keys.append(_key)
            lines = [f"- {k} ({type(getattr(config, k)).__name__})" for k in modifiable_keys]
            return CmdCtl.success(
                t(zh_CN="当前支持动态修改配置：\n", en_US="Dynamically modifiable configurations:\n")
                + "\n".join(lines)
            )
        else:
            dump = config.model_dump()
            if key in dump:
                return CmdCtl.success(
                    t(zh_CN=f"当前配置：\n{key}={getattr(config, key)}", en_US=f"Current config:\n{key}={getattr(config, key)}")
                )
            else:
                return CmdCtl.failed(
                    t(zh_CN=f"未知配置 `{key}`", en_US=f"Unknown config `{key}`")
                )


class ConfSetCommand(BaseCommand):
    """设置配置"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="conf_set",
            aliases=[],
            description="设置配置项",
            i18n_description=i18n_text(zh_CN="设置配置项", en_US="Set configuration"),
            usage="conf_set key=value",
            permission=CommandPermission.ADVANCED,
            category="配置",
            i18n_category=i18n_text(zh_CN="配置", en_US="Configuration"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        expr: Annotated[str, Arg("配置表达式 (key=value)", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.core.config import config

        if not expr or "=" not in expr:
            return CmdCtl.failed(
                t(
                    zh_CN="参数错误，请使用 `conf_set key=value` 的格式",
                    en_US="Invalid argument, use `conf_set key=value` format",
                )
            )

        key, value = expr.strip().split("=", 1)
        if not key or not value:
            return CmdCtl.failed(
                t(
                    zh_CN="参数错误，请使用 `conf_set key=value` 的格式",
                    en_US="Invalid argument, use `conf_set key=value` format",
                )
            )

        dump = config.model_dump()
        if key not in dump:
            return CmdCtl.failed(t(zh_CN=f"未知配置: `{key}`", en_US=f"Unknown config: `{key}`"))

        current_value = getattr(config, key)
        if isinstance(current_value, (int, float)):
            setattr(config, key, type(current_value)(value))
        elif isinstance(current_value, bool):
            if value.lower() in ("true", "1", "yes"):
                setattr(config, key, True)
            elif value.lower() in ("false", "0", "no"):
                setattr(config, key, False)
            else:
                return CmdCtl.failed(
                    t(
                        zh_CN=f"布尔值只能是 `true` 或 `false`，请检查 `{key}` 的值",
                        en_US=f"Boolean value must be `true` or `false`, check the value of `{key}`",
                    )
                )
        elif isinstance(current_value, str):
            setattr(config, key, value)
        else:
            return CmdCtl.failed(
                t(
                    zh_CN=f"不支持动态修改的配置类型 `{type(current_value)}`",
                    en_US=f"Unsupported config type for dynamic modification: `{type(current_value)}`",
                )
            )

        return CmdCtl.success(
            t(zh_CN=f"已设置 `{key}` 的值为 `{value}`", en_US=f"Set `{key}` to `{value}`")
        )


class ConfReloadCommand(BaseCommand):
    """重载配置"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="conf_reload",
            aliases=[],
            description="重载配置文件",
            i18n_description=i18n_text(zh_CN="重载配置文件", en_US="Reload configuration file"),
            permission=CommandPermission.ADVANCED,
            category="配置",
            i18n_category=i18n_text(zh_CN="配置", en_US="Configuration"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.core.config import reload_config

        try:
            reload_config()
        except Exception as e:
            return CmdCtl.failed(
                t(zh_CN=f"重载配置失败：{e}", en_US=f"Failed to reload configuration: {e}")
            )
        return CmdCtl.success(
            t(zh_CN="重载配置成功", en_US="Configuration reloaded successfully")
        )


class ConfSaveCommand(BaseCommand):
    """保存配置"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="conf_save",
            aliases=[],
            description="保存当前配置到文件",
            i18n_description=i18n_text(zh_CN="保存当前配置到文件", en_US="Save configuration to file"),
            permission=CommandPermission.ADVANCED,
            category="配置",
            i18n_category=i18n_text(zh_CN="配置", en_US="Configuration"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.core.config import save_config

        try:
            save_config()
        except Exception as e:
            return CmdCtl.failed(
                t(zh_CN=f"保存配置失败：{e}", en_US=f"Failed to save configuration: {e}")
            )
        return CmdCtl.success(
            t(zh_CN="保存配置成功", en_US="Configuration saved successfully")
        )
