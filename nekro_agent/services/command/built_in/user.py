"""内置命令 - 用户类"""

from typing import Annotated

from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.i18n import i18n_text, t
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


def _resolve_target_adapter_key(context: CommandExecutionContext, adapter_key: str) -> str:
    target_adapter_key = adapter_key.strip() or context.adapter_key
    if not target_adapter_key:
        raise ValueError("adapter_key 不能为空")
    return target_adapter_key


class SetUsernameCommand(BaseCommand):
    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="set_username",
            aliases=["name", "rename"],
            description="修改自己的用户名",
            i18n_description=i18n_text(zh_CN="修改自己的用户名", en_US="Change your username"),
            usage="set_username <用户名>",
            i18n_usage=i18n_text(zh_CN="set_username <用户名>", en_US="set_username <username>"),
            permission=CommandPermission.USER,
            category="用户",
            i18n_category=i18n_text(zh_CN="用户", en_US="User"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        username: Annotated[str, Arg("新的用户名", positional=True, greedy=True)],
    ) -> CommandResponse:
        new_username = username.strip()
        if not new_username:
            return CmdCtl.failed(t(zh_CN="用户名不能为空", en_US="Username cannot be empty"))
        if len(new_username) > 128:
            return CmdCtl.failed(t(zh_CN="用户名不能超过 128 个字符", en_US="Username cannot exceed 128 characters"))

        user = await DBUser.get_by_union_id(adapter_key=context.adapter_key, platform_userid=context.user_id)
        if user is None:
            return CmdCtl.failed(
                t(
                    zh_CN="未找到你的用户数据，请先发送一条普通消息完成注册",
                    en_US="User data not found. Send a regular message first to complete registration",
                )
            )

        user.username = new_username
        await user.save()
        return CmdCtl.success(
            t(zh_CN=f"用户名已修改为：{new_username}", en_US=f"Username changed to: {new_username}"),
            data={"username": new_username},
        )


class GrantAdvancedCommand(BaseCommand):
    """授予平台用户高级命令权限"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="grant_advanced",
            aliases=["adv_grant"],
            description="授予平台用户高级命令权限",
            i18n_description=i18n_text(
                zh_CN="授予平台用户高级命令权限",
                en_US="Grant advanced command permission to a platform user",
            ),
            usage="grant_advanced <platform_userid> [adapter_key]",
            i18n_usage=i18n_text(
                zh_CN="grant_advanced <平台用户ID> [适配器ID]",
                en_US="grant_advanced <platform_userid> [adapter_key]",
            ),
            permission=CommandPermission.SUPER_USER,
            category="用户",
            i18n_category=i18n_text(zh_CN="用户", en_US="User"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        platform_userid: Annotated[str, Arg("平台用户 ID", positional=True)],
        adapter_key: Annotated[str, Arg("适配器 ID，默认当前适配器", positional=True)] = "",
    ) -> CommandResponse:
        target_userid = platform_userid.strip()
        if not target_userid:
            return CmdCtl.failed(t(zh_CN="平台用户 ID 不能为空", en_US="Platform user ID cannot be empty"))

        try:
            target_adapter_key = _resolve_target_adapter_key(context, adapter_key)
        except ValueError as e:
            return CmdCtl.failed(str(e))

        from nekro_agent.adapters.utils import adapter_utils

        adapter = adapter_utils.get_adapter(target_adapter_key)
        await adapter.set_user_command_permission(target_userid, CommandPermission.ADVANCED)
        return CmdCtl.success(
            t(
                zh_CN=f"已授予 {target_adapter_key}:{target_userid} 高级命令权限",
                en_US=f"Granted advanced command permission to {target_adapter_key}:{target_userid}",
            ),
            data={
                "adapter_key": target_adapter_key,
                "platform_userid": target_userid,
                "permission": CommandPermission.ADVANCED.value,
            },
        )


class RevokeAdvancedCommand(BaseCommand):
    """撤销平台用户高级命令权限"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="revoke_advanced",
            aliases=["adv_revoke"],
            description="撤销平台用户高级命令权限",
            i18n_description=i18n_text(
                zh_CN="撤销平台用户高级命令权限",
                en_US="Revoke advanced command permission from a platform user",
            ),
            usage="revoke_advanced <platform_userid> [adapter_key]",
            i18n_usage=i18n_text(
                zh_CN="revoke_advanced <平台用户ID> [适配器ID]",
                en_US="revoke_advanced <platform_userid> [adapter_key]",
            ),
            permission=CommandPermission.SUPER_USER,
            category="用户",
            i18n_category=i18n_text(zh_CN="用户", en_US="User"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        platform_userid: Annotated[str, Arg("平台用户 ID", positional=True)],
        adapter_key: Annotated[str, Arg("适配器 ID，默认当前适配器", positional=True)] = "",
    ) -> CommandResponse:
        target_userid = platform_userid.strip()
        if not target_userid:
            return CmdCtl.failed(t(zh_CN="平台用户 ID 不能为空", en_US="Platform user ID cannot be empty"))

        try:
            target_adapter_key = _resolve_target_adapter_key(context, adapter_key)
        except ValueError as e:
            return CmdCtl.failed(str(e))

        from nekro_agent.adapters.utils import adapter_utils

        adapter = adapter_utils.get_adapter(target_adapter_key)
        await adapter.reset_user_command_permission(target_userid)
        return CmdCtl.success(
            t(
                zh_CN=f"已撤销 {target_adapter_key}:{target_userid} 的高级命令权限",
                en_US=f"Revoked advanced command permission from {target_adapter_key}:{target_userid}",
            ),
            data={
                "adapter_key": target_adapter_key,
                "platform_userid": target_userid,
                "permission": CommandPermission.USER.value,
            },
        )
