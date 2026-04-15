"""内置命令 - 信息类: na_info, na_help"""

from typing import Any

from nekro_agent.schemas.i18n import i18n_text, t
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import CommandExecutionContext, CommandResponse


def _format_channel_status(status: str) -> str:
    status_labels = {
        "active": t(zh_CN="启用", en_US="Enabled"),
        "disabled": t(zh_CN="停用", en_US="Disabled"),
        "observe": t(zh_CN="旁观", en_US="Observe"),
    }
    return status_labels.get(status, t(zh_CN="未知", en_US="Unknown"))


def _format_agent_runtime_phase(phase: str | None) -> str:
    phase_labels = {
        "llm_generating": t(zh_CN="LLM 生成中", en_US="LLM generating"),
        "llm_retrying": t(zh_CN="LLM 重试中", en_US="LLM retrying"),
        "sandbox_running": t(zh_CN="沙盒执行中", en_US="Sandbox running"),
        "sandbox_stopped": t(zh_CN="沙盒结束", en_US="Sandbox stopped"),
        "iterating": t(zh_CN="进入迭代", en_US="Iterating"),
        "completed": t(zh_CN="已完成", en_US="Completed"),
        "failed": t(zh_CN="生成失败", en_US="Generation failed"),
    }
    return phase_labels.get(phase or "", t(zh_CN="未知", en_US="Unknown"))


def _format_workspace_sandbox_status(status: str) -> str:
    status_labels = {
        "idle": t(zh_CN="闲置中", en_US="Idle"),
        "queued": t(zh_CN="排队中", en_US="Queued"),
        "running": t(zh_CN="执行中", en_US="Running"),
        "responding": t(zh_CN="回传结果", en_US="Responding"),
        "completed": t(zh_CN="已完成", en_US="Completed"),
        "cancelled": t(zh_CN="已中止", en_US="Cancelled"),
        "active": t(zh_CN="闲置中", en_US="Idle"),
        "stopped": t(zh_CN="已停止", en_US="Stopped"),
        "failed": t(zh_CN="执行失败", en_US="Failed"),
        "deleting": t(zh_CN="删除中", en_US="Deleting"),
        "unbound": t(zh_CN="未绑定", en_US="Unbound"),
    }
    return status_labels.get(status, t(zh_CN="未知", en_US="Unknown"))


def _resolve_channel_agent_runtime_status(chat_key: str) -> tuple[str, str]:
    from nekro_agent.services.system_broadcast import get_state_snapshot

    snapshot = get_state_snapshot()
    runtime_status: dict[str, Any] | None = snapshot.get("agent_runtime_status", {}).get(chat_key)
    if runtime_status is not None:
        phase = str(runtime_status.get("phase") or "")
        return _format_agent_runtime_phase(phase), phase

    active_status = snapshot.get("agent_active", {}).get(chat_key)
    if active_status is not None:
        return t(zh_CN="LLM 生成中", en_US="LLM generating"), "llm_generating"

    return t(zh_CN="闲置中", en_US="Idle"), "none"


async def _resolve_bound_workspace_sandbox_status(workspace_id: int | None) -> tuple[str, str]:
    if workspace_id is None:
        return _format_workspace_sandbox_status("unbound"), "unbound"

    from nekro_agent.models.db_workspace import DBWorkspace
    from nekro_agent.services.system_broadcast import get_state_snapshot

    snapshot = get_state_snapshot()
    workspace_status: dict[str, Any] | None = snapshot.get("workspace_status", {}).get(str(workspace_id))
    if workspace_status is not None:
        status = str(workspace_status.get("status") or "")
        if status == "active":
            runtime_status: dict[str, Any] | None = snapshot.get("workspace_cc_runtime_status", {}).get(str(workspace_id))
            if runtime_status is not None:
                phase = str(runtime_status.get("phase") or "")
                return _format_workspace_sandbox_status(phase), phase or "unknown"

            active_status: dict[str, Any] | None = snapshot.get("workspace_cc_active", {}).get(str(workspace_id))
            if active_status is not None:
                return _format_workspace_sandbox_status("running"), "running"

            return _format_workspace_sandbox_status("idle"), "idle"

        return _format_workspace_sandbox_status(status), status or "unknown"

    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        return t(zh_CN="未知", en_US="Unknown"), "unknown"

    if workspace.status == "active":
        return _format_workspace_sandbox_status("idle"), "idle"

    return _format_workspace_sandbox_status(workspace.status), workspace.status


class NaInfoCommand(BaseCommand):
    """查看系统信息"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_info",
            aliases=[],
            description="查看系统信息",
            i18n_description=i18n_text(zh_CN="查看系统信息", en_US="View system information"),
            permission=CommandPermission.USER,
            category="信息",
            i18n_category=i18n_text(zh_CN="信息", en_US="Information"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.core.os_env import OsEnv
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.tools.common_util import get_app_version

        db_chat_channel = await DBChatChannel.get_channel(chat_key=context.chat_key)
        preset = await db_chat_channel.get_preset()
        version = get_app_version()
        channel_status = db_chat_channel.channel_status.value
        channel_status_label = _format_channel_status(channel_status)
        runtime_status_label, runtime_status_phase = _resolve_channel_agent_runtime_status(context.chat_key)
        cc_sandbox_status_label, cc_sandbox_status_value = await _resolve_bound_workspace_sandbox_status(
            db_chat_channel.workspace_id
        )

        title = t(zh_CN="[Nekro-Agent 信息]", en_US="[Nekro-Agent Info]")
        subtitle = t(zh_CN="> 更智能、更优雅的代理执行 AI", en_US="> Smarter, more elegant agent execution AI")
        chat_settings = t(zh_CN="========聊天设定========", en_US="========Chat Settings========")
        preset_label = t(zh_CN="人设", en_US="Preset")
        channel_status_label_title = t(zh_CN="频道状态", en_US="Channel Status")
        runtime_status_label_title = t(zh_CN="Agent状态", en_US="Agent Status")
        cc_sandbox_status_label_title = t(zh_CN="CC沙盒状态", en_US="CC Sandbox Status")

        message = (
            f"{title}\n"
            f"{subtitle}\n"
            f"Author: KroMiose\n"
            f"Github: https://github.com/KroMiose/nekro-agent\n"
            f"Version: {version}\n"
            f"In-Docker: {OsEnv.RUN_IN_DOCKER}\n"
            f"{chat_settings}\n"
            f"{preset_label}: {preset.name}\n"
            f"{channel_status_label_title}: {channel_status_label}\n"
            f"{runtime_status_label_title}: {runtime_status_label}\n"
            f"{cc_sandbox_status_label_title}: {cc_sandbox_status_label}"
        )

        return CmdCtl.success(
            message,
            data={
                "version": version,
                "in_docker": OsEnv.RUN_IN_DOCKER,
                "preset": preset.name,
                "channel_status": channel_status_label,
                "channel_status_value": channel_status,
                "agent_runtime_status": runtime_status_label,
                "agent_runtime_phase": runtime_status_phase,
                "cc_sandbox_status": cc_sandbox_status_label,
                "cc_sandbox_status_value": cc_sandbox_status_value,
                "bound_workspace_id": db_chat_channel.workspace_id,
            },
        )


class NaHelpCommand(BaseCommand):
    """查看帮助信息"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_help",
            aliases=[],
            description="查看帮助信息",
            i18n_description=i18n_text(zh_CN="查看帮助信息", en_US="View help information"),
            permission=CommandPermission.USER,
            category="信息",
            i18n_category=i18n_text(zh_CN="信息", en_US="Information"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.services.command.registry import command_registry
        from nekro_agent.tools.common_util import get_app_version

        # 从注册表动态生成帮助信息
        commands = command_registry.list_all_commands()
        conflicts = command_registry.get_conflicting_short_names()

        # 按分类分组
        categories: dict[str, list[str]] = {}
        for meta in commands:
            cat = meta.get_category(context.lang)
            categories.setdefault(cat, [])
            # 构建命令描述行
            name = meta.name
            if name in conflicts:
                name = f"{meta.namespace}:{meta.name}"
            alias_str = f" ({', '.join(meta.aliases)})" if meta.aliases else ""
            perm_str = f"[{meta.permission.value.upper()}]" if meta.permission != CommandPermission.PUBLIC else ""
            line = f"{name}{alias_str}: {meta.get_description(context.lang)} {perm_str}".strip()
            categories[cat].append(line)

        # 构建输出
        help_title = t(zh_CN="[Nekro-Agent 帮助]", en_US="[Nekro-Agent Help]")
        more_info = t(zh_CN="更多信息", en_US="More Info")
        parts = [help_title]
        for cat_name, lines in categories.items():
            parts.append(f"\n====== [{cat_name}] ======")
            parts.extend(lines)

        parts.append(f"\n====== [{more_info}] ======")
        parts.append(f"Version: {get_app_version()}")
        parts.append("Github: https://github.com/KroMiose/nekro-agent")

        return CmdCtl.success("\n".join(parts))
