"""内置命令 - 配额类: quota, quota_boost, quota_reset, quota_set, quota_whitelist"""

import time
from typing import Annotated

from nekro_agent.schemas.i18n import i18n_text, t
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
            i18n_description=i18n_text(zh_CN="查看频道配额状态", en_US="View channel quota status"),
            permission=CommandPermission.SUPER_USER,
            category="配额",
            i18n_category=i18n_text(zh_CN="配额", en_US="Quota"),
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

        title = t(zh_CN="[频道配额状态]", en_US="[Channel Quota Status]")
        lines = [f"{title} {context.chat_key}", ""]

        quota_section = t(zh_CN="===== 每日回复配额 =====", en_US="===== Daily Reply Quota =====")
        lines.append(quota_section)
        bot_reply_label = t(zh_CN="今日 Bot 回复", en_US="Today bot replies")
        total_msg_label = t(zh_CN="今日总消息数", en_US="Today total messages")
        lines.append(f"{bot_reply_label}: {daily_bot_count}")
        lines.append(f"{total_msg_label}: {daily_total_count}")

        if effective_limit <= 0:
            limit_label = t(zh_CN="配置限额", en_US="Configured limit")
            unlimited = t(zh_CN="无限制", en_US="Unlimited")
            lines.append(f"{limit_label}: {unlimited}")
        else:
            limit_label = t(zh_CN="配置限额", en_US="Configured limit")
            lines.append(f"{limit_label}: {daily_limit}")
            if boost > 0:
                boost_label = t(zh_CN="临时提升", en_US="Temporary boost")
                effective_label = t(zh_CN="有效限额", en_US="Effective limit")
                lines.append(f"{boost_label}: +{boost}")
                lines.append(f"{effective_label}: {effective_limit}")
            remaining_label = t(zh_CN="今日剩余", en_US="Today remaining")
            lines.append(f"{remaining_label}: {max(0, effective_limit - daily_bot_count)}")

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
                hourly_label = t(zh_CN="小时限额", en_US="Hourly limit")
                hourly_used = t(zh_CN="本小时已用", en_US="Used this hour")
                lines.append(f"{hourly_label}: {hourly_limit}")
                lines.append(f"{hourly_used}: {hourly_count}")

        lines.append("")
        ctx_section = t(zh_CN="===== 会话上下文 =====", en_US="===== Session Context =====")
        lines.append(ctx_section)
        session_label = t(zh_CN="当前会话消息数", en_US="Current session messages")
        max_label = t(zh_CN="上下文最大条数", en_US="Max context length")
        lines.append(f"{session_label}: {session_msg_count}")
        lines.append(f"{max_label}: {context_max_length}")

        return CmdCtl.success("\n".join(lines))


class QuotaBoostCommand(BaseCommand):
    """临时提升配额"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="quota_boost",
            aliases=["quota-boost"],
            description="临时提升当日配额",
            i18n_description=i18n_text(zh_CN="临时提升当日配额", en_US="Temporarily boost daily quota"),
            usage="quota_boost <数字>",
            permission=CommandPermission.SUPER_USER,
            category="配额",
            i18n_category=i18n_text(zh_CN="配额", en_US="Quota"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        amount_str: Annotated[str, Arg("提升数量（正数增加，负数减少）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.services.quota_service import quota_service

        if not amount_str or not amount_str.lstrip("-").isdigit():
            return CmdCtl.failed(
                t(
                    zh_CN="用法: /quota_boost <数字>  (正数增加，负数减少，如 /quota_boost 10)",
                    en_US="Usage: /quota_boost <number>  (positive to increase, negative to decrease, e.g. /quota_boost 10)",
                )
            )

        amount = int(amount_str)
        new_total = quota_service.add_boost(context.chat_key, amount)
        if new_total < 0:
            new_total = 0
            quota_service.set_boost(context.chat_key, 0)
        sign = "+" if amount >= 0 else ""
        return CmdCtl.success(
            t(
                zh_CN=f"频道 {context.chat_key} 今日临时配额调整 {sign}{amount}，当前总提升: {new_total}",
                en_US=f"Channel {context.chat_key} daily quota adjusted {sign}{amount}, current total boost: {new_total}",
            )
        )


class QuotaResetCommand(BaseCommand):
    """重置配额提升"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="quota_reset",
            aliases=["quota-reset"],
            description="重置频道配额提升",
            i18n_description=i18n_text(zh_CN="重置频道配额提升", en_US="Reset channel quota boost"),
            permission=CommandPermission.SUPER_USER,
            category="配额",
            i18n_category=i18n_text(zh_CN="配额", en_US="Quota"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.services.quota_service import quota_service

        quota_service.clear_boost(context.chat_key)
        return CmdCtl.success(
            t(
                zh_CN=f"频道 {context.chat_key} 的临时配额提升已清除，恢复默认限额",
                en_US=f"Channel {context.chat_key} temporary quota boost cleared, restored to default limit",
            )
        )


class QuotaSetCommand(BaseCommand):
    """设置频道配额限制"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="quota_set",
            aliases=["quota-set"],
            description="设置频道每日配额限制",
            i18n_description=i18n_text(zh_CN="设置频道每日配额限制", en_US="Set channel daily quota limit"),
            usage="quota_set <数字>",
            permission=CommandPermission.SUPER_USER,
            category="配额",
            i18n_category=i18n_text(zh_CN="配额", en_US="Quota"),
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
            return CmdCtl.failed(
                t(
                    zh_CN="用法: /quota_set <数字>  (如 /quota_set 50，0 表示不限制)",
                    en_US="Usage: /quota_set <number>  (e.g. /quota_set 50, 0 means unlimited)",
                )
            )

        amount = int(amount_str)
        config_key = f"channel_config_{context.chat_key}"

        success, msg = UnifiedConfigService.set_config_value(config_key, "enable_AI_CHAT_DAILY_REPLY_LIMIT", "true")
        if not success:
            return CmdCtl.failed(t(zh_CN=f"设置失败: {msg}", en_US=f"Setting failed: {msg}"))

        success, msg = UnifiedConfigService.set_config_value(config_key, "AI_CHAT_DAILY_REPLY_LIMIT", str(amount))
        if not success:
            return CmdCtl.failed(t(zh_CN=f"设置失败: {msg}", en_US=f"Setting failed: {msg}"))

        success, msg = UnifiedConfigService.save_config(config_key)
        if not success:
            return CmdCtl.failed(t(zh_CN=f"保存失败: {msg}", en_US=f"Save failed: {msg}"))

        db_chat_channel = await DBChatChannel.get_channel(chat_key=context.chat_key)
        db_chat_channel._effective_config = None  # noqa: SLF001

        unlimited = t(zh_CN="无限制", en_US="Unlimited")
        display = unlimited if amount <= 0 else str(amount)
        return CmdCtl.success(
            t(
                zh_CN=f"频道 {context.chat_key} 的每日配额限制已设置为 {display}，重启后仍有效",
                en_US=f"Channel {context.chat_key} daily quota limit set to {display}, persists after restart",
            )
        )


class QuotaWhitelistCommand(BaseCommand):
    """管理配额用户白名单"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="quota_whitelist",
            aliases=["quota-whitelist"],
            description="管理配额用户白名单",
            i18n_description=i18n_text(zh_CN="管理配额用户白名单", en_US="Manage quota user whitelist"),
            usage="quota_whitelist [add|remove <用户ID>]",
            permission=CommandPermission.SUPER_USER,
            category="配额",
            i18n_category=i18n_text(zh_CN="配额", en_US="Quota"),
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
            title = t(zh_CN="配额用户白名单:", en_US="Quota user whitelist:")
            lines = [title]
            if user_whitelist:
                for u in user_whitelist:
                    lines.append(f"  - {u}")
            else:
                empty = t(zh_CN="(空)", en_US="(empty)")
                lines.append(f"  {empty}")
            return CmdCtl.success("\n".join(lines))

        cmd = parts[0]

        if cmd == "add" and len(parts) >= 2:
            user_id = parts[1]
            if user_id not in config.AI_CHAT_QUOTA_WHITELIST_USERS:
                config.AI_CHAT_QUOTA_WHITELIST_USERS.append(user_id)
                save_config()
                return CmdCtl.success(
                    t(zh_CN=f"已将用户 {user_id} 添加到配额白名单", en_US=f"Added user {user_id} to quota whitelist")
                )
            else:
                return CmdCtl.success(
                    t(zh_CN=f"用户 {user_id} 已在白名单中", en_US=f"User {user_id} is already in the whitelist")
                )

        if cmd == "remove" and len(parts) >= 2:
            user_id = parts[1]
            if user_id in config.AI_CHAT_QUOTA_WHITELIST_USERS:
                config.AI_CHAT_QUOTA_WHITELIST_USERS.remove(user_id)
                save_config()
                return CmdCtl.success(
                    t(zh_CN=f"已将用户 {user_id} 从配额白名单移除", en_US=f"Removed user {user_id} from quota whitelist")
                )
            else:
                return CmdCtl.success(
                    t(zh_CN=f"用户 {user_id} 不在白名单中", en_US=f"User {user_id} is not in the whitelist")
                )

        return CmdCtl.failed(
            t(
                zh_CN=(
                    "用法:\n"
                    "  /quota_whitelist                — 查看当前用户白名单\n"
                    "  /quota_whitelist add <用户ID>   — 添加用户到白名单\n"
                    "  /quota_whitelist remove <用户ID> — 从白名单移除用户"
                ),
                en_US=(
                    "Usage:\n"
                    "  /quota_whitelist                — View current user whitelist\n"
                    "  /quota_whitelist add <userID>   — Add user to whitelist\n"
                    "  /quota_whitelist remove <userID> — Remove user from whitelist"
                ),
            )
        )
