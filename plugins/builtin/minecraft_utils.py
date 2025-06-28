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
from typing import Any, Dict, List, Optional, Union

from nonebot.adapters.minecraft import Bot, Message, MessageSegment
from nonebot.adapters.minecraft.model import (
    BaseComponent,
    ClickAction,
    ClickEvent,
    HoverAction,
    HoverEvent,
    TextColor,
    TextComponent,
)

from nekro_agent.adapters.minecraft.core.bot import get_bot
from nekro_agent.api import core
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
)


def _llm_segment_dict_to_text_component(segment_dict: Dict[str, Any]) -> TextComponent:
    """
    将 LLM 输出的单个富文本段字典转换为 Minecraft TextComponent。
    主要用于构建 HoverEvent.text 中的组件。
    """
    text = segment_dict.get("text", "")
    component_data: Dict[str, Any] = {"text": text}

    if "color" in segment_dict:
        try:
            component_data["color"] = TextColor(str(segment_dict["color"]).lower())
        except ValueError:
            logger.warning(
                f"[MinecraftUtils] 无效的悬停文本颜色: {segment_dict['color']}",
            )

    for style_attr in ["bold", "italic", "underlined", "strikethrough", "obfuscated"]:
        if style_attr in segment_dict:
            component_data[style_attr] = segment_dict[style_attr]

    if "insertion" in segment_dict:
        component_data["insertion"] = segment_dict["insertion"]

    click_action_str = segment_dict.get("click_event_action")
    click_value = segment_dict.get("click_event_value")
    if click_action_str and click_value:
        try:
            action = ClickAction(str(click_action_str).lower())
            component_data["click_event"] = ClickEvent(
                action=action,
                value=str(click_value),
            )
        except ValueError:
            logger.warning(
                f"[MinecraftUtils] 无效的悬停点击事件动作: {click_action_str}",
            )

    hover_action_str = segment_dict.get("hover_event_action")
    if hover_action_str:
        try:
            hover_action = HoverAction(str(hover_action_str).lower())
            if hover_action == HoverAction.SHOW_TEXT:
                hover_text_segments_data = segment_dict.get("hover_event_text_segments")
                if isinstance(hover_text_segments_data, list):
                    nested_hover_components: List[BaseComponent] = [
                        _llm_segment_dict_to_text_component(s) for s in hover_text_segments_data
                    ]
                    component_data["hover_event"] = HoverEvent(
                        action=hover_action,
                        text=nested_hover_components,
                    )
                else:
                    logger.warning(
                        "[MinecraftUtils] hover_event_text_segments 在悬停事件中缺失或非列表",
                    )
            # TODO: 支持其他 HoverAction (show_item, show_entity) 如果需要
        except ValueError:
            logger.warning(
                f"[MinecraftUtils] 无效的悬停事件动作: {hover_action_str}",
            )
    return TextComponent(**{k: v for k, v in component_data.items() if v is not None})


def _llm_segment_to_mc_message_segment(
    segment_dict: Dict[str, Any],
) -> Optional[MessageSegment]:
    """
    将 LLM 输出的单个富文本段字典转换为 Minecraft MessageSegment。
    """
    text = segment_dict.get("text")
    if text is None:  # 每个段必须有文本
        logger.warning("[MinecraftUtils] 富文本段缺少 'text' 键。")
        return None

    segment_args: Dict[str, Any] = {}

    if "color" in segment_dict:
        try:
            segment_args["color"] = TextColor(str(segment_dict["color"]).lower())
        except ValueError:
            logger.warning(
                f"[MinecraftUtils] 无效的文本颜色: {segment_dict['color']}",
            )

    for style_attr in ["bold", "italic", "underlined", "strikethrough", "obfuscated"]:
        if style_attr in segment_dict:
            segment_args[style_attr] = segment_dict[style_attr]

    if "insertion" in segment_dict:
        segment_args["insertion"] = segment_dict["insertion"]

    click_action_str = segment_dict.get("click_event_action")
    click_value = segment_dict.get("click_event_value")
    if click_action_str and click_value:
        try:
            action = ClickAction(str(click_action_str).lower())
            segment_args["click_event"] = ClickEvent(
                action=action,
                value=str(click_value),
            )
        except ValueError:
            logger.warning(
                f"[MinecraftUtils] 无效的点击事件动作: {click_action_str}",
            )

    hover_action_str = segment_dict.get("hover_event_action")
    if hover_action_str:
        try:
            hover_action = HoverAction(str(hover_action_str).lower())
            if hover_action == HoverAction.SHOW_TEXT:
                hover_text_segments_data = segment_dict.get("hover_event_text_segments")
                if isinstance(hover_text_segments_data, list):
                    hover_components: List[BaseComponent] = [
                        _llm_segment_dict_to_text_component(s_dict) for s_dict in hover_text_segments_data
                    ]
                    segment_args["hover_event"] = HoverEvent(
                        action=hover_action,
                        text=hover_components,
                    )
                else:
                    logger.warning(
                        "[MinecraftUtils] hover_event_text_segments 缺失或非列表",
                    )
            # TODO: 支持其他 HoverAction (show_item, show_entity) 如果需要
        except ValueError:
            logger.warning(
                f"[MinecraftUtils] 无效的悬停事件动作: {hover_action_str}",
            )

    return MessageSegment.text(str(text), **segment_args)


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送Minecraft富文本消息",
    description="向指定的Minecraft聊天发送富文本消息。LLM需要提供特定格式的JSON字符串。",
)
async def send_rich_text(_ctx: AgentCtx, chat_key: str, rich_text_json: str):
    """发送Minecraft富文本消息
    CAUTION: THIS METHOD IS USED FOR SENDING MESSAGES VIA MINECRAFT ADAPTER, NOT A MODEL CONTEXT PROTOCOL (MCP) SERVICE.
    Args:
        chat_key (str): Minecraft 服务器的会话标识 (例如 'minecraft-servername')。
        rich_text_json (str): 一个 JSON 字符串，表示一个消息段(segment)的列表。
            每个 segment 都是一个 JSON 对象，用于描述一段具有特定样式的文本及其交互行为。

    富文本 Segment JSON 对象支持的键:
        - `text` (str, 必选): 该段的文本内容。
        - `color` (str, 可选): 文本颜色。有效值是 TextColor 枚举的小写形式，例如:
          `"black"`, `"dark_blue"`, `"dark_green"`, `"dark_aqua"`, `"dark_red"`,
          `"dark_purple"`, `"gold"`, `"gray"`, `"dark_gray"`, `"blue"`, `"green"`,
          `"aqua"`, `"red"`, `"light_purple"`, `"yellow"`, `"white"`.
          默认为服务器的默认文本颜色。
        - `bold` (bool, 可选): 文本是否加粗。默认为 `false`。
        - `italic` (bool, 可选): 文本是否斜体。默认为 `false`。
        - `underlined` (bool, 可选): 文本是否有下划线。默认为 `false`。
        - `strikethrough` (bool, 可选): 文本是否有删除线。默认为 `false`。
        - `obfuscated` (bool, 可选): 文本是否混淆显示 (随机字符)。默认为 `false`。
        - `insertion` (str, 可选): 当玩家在聊天中点击这段文本时，插入到玩家聊天输入框的文本。
        - `click_event_action` (str, 可选): 点击事件的动作。必须与 `click_event_value` 一起使用。
          有效值 (ClickAction 枚举的小写形式):
            - `"open_url"`: 打开一个 URL。
            - `"open_file"`: 打开一个文件 (通常在客户端上，不推荐用于服务器消息)。
            - `"run_command"`: 以玩家身份执行一条命令。
            - `"suggest_command"`: 在玩家聊天输入框中建议一条命令 (玩家需手动发送)。
            - `"change_page"`: (仅用于书本中) 改变书本的页面。
            - `"copy_to_clipboard"`: 将指定文本复制到玩家的剪贴板。
        - `click_event_value` (str, 可选): 点击事件的值。根据 `click_event_action` 的不同而不同:
            - 对于 `"open_url"`, `"suggest_command"`, `"copy_to_clipboard"`: 对应的 URL、命令字符串或要复制的文本。
            - 对于 `"run_command"`: 要执行的命令 (通常需要以 `/` 开头)。
            - 对于 `"change_page"`: 页码。
        - `hover_event_action` (str, 可选): 鼠标悬停事件的动作。目前主要支持 `"show_text"`。
          必须与 `hover_event_text_segments` 一起使用。
          有效值 (HoverAction 枚举的小写形式):
            - `"show_text"`: 悬停时显示一段富文本。
            - `"show_item"`: (暂未完全支持通过此JSON格式配置) 悬停时显示物品信息。
            - `"show_entity"`: (暂未完全支持通过此JSON格式配置) 悬停时显示实体信息。
        - `hover_event_text_segments` (List[Dict], 可选): 当 `hover_event_action` 为 `"show_text"` 时使用。
          它本身是一个消息段 (segment) 对象的列表 (与顶层结构相同，但不建议嵌套过深的悬停事件)，
          用于定义鼠标悬停时显示的富文本内容。

    示例 JSON 字符串:
    ```json
    [
        {"text": "欢迎来到 "},
        {"text": "我的世界!", "color": "gold", "bold": true},
        {
            "text": " 点击这里访问官网",
            "color": "aqua",
            "underlined": true,
            "click_event_action": "open_url",
            "click_event_value": "https://www.minecraft.net"
        },
        {
            "text": " 或 ",
            "color": "gray"
        },
        {
            "text": "执行命令",
            "color": "light_purple",
            "italic": true,
            "click_event_action": "suggest_command",
            "click_event_value": "/help",
            "hover_event_action": "show_text",
            "hover_event_text_segments": [
                {"text": "点击后会在你的聊天框输入 ", "color": "yellow"},
                {"text": "/help", "color": "red", "bold": true}
            ]
        }
    ]
    ```
    注意: JSON 字符串在作为参数传递时，内部的双引号需要被正确转义，例如在Python字符串中表示为 `\"`。
    示例参数: `rich_text_json='[{"text": "你好", "color": "red"}, {"text": " 世界!", "bold": true}]'`
    """

    def _parse_and_validate_segments(json_str: str) -> List[MessageSegment]:
        """解析并验证富文本JSON字符串，返回MessageSegment列表。"""
        try:
            segments_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"解析富文本 JSON 失败: {e}", exc_info=True)
            raise ValueError(f"富文本 JSON 格式错误: {e}") from e

        if not isinstance(segments_data, list):
            raise ValueError("富文本 JSON 解析后必须是一个列表。")  # noqa: TRY004

        parsed_message_segments: List[MessageSegment] = []
        for seg_dict in segments_data:
            if isinstance(seg_dict, dict):
                mc_segment = _llm_segment_to_mc_message_segment(seg_dict)
                if mc_segment:
                    parsed_message_segments.append(mc_segment)
            else:
                logger.warning(
                    f"[MinecraftUtils] 富文本列表中的元素不是字典: {seg_dict}",
                )

        if not parsed_message_segments:
            raise ValueError("没有可发送的有效富文本段。")
        return parsed_message_segments

    if not isinstance(chat_key, str) or not chat_key.startswith("minecraft-"):
        raise ValueError("chat_key 无效，必须是 'minecraft-servername' 格式。")
    if not isinstance(rich_text_json, str) or not rich_text_json.strip():
        raise ValueError("富文本 JSON 字符串不能为空。")

    bot: Optional[Bot] = get_bot(chat_key)
    if not bot:
        raise ConnectionError(f"未能找到或连接到 Minecraft 服务器: {chat_key}")

    try:
        message_segments = _parse_and_validate_segments(rich_text_json)

        channel = await DBChatChannel.get_channel(chat_key)
        preset = await channel.get_preset()

        plain_text_parts = []
        for seg in message_segments:  # message_segments 是 _parse_and_validate_segments 的结果
            if hasattr(seg, "data") and isinstance(seg.data, dict) and "text" in seg.data:
                plain_text_parts.append(str(seg.data["text"]))
        plain_text_content = "".join(plain_text_parts)

        await message_service.push_bot_message(
            chat_key=chat_key,
            agent_messages=plain_text_content,  # 使用提取的纯文本
            db_chat_channel=channel,
        )
        message_segments.insert(0, MessageSegment.text(f"<{preset.name}>", color=TextColor.GREEN))
        message_to_send = Message(message_segments)
        await bot.send_msg(message=message_to_send)
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
        chat_key (str): Minecraft 服务器的会话标识 (例如 'minecraft-servername')。
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

    if not bot.rcon:
        return f"错误：Minecraft 服务器 {chat_key} 未配置或未连接 RCON。"

    results_log: List[str] = []  # 用于记录每个命令的文本结果或错误

    for command in commands:
        try:
            response = await bot.call_api("send_rcon_cmd", command=command)

            response_msg = ""
            if isinstance(response, tuple) and len(response) > 0 and isinstance(response[0], str):
                response_msg = response[0].strip()
            elif isinstance(response, str):
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
