import json
import os
import re
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from nekro_agent.core.config import ModelConfigGroup, config, reload_config, save_config
from nekro_agent.core.database import reset_db
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import (
    PROMPT_ERROR_LOG_DIR,
    SANDBOX_PACKAGE_DIR,
    SANDBOX_PIP_CACHE_DIR,
    OsEnv,
)
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_exec_code import DBExecCode
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.agent.openai import OpenAIResponse, gen_openai_chat_response
from nekro_agent.services.agent.resolver import ParsedCodeRunData
from nekro_agent.services.message_service import message_service
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.plugin.schema import SandboxMethodType
from nekro_agent.services.sandbox.runner import limited_run_code
from nekro_agent.systems.cloud.api.auth import check_official_repos_starred
from nekro_agent.systems.cloud.api.telemetry import send_telemetry_report
from nekro_agent.tools.common_util import get_app_version

from .guard import command_guard, finish_with, reset_command_guard


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
    preset = await db_chat_channel.get_preset()
    info = f"基本人设: {preset.name}\n"
    await finish_with(matcher, message=f"频道 {target_chat_key} 信息：\n{info.strip()}")


@on_command("exec", priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    result, _, _ = await limited_run_code(
        ParsedCodeRunData(raw_content=cmd_content, code_content=cmd_content, thought_chain=""),
        from_chat_key=chat_key,
    )

    await finish_with(matcher, result or "<Empty Output>")


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
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher, trigger_on_off=True)

    target_chat_key: str = cmd_content or chat_key
    if not target_chat_key:
        await finish_with(matcher, message="请指定要查询的会话")
    if target_chat_key == "*":
        for channel in await DBChatChannel.all():
            await channel.set_active(True)
        await finish_with(matcher, message="已开启所有群聊的聊天功能")
    if target_chat_key == "private_*":
        for channel in await DBChatChannel.all():
            if channel.chat_type == ChatType.PRIVATE:
                await channel.set_active(True)
        await finish_with(matcher, message="已开启所有私聊的聊天功能")
    if target_chat_key == "group_*":
        for channel in await DBChatChannel.all():
            if channel.chat_type == ChatType.GROUP:
                await channel.set_active(True)
        await finish_with(matcher, message="已开启所有群聊的聊天功能")
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

    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
    preset = await db_chat_channel.get_preset()

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
            f"人设: {preset.name}\n"
            f"当前模型组: {config.USE_MODEL_GROUP}\n"
        ).strip(),
    )


@on_command("na_plugins", aliases={"na-plugins", "nps"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    plugins = plugin_collector.get_all_plugins()

    if not plugins:
        await finish_with(matcher, message="当前没有已加载的插件")
        return

    plugin_info_parts = []

    for plugin in plugins:
        # 获取插件基本信息
        plugin_name = plugin.name
        plugin_desc = plugin.description
        plugin_version = plugin.version
        plugin_author = plugin.author
        plugin_url = plugin.url
        plugin_status = "已启用" if plugin.is_enabled else "已禁用"

        # 获取插件功能统计
        sandbox_methods_count = len(plugin.sandbox_methods)
        has_prompt_inject = "是" if plugin.prompt_inject_method else "否"
        webhook_methods_count = len(plugin.webhook_methods)

        # 格式化插件信息
        plugin_info = (
            f"* {plugin_name} - v{plugin_version} ({plugin_status})\n"
            f"作者: {plugin_author}\n"
            f"说明: {plugin_desc}\n"
            f"链接: {plugin_url}\n"
            f"功能: 沙盒方法({sandbox_methods_count}), 提示注入({has_prompt_inject}), Webhook({webhook_methods_count})"
        )

        plugin_info_parts.append(plugin_info)

    # 组合所有插件信息
    all_plugin_info = "\n\n".join(plugin_info_parts)

    # 添加统计信息
    stats = f"共加载 {len(plugins)} 个插件"

    await finish_with(matcher, message=f"当前已加载的插件: \n{all_plugin_info}\n\n{stats}")


@on_command("plugin_info", aliases={"plugin-info", "npi"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if not cmd_content:
        await finish_with(matcher, message="请指定要查询的插件名或插件键名 (plugin_info <plugin_name/key>)")
        return

    plugins = plugin_collector.get_all_plugins()
    target_plugin = None
    search_term = cmd_content.strip()

    # 分步骤查找插件，优先级从高到低:
    # 1. 键名完全匹配（区分大小写）
    for plugin in plugins:
        if plugin.key == search_term:
            target_plugin = plugin
            break

    # 2. 键名完全匹配（不区分大小写）
    if not target_plugin:
        for plugin in plugins:
            if plugin.key.lower() == search_term.lower():
                target_plugin = plugin
                break

    # 3. 插件名完全匹配（区分大小写）
    if not target_plugin:
        for plugin in plugins:
            if plugin.name == search_term:
                target_plugin = plugin
                break

    # 4. 插件名完全匹配（不区分大小写）
    if not target_plugin:
        for plugin in plugins:
            if plugin.name.lower() == search_term.lower():
                target_plugin = plugin
                break

    # 5. 键名部分匹配
    if not target_plugin:
        for plugin in plugins:
            if search_term.lower() in plugin.key.lower():
                target_plugin = plugin
                break

    # 6. 插件名部分匹配
    if not target_plugin:
        for plugin in plugins:
            if search_term.lower() in plugin.name.lower():
                target_plugin = plugin
                break

    if not target_plugin:
        # 提供匹配建议
        suggestions = []
        for plugin in plugins:
            if any(
                c.lower() in plugin.key.lower() or c.lower() in plugin.name.lower() for c in search_term.lower() if c.isalnum()
            ):
                suggestions.append(f"- {plugin.name} (键名: {plugin.key})")

        suggestion_text = ""
        if suggestions:
            suggestion_text = "\n\n您可能想查找的插件:\n" + "\n".join(suggestions[:3])
            if len(suggestions) > 3:
                suggestion_text += f"\n...等共 {len(suggestions)} 个可能的匹配"

        await finish_with(
            matcher,
            message=f"未找到插件: {search_term}\n提示: 使用 `na_plugins` 命令查看所有已加载的插件{suggestion_text}",
        )
        return

    # 基本信息
    info = [
        f"=> [{target_plugin.name}] 插件详情",
        f"版本: v{target_plugin.version} ({'已启用' if target_plugin.is_enabled else '已禁用'})",
        f"键名: {target_plugin.key}",
        f"作者: {target_plugin.author}",
        f"说明: {target_plugin.description}",
        f"链接: {target_plugin.url}",
        "",
        "===== 功能统计 =====",
        f"沙盒方法: {len(target_plugin.sandbox_methods)}",
        f"提示注入: {'有' if target_plugin.prompt_inject_method else '无'}",
        f"Webhook: {len(target_plugin.webhook_methods)}",
    ]

    # 配置信息
    try:
        plugin_config = target_plugin.get_config()
        config_items = plugin_config.model_dump()
        if config_items:
            info.append("")
            info.append("===== 配置信息 =====")
            for key, value in config_items.items():
                info.append(f"{key}: {value}")
    except Exception as e:
        info.append("")
        info.append(f"获取配置失败: {e}")

    # 方法列表
    if target_plugin.sandbox_methods:
        info.append("")
        info.append("===== 方法列表 =====")
        for method in target_plugin.sandbox_methods:
            method_type_str = {
                SandboxMethodType.AGENT: "代理方法",
                SandboxMethodType.MULTIMODAL_AGENT: "多模态代理",
                SandboxMethodType.TOOL: "工具方法",
                SandboxMethodType.BEHAVIOR: "行为方法",
            }.get(method.method_type, "未知类型")
            info.append(f"- {method.func.__name__} ({method_type_str}): {method.name}")

    await finish_with(matcher, message="\n".join(info))


@on_command("reset_plugin", aliases={"reset-plugin"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if not cmd_content:
        await finish_with(matcher, message="请指定要重置的插件名或插件键名 (reset_plugin <plugin_name/key>)")
    else:
        plugins = plugin_collector.get_all_plugins()
        target_plugin = None
        search_term = cmd_content.strip()

        # 分步骤查找插件，优先级从高到低:
        # 1. 键名完全匹配（区分大小写）
        for plugin in plugins:
            if plugin.key == search_term:
                target_plugin = plugin
                break

        # 2. 键名完全匹配（不区分大小写）
        if not target_plugin:
            for plugin in plugins:
                if plugin.key.lower() == search_term.lower():
                    target_plugin = plugin
                    break

        # 3. 插件名完全匹配（区分大小写）
        if not target_plugin:
            for plugin in plugins:
                if plugin.name == search_term:
                    target_plugin = plugin
                    break

        # 4. 插件名完全匹配（不区分大小写）
        if not target_plugin:
            for plugin in plugins:
                if plugin.name.lower() == search_term.lower():
                    target_plugin = plugin
                    break

        if not target_plugin:
            await finish_with(matcher, message=f"未找到插件: {search_term}")
            return

        config_path = target_plugin._plugin_config_path  # noqa: SLF001
        if config_path.exists():
            config_path.unlink()
            await finish_with(matcher, message=f"插件 {target_plugin.name} 配置文件已删除")
        else:
            await finish_with(matcher, message=f"插件 {target_plugin.name} 配置文件不存在")


@on_command("na_help", aliases={"na-help"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    await finish_with(
        matcher,
        (
            "=> [Nekro-Agent 帮助]\n"
            "na_info: 查看系统信息\n"
            "====== [聊天管理] ======\n"
            "reset <chat_key?>: 清空指定会话的聊天记录\n"
            "na_on <chat_key?>/<*>: 开启指定会话的聊天功能\n"
            "na_off <chat_key?>/<*>: 关闭指定会话的聊天功能\n"
            "\n====== [插件系统] ======\n"
            "na_plugins: 查看当前已加载的插件及其详细信息\n"
            "plugin_info <name/key>: 查看指定插件的详细信息\n"
            "\n====== [系统维护] ======\n"
            "clear_sandbox_cache: 清理沙盒环境的缓存和包目录\n"
            "debug_on: 开启调试模式\n"
            "debug_off: 关闭调试模式\n"
            "system <message>: 添加系统消息\n"
            "model_test <model_name1> ...: 测试模型可达性\n"
            "\n====== [错误日志管理] ======\n"
            "log_err_list [-p <页码>] [-s <每页数量>]: 查看最近错误日志\n"
            "log_err_list -a/--all: 查看全部日志目录文件\n"
            "log_chat_test <日志索引/文件名> [-g <模型组名>]: 测试错误日志\n"
            "\n注: 未指定会话时，默认操作对象为当前会话, 星号(*)表示所有会话\n"
            "====== [更多信息] ======\n"
            f"Version: {get_app_version()}\n"
            "Github: https://github.com/KroMiose/nekro-agent\n"
        ).strip(),
    )


@on_command("telemetry_report", aliases={"telemetry-report"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    """手动触发遥测数据提交（用于调试）"""
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)
    # 获取当前时间和上一个整点时间
    now = datetime.now()
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    prev_hour = current_hour - timedelta(hours=1)

    # 上报上一个小时的数据
    response = await send_telemetry_report(prev_hour, current_hour)
    if response.success:
        await finish_with(matcher, message=f"遥测数据上报成功: {prev_hour} - {current_hour}")
    else:
        await finish_with(matcher, message=f"遥测数据上报失败: {response.message}")


@on_command("model_test", aliases={"model-test"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    model_names = cmd_content.strip().split()
    if "-g" in model_names:
        model_names.remove("-g")
        use_group_name = True
    else:
        use_group_name = False

    if "--stream" in model_names:
        stream_mode = True
        model_names.remove("--stream")
    else:
        stream_mode = False

    if "--use-system" in model_names:
        use_system = True
        model_names.remove("--use-system")
    else:
        use_system = False

    if not model_names:
        await finish_with(matcher, message="请指定要测试的模型名 (model_test <model_name1> <model_name2> ...)")

    test_model_groups: List[ModelConfigGroup] = []
    if use_group_name:
        # 处理模型组名称的通配符匹配
        for group_name in model_names:
            if "*" in group_name:
                pattern = group_name.replace("*", ".*")

                matching_groups = [g for g in config.MODEL_GROUPS if re.match(pattern, g)]
                test_model_groups.extend(
                    [config.MODEL_GROUPS[g] for g in matching_groups if config.MODEL_GROUPS[g].MODEL_TYPE == "chat"],
                )
            elif group_name in config.MODEL_GROUPS:
                if config.MODEL_GROUPS[group_name].MODEL_TYPE == "chat":
                    test_model_groups.append(config.MODEL_GROUPS[group_name])
    else:
        # 处理模型名称的通配符匹配
        for model_name in model_names:
            if "*" in model_name:
                pattern = model_name.replace("*", ".*")

                matching_groups = [
                    g for g in config.MODEL_GROUPS.values() if g.MODEL_TYPE == "chat" and re.match(pattern, g.CHAT_MODEL)
                ]
                test_model_groups.extend(matching_groups)
            else:
                matching_groups = [
                    g for g in config.MODEL_GROUPS.values() if model_name == g.CHAT_MODEL and g.MODEL_TYPE == "chat"
                ]
                test_model_groups.extend(matching_groups)

    if not test_model_groups:
        await finish_with(matcher, message="未找到符合条件的模型组")

    await matcher.send(f"正在准备测试 {len(test_model_groups)} 个模型组...")

    model_test_success_result_map: Dict[str, int] = {}
    model_test_fail_result_map: Dict[str, int] = {}
    model_speed_map: Dict[str, List[float]] = {}

    for model_group in test_model_groups:
        if model_group.CHAT_MODEL not in model_test_success_result_map:
            model_test_success_result_map[model_group.CHAT_MODEL] = 0
        if model_group.CHAT_MODEL not in model_test_fail_result_map:
            model_test_fail_result_map[model_group.CHAT_MODEL] = 0
        if model_group.CHAT_MODEL not in model_speed_map:
            model_speed_map[model_group.CHAT_MODEL] = []

        try:
            start_time = time.time()
            messages = [{"role": "user", "content": "Repeat the following text without any thinking or explanation: Test"}]
            if use_system:
                messages.insert(
                    0,
                    {"role": "system", "content": "You are a helpful assistant that follows instructions precisely."},
                )
            llm_response: OpenAIResponse = await gen_openai_chat_response(
                model=model_group.CHAT_MODEL,
                messages=messages,
                base_url=model_group.BASE_URL,
                api_key=model_group.API_KEY,
                stream_mode=stream_mode,
                proxy_url=model_group.CHAT_PROXY,
            )
            end_time = time.time()
            assert llm_response.response_content
            model_test_success_result_map[model_group.CHAT_MODEL] += 1
            model_speed_map[model_group.CHAT_MODEL].append(end_time - start_time)
        except Exception as e:
            logger.error(f"测试 {model_group.CHAT_MODEL} 失败: {e}")
            model_test_fail_result_map[model_group.CHAT_MODEL] += 1

    # 构建测试结果输出
    result_lines = ["=> [模型测试结果]"]
    for model_name in set(list(model_test_success_result_map.keys()) + list(model_test_fail_result_map.keys())):
        success = model_test_success_result_map.get(model_name, 0)
        fail = model_test_fail_result_map.get(model_name, 0)
        status = "✅ 通过" if success > 0 and fail == 0 else "❌ 失败" if fail > 0 else "⚠️ 未知"

        # 添加速度信息
        speed_info = ""
        if model_speed_map.get(model_name):
            speeds = model_speed_map[model_name]
            avg_speed = sum(speeds) / len(speeds)
            if len(speeds) > 1:
                min_speed = min(speeds)
                max_speed = max(speeds)
                speed_info = f" | 速度: {avg_speed:.2f}s (最快: {min_speed:.2f}s, 最慢: {max_speed:.2f}s)"
            else:
                speed_info = f" | 速度: {avg_speed:.2f}s"

        result_lines.append(f"{status} {model_name}: (成功: {success}, 失败: {fail}){speed_info}")

    await finish_with(matcher, message="\n".join(result_lines))


@on_command("clear_sandbox_cache", aliases={"clear-sandbox-cache", "na_csc", "na-csc"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    """清理沙盒环境的缓存目录"""
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    cleared_size = 0
    cleared_files = 0

    # 清理 pip 缓存目录
    pip_cache_path = Path(SANDBOX_PIP_CACHE_DIR)
    if pip_cache_path.exists():
        for root, _, files in os.walk(SANDBOX_PIP_CACHE_DIR):
            root_path = Path(root)
            for file in files:
                file_path = root_path / file
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleared_size += file_size
                    cleared_files += 1
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path}: {e}")

        # 清空目录但保留目录本身
        for item in pip_cache_path.iterdir():
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                except Exception as e:
                    logger.error(f"删除目录失败 {item}: {e}")

    # 清理包目录
    package_path = Path(SANDBOX_PACKAGE_DIR)
    if package_path.exists():
        for root, _, files in os.walk(SANDBOX_PACKAGE_DIR):
            root_path = Path(root)
            for file in files:
                file_path = root_path / file
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleared_size += file_size
                    cleared_files += 1
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path}: {e}")

        # 清空目录但保留目录本身
        for item in package_path.iterdir():
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                except Exception as e:
                    logger.error(f"删除目录失败 {item}: {e}")

    # 创建目录（如果不存在）
    Path(SANDBOX_PIP_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    Path(SANDBOX_PACKAGE_DIR).mkdir(parents=True, exist_ok=True)

    size_in_mb = cleared_size / (1024 * 1024)
    await finish_with(
        matcher,
        message=f"沙盒缓存清理完成！\n已清理文件：{cleared_files} 个\n释放空间：{size_in_mb:.2f} MB",
    )


@on_command("github_stars_check", aliases={"github-stars-check"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    """检查用户是否已Star官方GitHub仓库"""
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    try:
        result = await check_official_repos_starred()

        if not result.success:
            await finish_with(matcher, message=f"检查GitHub Star状态失败: {result.message}")

        if not result.data:
            await finish_with(matcher, message="获取Star状态数据为空")

        # 构建响应消息
        starred = ", ".join(result.data.starred_repositories) if result.data.starred_repositories else "无"
        unstarred = ", ".join(result.data.unstarred_repositories) if result.data.unstarred_repositories else "无"
        status = "已Star所有官方仓库" if result.data.all_starred else "还有未Star的官方仓库"

        message = f"=> [GitHub Star 状态]\n状态: {status}\n已Star: {starred}\n未Star: {unstarred}"

    except Exception as e:
        logger.error(f"检查GitHub Star状态时发生错误: {e}")
        await finish_with(matcher, message=f"执行失败: {e}")
    else:
        await finish_with(matcher, message=message)


@on_command("log_err_list", aliases={"log-err-list", "log_err_ls", "log-err-ls"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    """查看错误日志列表"""
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    from nekro_agent.services.agent.run_agent import RECENT_ERR_LOGS

    # 解析参数，支持分页
    args = cmd_content.strip().split()
    page = 1
    page_size = 10
    use_dir_files = False

    for i, _arg in enumerate(args):
        if _arg == "-p" and i + 1 < len(args):
            try:
                page = int(args[i + 1])
            except ValueError:
                await finish_with(matcher, message="⚠️ 分页参数格式错误")
        elif _arg == "-s" and i + 1 < len(args):
            try:
                page_size = int(args[i + 1])
            except ValueError:
                await finish_with(matcher, message="⚠️ 每页显示数量参数格式错误")
        elif _arg == "-a" or _arg == "--all":
            use_dir_files = True

    # 确保页码和页大小合法
    page = max(1, page)
    page_size = max(1, min(50, page_size))

    # 获取所有错误日志
    if use_dir_files:
        # 从错误日志目录读取所有文件
        log_dir = Path(PROMPT_ERROR_LOG_DIR)
        if not log_dir.exists():
            await finish_with(matcher, message="⚠️ 错误日志目录不存在")

        all_logs = []
        for file_path in log_dir.glob("*.json"):
            all_logs.append(file_path)

        # 按修改时间从新到旧排序
        logs = sorted(all_logs, key=lambda p: p.stat().st_mtime, reverse=True)
    else:
        # 使用缓存的最近日志列表，从新到旧排序
        logs = list(RECENT_ERR_LOGS)

    total_logs = len(logs)
    total_pages = (total_logs + page_size - 1) // page_size if total_logs > 0 else 1

    # 确保页码不超过总页数
    page = min(page, total_pages)

    # 计算当前页的日志
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_logs)
    current_page_logs = logs[start_idx:end_idx]

    # 构建响应消息
    if not current_page_logs:
        await finish_with(matcher, message="📭 没有错误日志记录")

    result_lines = [f"📋 错误日志列表 (第 {page}/{total_pages} 页，共 {total_logs} 条):"]

    for i, log_path in enumerate(current_page_logs, start=start_idx + 1):
        # 获取文件修改时间
        try:
            mod_time = datetime.fromtimestamp(log_path.stat().st_mtime).strftime("%m-%d %H:%M:%S")
            result_lines.append(f"{i}. 📄 [{mod_time}] {log_path.name}")
        except:
            result_lines.append(f"{i}. 📄 {log_path.name}")

    result_lines.append("\n🔍 使用方法:")
    result_lines.append("log_err_list -p <页码> -s <每页数量>: 查看最近错误日志列表")
    result_lines.append("log_err_list -a/--all: 查看错误日志目录中的所有日志文件")
    result_lines.append("log_chat_test <日志索引/文件名> [-g <模型组名>] [--stream]: 使用错误日志内容测试请求")

    await finish_with(matcher, message="\n".join(result_lines))


@on_command("log_chat_test", aliases={"log-chat-test"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    """使用错误日志中的对话测试LLM请求"""
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    from nekro_agent.services.agent.run_agent import RECENT_ERR_LOGS

    # 解析参数
    args = cmd_content.strip().split()
    if not args:
        await finish_with(matcher, message="⚠️ 请指定要测试的日志索引或文件名")

    log_identifier = args[0]
    model_group_name = config.USE_MODEL_GROUP  # 默认使用主模型组
    use_stream_mode = False  # 是否使用流式请求

    # 检查是否指定了模型组或流式模式
    i = 1
    while i < len(args):
        if args[i] == "-g" and i + 1 < len(args):
            model_group_name = args[i + 1]
            i += 2
        elif args[i] == "--stream" or args[i] == "-s":
            use_stream_mode = True
            i += 1
        else:
            i += 1

    # 验证模型组是否存在
    if model_group_name not in config.MODEL_GROUPS:
        await finish_with(matcher, message=f"⚠️ 指定的模型组 '{model_group_name}' 不存在")

    model_group = config.MODEL_GROUPS[model_group_name]

    # 查找目标日志文件
    log_path = None
    try:
        # 尝试作为索引解析
        idx = int(log_identifier) - 1
        logs = list(RECENT_ERR_LOGS)
        if 0 <= idx < len(logs):
            log_path = logs[idx]
    except ValueError:
        # 尝试作为文件名匹配队列中的文件
        for p in RECENT_ERR_LOGS:
            if log_identifier == p.name:
                log_path = p
                break

        # 如果仍未找到，尝试直接在错误日志目录中查找
        if not log_path:
            direct_path = Path(PROMPT_ERROR_LOG_DIR) / log_identifier
            if direct_path.exists() and direct_path.is_file():
                log_path = direct_path

    if not log_path and not log_identifier.endswith(".json"):
        direct_path = Path(PROMPT_ERROR_LOG_DIR) / f"{log_identifier}.json"
        if direct_path.exists() and direct_path.is_file():
            log_path = direct_path

    if not log_path:
        await finish_with(
            matcher,
            message=f"⚠️ 未找到指定的日志: {log_identifier}\n提示: 可以使用log_err_list命令查看最近的错误日志，或直接指定错误日志目录中的文件名",
        )

    # 检查日志文件是否存在
    if not log_path.exists():
        await finish_with(matcher, message=f"⚠️ 日志文件不存在: {log_path.name}")

    # 读取日志文件内容
    try:
        log_content = log_path.read_text(encoding="utf-8")
        log_data = json.loads(log_content)
    except Exception as e:
        await finish_with(matcher, message=f"⚠️ 解析日志文件失败: {e}")

    # 从日志中提取messages
    try:
        messages = log_data["request"]["messages"]
    except KeyError:
        # 尝试旧格式
        try:
            messages = log_data.get("messages", [])
            if not messages:
                await finish_with(matcher, message=f"⚠️ 日志中未找到有效的对话内容: {log_path.name}")
        except (KeyError, AttributeError):
            await finish_with(matcher, message=f"⚠️ 日志格式不合法或未找到有效的对话内容: {log_path.name}")

    # 测试前的提示信息
    stream_info = "（流式模式）" if use_stream_mode else ""
    testing_message = (
        f"🚀 正在使用 {model_group.CHAT_MODEL} ({model_group_name}) {stream_info}\n测试请求日志: {log_path.name}..."
    )
    await matcher.send(testing_message)

    # 发起测试请求
    start_time = time.time()
    try:
        llm_response: OpenAIResponse = await gen_openai_chat_response(
            model=model_group.CHAT_MODEL,
            messages=messages,
            base_url=model_group.BASE_URL,
            api_key=model_group.API_KEY,
            stream_mode=use_stream_mode,
            proxy_url=model_group.CHAT_PROXY,
            max_wait_time=config.AI_GENERATE_TIMEOUT,
        )
        end_time = time.time()

        # 获取响应总长度
        total_length = len(llm_response.response_content)

        # 截取响应结果的前 64 个字符
        preview = (
            llm_response.response_content[:64] + "..."
            if len(llm_response.response_content) > 64
            else llm_response.response_content
        )

        # 构建响应消息
        elapsed = end_time - start_time
        # 根据响应时间添加不同的emoji
        speed_emoji = "⚡" if elapsed < 1 else "🚀" if elapsed < 3 else "🏃" if elapsed < 5 else "🐢"

        # 根据长度选择emoji
        length_emoji = "📏" if total_length < 100 else "📊" if total_length < 500 else "📜" if total_length < 2000 else "📚"

        result_message = (
            f"🟢 测试成功！\n"
            f"📊 测试结果:\n"
            f"- 模型: {model_group.CHAT_MODEL}\n"
            f"- 流式模式: {use_stream_mode}\n"
            f"- 耗时: {speed_emoji} {elapsed:.2f}s\n"
            f"- 响应预览:\n{preview}\n======\n"
            f"响应总长度: {length_emoji} {total_length} 字符\n"
        )

    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time

        safe_error: str = str(e).replace(model_group.API_KEY, "[API_KEY]").replace(model_group.BASE_URL, "[BASE_URL]")

        await finish_with(
            matcher,
            message=(
                f"🔴 测试失败！\n"
                f"📊 测试结果:\n"
                f"- 模型: {model_group.CHAT_MODEL}\n"
                f"- 流式模式: {use_stream_mode}\n"
                f"- 耗时: {elapsed:.2f}s\n"
                f"- 错误信息: {safe_error!s}"
            ),
        )
    else:
        await finish_with(matcher, message=result_message)


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
