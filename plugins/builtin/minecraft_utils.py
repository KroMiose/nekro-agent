"""
# Minecraft 工具集 (Minecraft Utils)

为 `Minecraft` 适配器提供一系列专属的增强功能，允许 AI 与游戏服务器进行深度交互。

## 主要功能

- **发送富文本消息**: AI 可以构建一种特殊的 JSON 格式消息，在游戏中显示带有颜色、样式（粗体、斜体）、点击事件（如打开网页、执行命令）和悬停提示的复杂文本。这可以用来创建交互式公告、任务指引等。
- **执行 RCON 命令**: AI 能够通过 RCON 协议直接向 Minecraft 服务器发送指令。这意味着 AI 可以像一个游戏管理员（OP）一样，执行诸如 `/weather clear` (改变天气)、`/give` (给予物品)、`/tp` (传送玩家) 等各种原版指令。

## 使用方法

此插件的所有工具都是为 AI 自动调用而设计的，用户无需手动操作。AI 会根据需要与 Minecraft 服务器进行交互：

- 当需要发送复杂的交互式信息时，AI 会构造富文本并调用 `send_rich_text`。
- 当需要改变游戏世界的状态或与玩家互动时，AI 会调用 `execute_rcon_commands` 来执行相应的指令。

通过这个插件，AI 可以在很大程度上成为一个合格的 Minecraft 服务器"服主"或"游戏管理员"。
"""

import json
from typing import Any, Dict, List, Optional

from nonebot.adapters.minecraft import Bot, Message, MessageSegment
from nonebot.adapters.minecraft.models import (
    ClickAction,
    ClickEvent,
    Color,
    Component,
    HoverAction,
    HoverEvent,
)

from nekro_agent.adapters.minecraft.core.bot import get_bot
from nekro_agent.api import core, i18n
from nekro_agent.api.core import logger
from nekro_agent.api.plugin import NekroPlugin, SandboxMethod, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.services.message_service import message_service

RCON_ERROR_PREFIXES = (
    "Unknown or incomplete command",
    "Incorrect argument",
    "Invalid player",
    "Player not found",
    "That player is not online",
    "You do not have permission to use this command",
    "Cannot give",
    "Invalid UUID",
    "No such entity",
    "That block is not a container",
    "Could not insert items",
    "Data tag parsing failed",
    "Expected",
    "Invalid command syntax",
    "An unexpected error occurred",
    "No targets matched selector",
    "The entity UUID is invalid",
    "Invalid command format",
)

plugin = NekroPlugin(
    name="Minecraft 工具插件",
    module_name="minecraft_utils",
    description="提供 Minecraft 适配器专用的消息发送和 RCON 命令执行功能。",
    version="0.1.0",
    author="Zaxpris",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["minecraft"],
    i18n_name=i18n.i18n_text(
        zh_CN="Minecraft 工具插件",
        en_US="Minecraft Utils Plugin",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="提供 Minecraft 适配器专用的消息发送和 RCON 命令执行功能",
        en_US="Provides Minecraft adapter utilities for message sending and RCON command execution",
    ),
)


def _llm_segment_dict_to_component(segment_dict: Dict[str, Any]) -> Component:
    """将 LLM 输出的单个富文本段字典转换为 Minecraft Component。

    仅支持颜色和字形样式（粗体、斜体、下划线、删除线、混淆）。
    """
    text = segment_dict.get("text", "")
    component_data: Dict[str, Any] = {"text": text}

    if "color" in segment_dict:
        try:
            component_data["color"] = Color(str(segment_dict["color"]).lower())
        except ValueError:
            logger.warning(f"[MinecraftUtils] 无效的文本颜色: {segment_dict['color']}")

    for style_attr in ["bold", "italic", "underlined", "strikethrough", "obfuscated"]:
        if style_attr in segment_dict:
            component_data[style_attr] = segment_dict[style_attr]

    return Component(**{k: v for k, v in component_data.items() if v is not None})


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送Minecraft富文本消息",
    description="向指定的Minecraft聊天发送富文本消息。LLM需要提供特定格式的JSON字符串。",
)
async def send_rich_text(_ctx: AgentCtx, chat_key: str, rich_text_json: str):
    """发送Minecraft富文本消息
    CAUTION: THIS METHOD IS USED FOR SENDING MESSAGES VIA MINECRAFT ADAPTER, NOT A MODEL CONTEXT PROTOCOL (MCP) SERVICE.
    Args:
        chat_key (str): Minecraft 服务器的频道标识 (例如 'minecraft-servername')。
        rich_text_json (str): 一个 JSON 字符串，表示一个消息段(segment)的列表。
            每个 segment 都是一个 JSON 对象，用于描述一段具有特定样式的文本。

    富文本 Segment JSON 对象支持的键:
        - `text` (str, 必选): 该段的文本内容。
        - `color` (str, 可选): 文本颜色。有效值:
          `"black"`, `"dark_blue"`, `"dark_green"`, `"dark_aqua"`, `"dark_red"`,
          `"dark_purple"`, `"gold"`, `"gray"`, `"dark_gray"`, `"blue"`, `"green"`,
          `"aqua"`, `"red"`, `"light_purple"`, `"yellow"`, `"white"`.
        - `bold` (bool, 可选): 文本是否加粗。
        - `italic` (bool, 可选): 文本是否斜体。
        - `underlined` (bool, 可选): 文本是否有下划线。
        - `strikethrough` (bool, 可选): 文本是否有删除线。
        - `obfuscated` (bool, 可选): 文本是否混淆显示 (随机字符)。

    示例 JSON 字符串:
    ```json
    [
        {"text": "欢迎来到 "},
        {"text": "我的世界!", "color": "gold", "bold": true},
        {"text": " 这是绿色斜体", "color": "green", "italic": true},
        {"text": " 这是红色下划线", "color": "red", "underlined": true}
    ]
    ```
    示例参数: `rich_text_json='[{"text": "你好", "color": "red"}, {"text": " 世界!", "bold": true}]'`
    """

    def _parse_and_validate_components(json_str: str) -> List[Component]:
        """解析并验证富文本JSON字符串，返回Component列表。"""
        try:
            segments_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"解析富文本 JSON 失败: {e}", exc_info=True)
            raise ValueError(f"富文本 JSON 格式错误: {e}") from e

        if not isinstance(segments_data, list):
            raise ValueError("富文本 JSON 解析后必须是一个列表。")  # noqa: TRY004

        parsed_components: List[Component] = []
        for seg_dict in segments_data:
            if isinstance(seg_dict, dict):
                component = _llm_segment_dict_to_component(seg_dict)
                parsed_components.append(component)
            else:
                logger.warning(
                    f"[MinecraftUtils] 富文本列表中的元素不是字典: {seg_dict}",
                )

        if not parsed_components:
            raise ValueError("没有可发送的有效富文本段。")
        return parsed_components

    if not isinstance(chat_key, str) or not chat_key.startswith("minecraft-"):
        raise ValueError("chat_key 无效，必须是 'minecraft-servername' 格式。")
    if not isinstance(rich_text_json, str) or not rich_text_json.strip():
        raise ValueError("富文本 JSON 字符串不能为空。")

    bot: Optional[Bot] = get_bot(chat_key)
    if not bot:
        raise ConnectionError(f"未能找到或连接到 Minecraft 服务器: {chat_key}")

    try:
        components = _parse_and_validate_components(rich_text_json)

        channel = await DBChatChannel.get_channel(chat_key)
        preset = await channel.get_preset()

        plain_text_parts = [c.text for c in components if c.text]
        plain_text_content = "".join(plain_text_parts)

        await message_service.push_bot_message(
            chat_key=chat_key,
            agent_messages=plain_text_content,
            db_chat_channel=channel,
        )
        prefix_component = Component(text=f"<{preset.name}>", color=Color.green)
        # 以单根组件 + extra 数组格式发送（标准 tellraw 格式）
        root_segment = MessageSegment.text(text="", extra=[prefix_component] + components)
        await bot.send_msg(message=root_segment)
        logger.info(f"Minecraft 富文本消息已发送到 {chat_key}")
    except ValueError as e:
        logger.error(f"处理富文本消息失败: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(
            f"发送 Minecraft 富文本消息到 {chat_key} 失败: {e}",
            exc_info=True,
        )
        raise Exception(f"发送 Minecraft 富文本消息失败: {e}") from e


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="批量执行Minecraft RCON命令",
    description="在指定的Minecraft服务器上批量执行RCON命令。",
)
async def execute_rcon_commands(
    _ctx: AgentCtx,
    chat_key: str,
    commands: List[str],
    continue_on_error: bool = False,
) -> str:
    """批量执行Minecraft RCON命令
    CAUTION: THIS METHOD IS USED FOR EXECUTING RCON COMMANDS VIA MINECRAFT ADAPTER, NOT A MODEL CONTEXT PROTOCOL (MCP) SERVICE.
    Args:
        chat_key (str): Minecraft 服务器的频道标识 (例如 'minecraft-servername')。
        commands (List[str]): 要执行的 RCON 命令列表。
        continue_on_error (bool, optional): 如果为 True，则在单个命令出错时继续执行后续命令，
                                        并将错误信息记录在对应命令的结果中。
                                        如果为 False (默认)，则在任何命令出错时立即停止，
                                        并返回错误信息及之前已成功执行的命令结果。

    Returns:
        str:
            RCON 命令的执行结果。
            如果 continue_on_error 为 True，返回所有命令结果的拼接字符串，错误会明确指出。
            如果 continue_on_error 为 False 且发生错误，则返回一个描述错误的字符串，包含出错命令和已成功的结果。
            如果 continue_on_error 为 False 且所有命令成功，则返回所有成功结果的拼接字符串。

    Examples:
        execute_rcon_commands(chat_key="minecraft-myserver", commands=["say Hello", "time set day"], continue_on_error=False)
        -> "Command 'say Hello': Hello\nCommand 'time set day': Set the time to 24000"

        execute_rcon_commands(chat_key="minecraft-myserver", commands=["say Hello", "invalid_command", "say World"], continue_on_error=False)
        -> "Error executing command 'invalid_command': <具体错误>\nPrevious results:\nCommand 'say Hello': Hello"

        execute_rcon_commands(chat_key="minecraft-myserver", commands=["say Hello", "invalid_command", "say World"], continue_on_error=True)
        -> "Command 'say Hello': Hello\nCommand 'invalid_command': Error - <具体错误>\nCommand 'say World': World"
    """
    if not isinstance(chat_key, str) or not chat_key.startswith("minecraft-"):
        raise ValueError("chat_key 无效，必须是 'minecraft-servername' 格式。")
    if not isinstance(commands, list) or not all(isinstance(cmd, str) and cmd.strip() for cmd in commands):
        raise ValueError("RCON 命令列表无效，必须是非空字符串的列表。")
    if not commands:
        raise ValueError("RCON 命令列表不能为空。")

    bot: Optional[Bot] = get_bot(chat_key)
    if not bot:
        # 以字符串形式返回错误，因为这是 Agent 类型方法
        return f"错误：未能找到或连接到 Minecraft 服务器: {chat_key}"

    results_log: List[str] = []  # 用于记录每个命令的文本结果或错误

    for command in commands:
        try:
            response = await bot.send_rcon_command(command=command)

            response_msg = ""
            if isinstance(response, str):
                response_msg = response.strip()

            is_error = response_msg and any(response_msg.startswith(prefix) for prefix in RCON_ERROR_PREFIXES)

            if is_error:
                error_message = f"在 {chat_key} 上执行 RCON 命令 '{command}' 失败: {response_msg}"
                logger.error(error_message)
                if not continue_on_error:
                    error_response = f"执行命令 '{command}' 时出错: {response_msg}"
                    if results_log:  # 如果之前有成功的结果
                        error_response += "\n先前成功的结果:\n" + "\n".join(results_log)
                    return error_response
                # 如果 continue_on_error 为 True，则记录错误并继续
                results_log.append(f"Command '{command}': Error - {response_msg}")
            else:
                # 命令成功执行
                result_str = response_msg if response_msg else "指令已成功执行，无返回内容"
                log_entry = f"Command '{command}': {result_str}"
                results_log.append(log_entry)
                logger.info(
                    f"RCON 命令 '{command}' 在 {chat_key} 上执行成功，响应: {result_str}",
                )

        except Exception as e:
            # 此处捕获的是网络错误等更底层的异常
            error_message = f"在 {chat_key} 上执行 RCON 命令 '{command}' 时发生意外: {e}"
            logger.error(error_message, exc_info=True)
            if not continue_on_error:
                error_response = f"执行命令 '{command}' 时出错: {e}"
                if results_log:  # 如果之前有成功的结果
                    error_response += "\n先前成功的结果:\n" + "\n".join(results_log)
                return error_response
            # 如果 continue_on_error 为 True，则记录错误并继续
            results_log.append(f"Command '{command}': Error - {e}")

    return "\n".join(results_log)
