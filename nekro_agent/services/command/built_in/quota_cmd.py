"""内置命令 - 配额类: quota, quota_boost, quota_reset, quota_set, quota_whitelist"""

import time
from typing import Annotated

from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class QuotaCommand(BaseCommand):
    """查看配额状态"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="quota",
            description="查看频道配额状态",
            permission=CommandPermission.SUPER_USER,
            category="配额",
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.models.db_chat_message import DBChatMessage
        from nekro_agent.services.quota_service import quota_service

        db_chat_channel = await DBChatChannel.get_channel(chat_key=context.chat_key)
        effective_config = await db_chat_channel.get_effective_config()
        daily_limit = effective_config.AI_CHAT_DAILY_REPLY_LIMIT

        boost = quota_service.get_boost(context.chat_key)
        effective_limit = daily_limit + boost

        today_start = time.time() - (time.time() % 86400)
        daily_bot_count = (
            await DBChatMessage.filter(
                chat_key=context.chat_key,
                sender_id=-1,
                send_timestamp__gte=int(today_start),
            )
            .exclude(sender_name="SYSTEM")
            .count()
        )
        daily_total_count = await DBChatMessage.filter(
            chat_key=context.chat_key,
            send_timestamp__gte=int(today_start),
        ).count()

        session_msg_count = await DBChatMessage.filter(
            chat_key=context.chat_key,
            send_timestamp__gte=int(db_chat_channel.conversation_start_time.timestamp()),
        ).count()
        context_max_length = effective_config.AI_CHAT_CONTEXT_MAX_LENGTH

        lines = [f"[频道配额状态] {context.chat_key}", ""]
        lines.append("===== 每日回复配额 =====")
        lines.append(f"今日 Bot 回复: {daily_bot_count}")
        lines.append(f"今日总消息数: {daily_total_count}")

        if effective_limit <= 0:
            lines.append("配置限额: 无限制")
        else:
            lines.append(f"配置限额: {daily_limit}")
            if boost > 0:
                lines.append(f"临时提升: +{boost}")
                lines.append(f"有效限额: {effective_limit}")
            lines.append(f"今日剩余: {max(0, effective_limit - daily_bot_count)}")

            if effective_config.AI_CHAT_ENABLE_HOURLY_LIMIT:
                hourly_limit = quota_service.calculate_hourly_quota(effective_limit)
                hour_start = time.time() - (time.time() % 3600)
                hourly_count = (
                    await DBChatMessage.filter(
                        chat_key=context.chat_key,
                        sender_id=-1,
                        send_timestamp__gte=int(hour_start),
                    )
                    .exclude(sender_name="SYSTEM")
                    .count()
                )
                lines.append(f"小时限额: {hourly_limit}")
                lines.append(f"本小时已用: {hourly_count}")

        lines.append("")
        lines.append("===== 会话上下文 =====")
        lines.append(f"当前会话消息数: {session_msg_count}")
        lines.append(f"上下文最大条数: {context_max_length}")

        return CmdCtl.success("\n".join(lines))


class QuotaBoostCommand(BaseCommand):
    """临时提升配额"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="quota_boost",
            aliases=["quota-boost"],
            description="临时提升当日配额",
            usage="quota_boost <数字>",
            permission=CommandPermission.SUPER_USER,
            category="配额",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        amount_str: Annotated[str, Arg("提升数量（正数增加，负数减少）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.services.quota_service import quota_service

        if not amount_str or not amount_str.lstrip("-").isdigit():
            return CmdCtl.failed("用法: /quota_boost <数字>  (正数增加，负数减少，如 /quota_boost 10)")

        amount = int(amount_str)
        new_total = quota_service.add_boost(context.chat_key, amount)
        if new_total < 0:
            new_total = 0
            quota_service.set_boost(context.chat_key, 0)
        sign = "+" if amount >= 0 else ""
        return CmdCtl.success(
            f"频道 {context.chat_key} 今日临时配额调整 {sign}{amount}，当前总提升: {new_total}"
        )


class QuotaResetCommand(BaseCommand):
    """重置配额提升"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="quota_reset",
            aliases=["quota-reset"],
            description="重置频道配额提升",
            permission=CommandPermission.SUPER_USER,
            category="配额",
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.services.quota_service import quota_service

        quota_service.clear_boost(context.chat_key)
        return CmdCtl.success(f"频道 {context.chat_key} 的临时配额提升已清除，恢复默认限额")


class QuotaSetCommand(BaseCommand):
    """设置频道配额限制"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="quota_set",
            aliases=["quota-set"],
            description="设置频道每日配额限制",
            usage="quota_set <数字>",
            permission=CommandPermission.SUPER_USER,
            category="配额",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        amount_str: Annotated[str, Arg("每日配额限制（0表示不限制）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.services.config_service import UnifiedConfigService

        if not amount_str or not amount_str.lstrip("-").isdigit():
            return CmdCtl.failed("用法: /quota_set <数字>  (如 /quota_set 50，0 表示不限制)")

        amount = int(amount_str)
        config_key = f"channel_config_{context.chat_key}"

        success, msg = UnifiedConfigService.set_config_value(config_key, "enable_AI_CHAT_DAILY_REPLY_LIMIT", "true")
        if not success:
            return CmdCtl.failed(f"设置失败: {msg}")

        success, msg = UnifiedConfigService.set_config_value(config_key, "AI_CHAT_DAILY_REPLY_LIMIT", str(amount))
        if not success:
            return CmdCtl.failed(f"设置失败: {msg}")

        success, msg = UnifiedConfigService.save_config(config_key)
        if not success:
            return CmdCtl.failed(f"保存失败: {msg}")

        db_chat_channel = await DBChatChannel.get_channel(chat_key=context.chat_key)
        db_chat_channel._effective_config = None  # noqa: SLF001

        display = "无限制" if amount <= 0 else str(amount)
        return CmdCtl.success(f"频道 {context.chat_key} 的每日配额限制已设置为 {display}，重启后仍有效")


class QuotaWhitelistCommand(BaseCommand):
    """管理配额用户白名单"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="quota_whitelist",
            aliases=["quota-whitelist"],
            description="管理配额用户白名单",
            usage="quota_whitelist [add|remove <用户ID>]",
            permission=CommandPermission.SUPER_USER,
            category="配额",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        args_str: Annotated[str, Arg("子命令和参数", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.core.config import config, save_config

        parts = args_str.strip().split() if args_str else []

        if not parts:
            user_whitelist = config.AI_CHAT_QUOTA_WHITELIST_USERS
            lines = ["配额用户白名单:"]
            if user_whitelist:
                for u in user_whitelist:
                    lines.append(f"  - {u}")
            else:
                lines.append("  (空)")
            return CmdCtl.success("\n".join(lines))

        cmd = parts[0]

        if cmd == "add" and len(parts) >= 2:
            user_id = parts[1]
            if user_id not in config.AI_CHAT_QUOTA_WHITELIST_USERS:
                config.AI_CHAT_QUOTA_WHITELIST_USERS.append(user_id)
                save_config()
                return CmdCtl.success(f"已将用户 {user_id} 添加到配额白名单")
            else:
                return CmdCtl.success(f"用户 {user_id} 已在白名单中")

        if cmd == "remove" and len(parts) >= 2:
            user_id = parts[1]
            if user_id in config.AI_CHAT_QUOTA_WHITELIST_USERS:
                config.AI_CHAT_QUOTA_WHITELIST_USERS.remove(user_id)
                save_config()
                return CmdCtl.success(f"已将用户 {user_id} 从配额白名单移除")
            else:
                return CmdCtl.success(f"用户 {user_id} 不在白名单中")

        return CmdCtl.failed(
            "用法:\n"
            "  /quota_whitelist                — 查看当前用户白名单\n"
            "  /quota_whitelist add <用户ID>   — 添加用户到白名单\n"
            "  /quota_whitelist remove <用户ID> — 从白名单移除用户"
        )
