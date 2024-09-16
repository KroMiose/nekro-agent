import os
from typing import List, Optional, Tuple, Union

from miose_toolkit_common import Env
from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from nekro_agent.core.config import config, reload_config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.chat_channel import (
    MAX_PRESET_STATUS_SHOW_SIZE,
    PresetStatus,
    channelData,
)
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.chat import chat_service
from nekro_agent.services.sandbox.executor import limited_run_code
from nekro_agent.systems.message.push_bot_msg import push_system_message
from nekro_agent.tools.common_util import get_app_version
from nekro_agent.tools.onebot_util import gen_chat_text, get_chat_info, get_user_name


async def command_guard(
    event: Union[MessageEvent, GroupMessageEvent],
    bot: Bot,
    arg: Message,
    matcher: Matcher,
) -> Tuple[str, str, str, ChatType]:
    """指令执行前处理

    Args:
        event (Union[MessageEvent, GroupMessageEvent]): 事件对象
        bot (Bot): Bot 对象
        arg (Message): 命令参数
        matcher (Matcher): Matcher 对象

    Returns:
        Tuple[str, ChatType]: 用户名, 命令内容(不含命令名), 会话标识, 会话类型
    """
    username = await get_user_name(event=event, bot=bot, user_id=event.get_user_id())
    # 判断是否是禁止使用的用户
    if event.get_user_id() not in config.SUPER_USERS:
        logger.warning(f"用户 {username} 不在允许用户中")
        await matcher.finish(f"用户 [{event.get_user_id()}]{username} 不在允许用户中")

    cmd_content: str = arg.extract_plain_text().strip()
    chat_key, chat_type = await get_chat_info(event=event)
    return username, cmd_content, chat_key, chat_type


@on_command("reset", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    target_chat_key: str = cmd_content or chat_key
    if not target_chat_key:
        await matcher.finish(message="请指定要清空聊天记录的会话")
    db_chat_channel: DBChatChannel = DBChatChannel.get_channel(chat_key=target_chat_key)
    db_chat_channel.reset_channel()
    msgs = DBChatMessage.filter(conditions={DBChatMessage.chat_key: target_chat_key})
    msg_cnt = len(msgs)

    for msg in msgs:
        msg.delete()
    await matcher.finish(message=f"已清空 {msg_cnt} 条 {target_chat_key} 的聊天记录")


@on_command("inspect", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    target_chat_key: str = cmd_content or chat_key
    if not target_chat_key:
        await matcher.finish(message="请指定要查询的会话")
    db_chat_channel: DBChatChannel = DBChatChannel.get_channel(chat_key=target_chat_key)

    info = f"基本人设: {config.AI_CHAT_PRESET_NAME}\n"
    channel_data: channelData = db_chat_channel.get_channel_data()
    if channel_data.preset_status_list:
        info += "人设状态历史:\n"
    for status in channel_data.preset_status_list[-MAX_PRESET_STATUS_SHOW_SIZE:]:
        info += f"[{status.setting_name}] - {status.description}\n"

    await matcher.finish(message=f"频道 {target_chat_key} 信息：\n{info.strip()}")


@on_command("exec", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    result: str = await limited_run_code(cmd_content, from_chat_key=chat_key)

    if result:
        await matcher.finish(result)


@on_command("system", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    await push_system_message(chat_key=chat_key, agent_messages=cmd_content)
    await matcher.finish(message="系统消息添加成功")


@on_command("config_show", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if not cmd_content:
        modifiable_config_key: List[str] = []
        for _key, _value in config.dump_config_template().items():
            if isinstance(_value, (int, float, bool, str)):
                modifiable_config_key.append(_key)
        sep = "\n"
        await matcher.finish(message=f"当前支持动态修改配置：\n{sep.join([f'- {k}' for k in modifiable_config_key])}")
    else:
        if config.dump_config_template().get(cmd_content):
            await matcher.finish(message=f"当前配置：\n{cmd_content}={getattr(config, cmd_content)}")
        else:
            await matcher.finish(message=f"未知配置 `{cmd_content}`")


@on_command("config_set", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    try:
        key, value = cmd_content.strip().split("=", 1)
    except ValueError:
        await matcher.finish(message="参数错误，请使用 `config_set key=value` 的格式")

    if config.dump_config_template().get(key):
        _c_type = type(getattr(config, key))
        _c_value = getattr(config, key)
        if isinstance(_c_value, (int, float)):
            setattr(config, key, _c_type(value))
        elif isinstance(_c_value, bool):
            if value.lower() in ["true", "1", "yes"]:
                setattr(config, key, True)
            elif value.lower() in ["false", "0", "no"]:
                setattr(config, key, False)
            else:
                await matcher.finish(message=f"布尔值只能是 `true` 或 `false`，请检查 `{key}` 的值")
        elif isinstance(_c_value, str):
            setattr(config, key, _c_type(value))
        else:
            await matcher.finish(message=f"不支持动态修改的配置类型 `{_c_type}`")
        await matcher.finish(message=f"已设置 `{key}` 的值为 `{value}`")
    else:
        await matcher.finish(message=f"未知配置: `{key}`")


@on_command("config_reload", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    await matcher.finish(message="功能未实现")
    try:
        config.dump_config(envs=[Env.Default.value])
    except Exception as e:
        await matcher.finish(message=f"保存配置失败：{e}")
    else:
        await matcher.finish(message="已保存配置")


@on_command("config_save", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    await matcher.finish(message="功能未实现")
    reload_config()
    await matcher.finish(message="重载配置成功")


@on_command("docker_restart", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if not OsEnv.RUN_IN_DOCKER:
        await matcher.finish(message="当前环境不在 Docker 容器中，无法执行此操作")

    container_name: str = cmd_content or "nekro_agent"
    os.system(f"docker restart {container_name}")


@on_command("docker_logs", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if not OsEnv.RUN_IN_DOCKER:
        await matcher.finish(message="当前环境不在 Docker 容器中，无法执行此操作")

    lines_limit: int = 100
    container_name: str = cmd_content or "nekro_agent"
    logs = os.popen(f"docker logs {container_name} --tail {lines_limit}").read()
    await matcher.finish(message=f"容器日志: \n{logs}")


@on_command("sh", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    outputs = os.popen(cmd_content).read()
    await matcher.finish(message=f"命令 `{cmd_content}` 输出: \n{outputs or '<Empty>'}")


@on_command("na_info", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    version: str = get_app_version()
    await matcher.finish(
        message=(
            f"[Nekro-Agent] - 更智能、更优雅的代理执行 AI\n"
            f"Author: KroMiose\n"
            f"Github: https://github.com/KroMiose/nekro-agent\n"
            f"Version: {version}\n"
            f"In-Docker: {OsEnv.RUN_IN_DOCKER}\n"
            "========会话设定========\n"
            f"人设: {config.AI_CHAT_PRESET_NAME}\n"
            f"当前模型组: {config.USE_MODEL_GROUP}\n"
        ).strip(),
    )
