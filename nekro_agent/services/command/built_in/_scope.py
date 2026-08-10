"""内置命令作用域辅助。"""

from typing import Optional

from nekro_agent.schemas.i18n import t
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import CommandExecutionContext, CommandResponse


def resolve_channel_target(
    context: CommandExecutionContext,
    target: str,
    *,
    missing_message: Optional[CommandResponse] = None,
) -> tuple[Optional[str], Optional[CommandResponse]]:
    """解析频道目标。

    SUPER_USER 可指定任意目标；非 SUPER_USER 只能操作当前频道。
    """
    normalized_target = target.strip()
    if context.is_super_user:
        target_chat_key = normalized_target or context.chat_key
    elif normalized_target and normalized_target != context.chat_key:
        return None, CmdCtl.failed(
            t(
                zh_CN="此命令仅允许操作当前频道，跨频道或批量操作需要超级用户权限",
                en_US="This command can only operate on the current channel. Cross-channel or bulk operations require super user permission.",
            )
        )
    else:
        target_chat_key = context.chat_key

    if not target_chat_key:
        return None, missing_message or CmdCtl.failed(
            t(zh_CN="请指定要操作的聊天", en_US="Please specify the target chat")
        )

    return target_chat_key, None
