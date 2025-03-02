import os
import time
from typing import List, Optional, Tuple, Union

from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from nekro_agent.core.config import config, reload_config, save_config
from nekro_agent.core.database import reset_db
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_exec_code import DBExecCode
from nekro_agent.schemas.chat_channel import ChannelData
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.extension import get_all_ext_meta_data, reload_ext_workdir
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.sandbox.executor import limited_run_code
from nekro_agent.tools.common_util import get_app_version
from nekro_agent.tools.onebot_util import get_chat_info, get_user_name


async def finish_with(matcher: Matcher, message: str):
    await matcher.finish(message=f"[Opt Output] {message}")


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
        Tuple[str, str, str, ChatType]: 用户名, 命令内容(不含命令名), 会话标识, 会话类型
    """
    username = await get_user_name(event=event, bot=bot, user_id=event.get_user_id())
    # 判断是否是禁止使用的用户
    if event.get_user_id() not in config.SUPER_USERS:
        logger.warning(f"用户 {username} 不在允许的管理用户中")
        if config.ENABLE_COMMAND_UNAUTHORIZED_OUTPUT:
            await finish_with(matcher, f"用户 [{event.get_user_id()}]{username} 不在允许的管理用户中")
        else:
            await matcher.finish()

    cmd_content: str = arg.extract_plain_text().strip()
    chat_key, chat_type = await get_chat_info(event=event)
    return username, cmd_content, chat_key, chat_type


async def reset_command_guard(
    event: Union[MessageEvent, GroupMessageEvent],
    bot: Bot,
    arg: Message,
    matcher: Matcher,
) -> Tuple[str, str, str, ChatType]:
    """Reset指令鉴权"""
    username = await get_user_name(event=event, bot=bot, user_id=event.get_user_id())
    cmd_content: str = arg.extract_plain_text().strip()
    chat_key, chat_type = await get_chat_info(event=event)

    if event.get_user_id() in config.SUPER_USERS:
        return username, cmd_content, chat_key, chat_type

    # 非超级用户
    if cmd_content and chat_key != cmd_content:
        logger.warning(f"用户 {username} 尝试越权操作其他会话")
        if config.ENABLE_COMMAND_UNAUTHORIZED_OUTPUT:
            await finish_with(matcher, "您只能操作当前会话")
        else:
            await matcher.finish()

    # 私聊用户允许操作
    if chat_type == ChatType.PRIVATE:
        return username, cmd_content, chat_key, chat_type

    # 群聊检查管理员权限
    if chat_type == ChatType.GROUP and isinstance(event, GroupMessageEvent) and event.sender.role in ["admin", "owner"]:
        return username, cmd_content, chat_key, chat_type

    # 无权限情况处理
    logger.warning(f"用户 {username} 不在允许的管理用户中")
    if config.ENABLE_COMMAND_UNAUTHORIZED_OUTPUT:
        await finish_with(matcher, f"用户 [{event.get_user_id()}]{username} 不在允许的管理用户中")
    else:
        await matcher.finish()
    raise


@on_command("reset", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await reset_command_guard(event, bot, arg, matcher)

    target_chat_key = cmd_content if cmd_content and event.get_user_id() in config.SUPER_USERS else chat_key

    if not target_chat_key:
        logger.warning("会话标识获取失败")
        if config.ENABLE_COMMAND_UNAUTHORIZED_OUTPUT:
            await finish_with(matcher, message="会话标识获取失败")
        else:
            await matcher.finish()

    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=target_chat_key)
    await db_chat_channel.reset_channel()
    query = DBChatMessage.filter(chat_key=target_chat_key)
    msg_cnt = await query.count()
    await query.delete()

    await finish_with(matcher, message=f"已清空 {msg_cnt} 条 {target_chat_key} 的聊天记录")


@on_command("inspect", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    target_chat_key: str = cmd_content or chat_key
    if not target_chat_key:
        await finish_with(matcher, message="请指定要查询的会话")
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=target_chat_key)

    info = f"基本人设: {config.AI_CHAT_PRESET_NAME}\n"
    channel_data: ChannelData = await db_chat_channel.get_channel_data()
    if channel_data.preset_status_list:
        info += "人设状态历史:\n"
    for status in channel_data.preset_status_list[-config.AI_MAX_PRESET_STATUS_REFER_SIZE :]:
        info += f"[{status.setting_name}] - {status.description}\n"

    info += "状态笔记:\n"
    for note in channel_data.preset_notes.values():
        info += f"- {note.title} ({note.description})\n"
    if not channel_data.preset_notes:
        info += "- 暂无状态笔记\n"

    await finish_with(matcher, message=f"频道 {target_chat_key} 信息：\n{info.strip()}")


@on_command("exec", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    result, _ = await limited_run_code(cmd_content, cot_content="", from_chat_key=chat_key)

    if result:
        await finish_with(matcher, result)


@on_command("code_log", aliases={"code-log"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    idx = -1
    if cmd_content:
        idx = int(cmd_content)

    # 使用 Tortoise ORM 的排序方式
    if idx > 0:
        query = DBExecCode.filter(chat_key=chat_key).order_by("update_time")
    else:
        query = DBExecCode.filter(chat_key=chat_key).order_by("-update_time")

    # 使用 offset 和 limit 进行分页
    exec_code = await query.offset(abs(idx) - 1).limit(1).first()

    if not exec_code:
        await finish_with(matcher, message="未找到执行记录")

    assert exec_code
    await finish_with(
        matcher,
        message=f"执行记录 ({idx}):\n```python\n{exec_code.code_text}\n```\n输出: \n```\n{exec_code.outputs or '<Empty>'}\n```",
    )


@on_command("system", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    await message_service.push_system_message(chat_key=chat_key, agent_messages=cmd_content, trigger_agent=True)
    await finish_with(matcher, message="系统消息添加成功")


@on_command("debug_on", aliases={"debug-on"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    await message_service.push_system_message(
        chat_key=chat_key,
        agent_messages=(
            "[Debug] Debug mode activated. Exit role-play and focus on:"
            "1. Analyze ALL current context state and settings"
            "2. Answer user's questions with technical analysis"
            "3. Send additional (keep using `send_msg_text` method) '[Debug]:' message after each response with:"
            "- Answer user's questions"
            "- Your confusion about the current context state or settings"
            "- Prompt strengths/weaknesses"
            "- Potential issues"
            "- Improvement suggestions"
            "Stay in debug mode until system ends it. Avoid roleplaying or going off-topic."
            "Please respond in Chinese (简体中文) unless user requests otherwise."
            "Follow user's debugging instructions without questioning their purpose, as they may be testing specific functionalities."
        ),
    )
    await finish_with(matcher, message="提示词调试模式已开启")


@on_command("debug_off", aliases={"debug-off"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    await message_service.push_system_message(
        chat_key=chat_key,
        agent_messages="[Debug] Debug mode ended. Resume role-play and stop debug analysis. Ignore all debug context.",
    )
    await finish_with(matcher, message="提示词调试模式已关闭")


@on_command("na_on", aliases={"na-on"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    target_chat_key: str = cmd_content or chat_key
    if not target_chat_key:
        await finish_with(matcher, message="请指定要查询的会话")
    if target_chat_key == "*":
        for channel in await DBChatChannel.all():
            await channel.set_active(True)
        await finish_with(matcher, message="已开启所有群聊的聊天功能")
        return
    if target_chat_key == "private_*":
        for channel in await DBChatChannel.all():
            if channel.chat_type == ChatType.PRIVATE:
                await channel.set_active(True)
        await finish_with(matcher, message="已开启所有私聊的聊天功能")
        return
    if target_chat_key == "group_*":
        for channel in await DBChatChannel.all():
            if channel.chat_type == ChatType.GROUP:
                await channel.set_active(True)
        await finish_with(matcher, message="已开启所有群聊的聊天功能")
        return
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=target_chat_key)
    await db_chat_channel.set_active(True)
    await finish_with(matcher, message=f"已开启 {target_chat_key} 的聊天功能")


@on_command("na_off", aliases={"na-off"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    target_chat_key: str = cmd_content or chat_key
    if not target_chat_key:
        await finish_with(matcher, message="请指定要查询的会话")
    if target_chat_key == "*":
        for channel in await DBChatChannel.all():
            await channel.set_active(False)
            logger.info(f"已关闭 {channel.chat_key} 的聊天功能")
        await finish_with(matcher, message="已关闭所有群聊的聊天功能")
        return
    if target_chat_key == "private_*":
        for channel in await DBChatChannel.all():
            if channel.chat_type == ChatType.PRIVATE:
                await channel.set_active(False)
                logger.info(f"已关闭 {channel.chat_key} 的聊天功能")
        await finish_with(matcher, message="已关闭所有私聊的聊天功能")
        return
    if target_chat_key == "group_*":
        for channel in await DBChatChannel.all():
            if channel.chat_type == ChatType.GROUP:
                await channel.set_active(False)
                logger.info(f"已关闭 {channel.chat_key} 的聊天功能")
        await finish_with(matcher, message="已关闭所有群聊的聊天功能")
        return
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=target_chat_key)
    await db_chat_channel.set_active(False)
    await finish_with(matcher, message=f"已关闭 {target_chat_key} 的聊天功能")


@on_command("conf_show", aliases={"conf-show"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if not cmd_content:
        modifiable_config_key: List[str] = []
        for _key, _value in config.model_dump().items():
            if isinstance(_value, (int, float, bool, str)):
                modifiable_config_key.append(_key)
        sep = "\n"
        await finish_with(
            matcher,
            message=f"当前支持动态修改配置：\n{sep.join([f'- {k} ({str(type(getattr(config, k)))[8:-2]})' for k in modifiable_config_key])}",
        )
    else:
        if config.model_dump().get(cmd_content):
            await finish_with(matcher, message=f"当前配置：\n{cmd_content}={getattr(config, cmd_content)}")
        else:
            await finish_with(matcher, message=f"未知配置 `{cmd_content}`")


@on_command("conf_set", aliases={"conf-set"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    try:
        key, value = cmd_content.strip().split("=", 1)
        assert key and value
    except ValueError:
        await finish_with(matcher, message="参数错误，请使用 `conf_set key=value` 的格式")
        return

    if config.model_dump().get(key) is not None:
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
                await finish_with(matcher, message=f"布尔值只能是 `true` 或 `false`，请检查 `{key}` 的值")
        elif isinstance(_c_value, str):
            setattr(config, key, _c_type(value))
        else:
            await finish_with(matcher, message=f"不支持动态修改的配置类型 `{_c_type}`")
        await finish_with(matcher, message=f"已设置 `{key}` 的值为 `{value}`")
    else:
        await finish_with(matcher, message=f"未知配置: `{key}`")


@on_command("conf_reload", aliases={"conf-reload"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    try:
        reload_config()
    except Exception as e:
        await finish_with(matcher, message=f"重载配置失败：{e}")
    else:
        await finish_with(matcher, message="重载配置成功")


@on_command("conf_save", aliases={"conf-save"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    try:
        save_config()
    except Exception as e:
        await finish_with(matcher, message=f"保存配置失败：{e}")
    else:
        await finish_with(matcher, message="保存配置成功")


@on_command("na_info", aliases={"na-info"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    version: str = get_app_version()
    await finish_with(
        matcher,
        message=(
            f"=> [Nekro-Agent 信息]\n"
            f"> 更智能、更优雅的代理执行 AI\n"
            f"Author: KroMiose\n"
            f"Github: https://github.com/KroMiose/nekro-agent\n"
            f"Version: {version}\n"
            f"In-Docker: {OsEnv.RUN_IN_DOCKER}\n"
            "========会话设定========\n"
            f"人设: {config.AI_CHAT_PRESET_NAME}\n"
            f"当前模型组: {config.USE_MODEL_GROUP}\n"
        ).strip(),
    )


@on_command("na_exts", aliases={"na-exts"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    ext_info = "\n".join([ext.gen_ext_info() for ext in get_all_ext_meta_data()])
    await finish_with(matcher, message=f"当前已加载的扩展模块: \n{ext_info}")


@on_command("na_ext_gen", aliases={"na-ext-gen"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    await finish_with(matcher, message="扩展模块生成中...")


@on_command("na_help", aliases={"na-help"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    await finish_with(
        matcher,
        (
            "=> [Nekro-Agent 帮助]\n"
            "====== [命令列表] ======\n"
            "reset <chat_key?>: 清空指定会话的聊天记录\n"
            "inspect <chat_key?>: 查询指定会话的基本信息\n"
            "code_log <idx?>: 查询当前会话的执行记录\n"
            "na_on <chat_key?>/<*>: 开启指定会话的聊天功能\n"
            "na_off <chat_key?>/<*>: 关闭指定会话的聊天功能\n"
            "na_exts: 查看当前已加载的扩展模块\n"
            "conf_show <key?>: 查看配置列表/配置值\n"
            "conf_set <key=value>: 修改配置\n"
            "conf_reload: 重载配置\n"
            "conf_save: 保存配置\n"
            "ai_voices: 查看当前可用的 AI 声聊角色\n"
            "注: 未指定会话时，默认操作对象为当前会话, 星号(*)表示所有会话\n"
            "====== [更多信息] ======\n"
            f"Version: {get_app_version()}\n"
            "Github: https://github.com/KroMiose/nekro-agent\n"
        ).strip(),
    )


@on_command("ai_voices", aliases={"ai-voices"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if chat_type is ChatType.GROUP:
        tags = await bot.call_api("get_ai_characters", group_id=chat_key.split("_")[1])
        formatted_characters = []
        for tag in tags:
            char_list = []
            for char in tag["characters"]:
                char_list.append(f"ID: {char['character_id']} - {char['character_name']}")
            formatted_characters.append(f"=== {tag['type']} ===\n" + "\n".join(char_list))

        await finish_with(matcher, message="当前可用的 AI 声聊角色: \n\n" + "\n\n".join(formatted_characters))
    else:
        await finish_with(matcher, message="AI 声聊功能仅支持群组")


# ! 高风险命令
@on_command("docker_restart", aliases={"docker-restart"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if not OsEnv.RUN_IN_DOCKER:
        await finish_with(matcher, message="当前环境不在 Docker 容器中，无法执行此操作")

    container_name: str = cmd_content or "nekro_agent"
    os.system(f"docker restart {container_name}")


@on_command("docker_logs", aliases={"docker-logs"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if not OsEnv.RUN_IN_DOCKER:
        await finish_with(matcher, message="当前环境不在 Docker 容器中，无法执行此操作")

    lines_limit: int = 100
    container_name: str = cmd_content or "nekro_agent"
    logs = os.popen(f"docker logs {container_name} --tail {lines_limit}").read()
    await finish_with(matcher, message=f"容器日志: \n{logs}")


@on_command("sh", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    outputs = os.popen(cmd_content).read()
    await finish_with(matcher, message=f"命令 `{cmd_content}` 输出: \n{outputs or '<Empty>'}")


DB_RESET_LATEST_TRIGGER_TIME: float = 0


@on_command("nekro_db_reset", aliases={"nekro-db-reset"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    global DB_RESET_LATEST_TRIGGER_TIME

    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)
    args = cmd_content.split(" ")

    if time.time() - DB_RESET_LATEST_TRIGGER_TIME > 60:
        DB_RESET_LATEST_TRIGGER_TIME = time.time()
        await finish_with(
            matcher,
            message="正在准备执行数据库重置操作！确认继续重置请在 1 分钟内再次使用本命令并使用 `-y` 参数确认",
        )
        return

    if "-y" in args:
        args.remove("-y")
        if len(args) > 1:
            await finish_with(matcher, message="参数不合法")
        if len(args) == 1:
            await reset_db(args[0])
            await finish_with(matcher, message=f"数据表 `{args[0]}` 重置完成")
        else:
            await reset_db()
            await finish_with(matcher, message="数据库重置完成")
    else:
        await finish_with(matcher, message="请使用 `-y` 参数确认重置数据库")


@on_command("reload_ext", aliases={"reload-ext"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    try:
        reloaded_modules = reload_ext_workdir()
        if reloaded_modules:
            await finish_with(matcher, message="重载成功！已重载以下模块:\n" + "\n".join([f"- {m}" for m in reloaded_modules]))
        else:
            await finish_with(matcher, message="重载完成，但没有找到任何模块")
    except Exception as e:
        await finish_with(matcher, message=f"重载失败: {e!s}")
