"""内置命令 - 用户类"""

from typing import Annotated

from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.i18n import i18n_text, t
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


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
