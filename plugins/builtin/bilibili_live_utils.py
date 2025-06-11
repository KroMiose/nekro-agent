import json
import re
from typing import Any, Dict, List

from pydantic import Field

from nekro_agent.api import core
from nekro_agent.api.core import logger
from nekro_agent.api.plugin import (
    ConfigBase,
    NekroPlugin,
    SandboxMethod,
    SandboxMethodType,
)
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.message_service import message_service
from nekro_agent.tools.common_util import calculate_text_similarity

plugin = NekroPlugin(
    name="Bilibili 直播工具插件",
    module_name="bilibili_live_utils",
    description="提供 Bilibili 直播适配器专用的消息发送和Live2d模型设置等功能",
    version="0.1.0",
    author="Zaxpris",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["bilibili_live"],
)


@plugin.mount_config()
class BasicConfig(ConfigBase):
    """基础配置"""

    STRICT_MESSAGE_FILTER: bool = Field(
        default=False,
        title="启用严格重复消息过滤",
        description="启用后，完全重复的消息将直接抛出异常，否则仅过滤并提示",
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.7,
        title="消息相似度警告阈值",
        description="当消息相似度超过该阈值时，将触发系统警告提示引导 AI 调整生成策略",
    )
    SIMILARITY_CHECK_LENGTH: int = Field(
        default=12,
        title="启用消息相似度检查阈值",
        description="当消息长度超过该阈值时，将进行相似度检查",
    )


config: BasicConfig = plugin.get_config(BasicConfig)

# 消息缓存
SEND_MSG_CACHE: Dict[str, List[str]] = {}


def extract_expressions(json_data: Dict) -> str:
    """
    从 JSON 数据中提取并格式化表情详情（名称、文件、激活状态）。

    此函数在内部用于为 LLM 准备可用表情的列表。

    参数:
        json_data (Dict): 从 JSON 解析的字典，包含表情数据，通常来自 API 响应。期望的结构类似：`{"data": {"expressions": [{"name": "str", "file": "str", "active": bool}, ...]}}`。

    返回:
        str: 一个字符串，包含每个表情的名称、文件和激活状态，格式化以便于阅读（例如："开心 happy.exp3.json 激活\n伤心 sad.exp3.json 未激活"）。
        如果 'expressions' 数组缺失或为空，则返回 "未找到表情数据。"。
        如果 JSON 处理失败，则返回错误消息。
    """
    try:
        # 提取expressions数组
        expressions = json_data.get("data", {}).get("expressions", [])

        if not expressions:
            return "未找到表情数据。"

        result = []

        # 遍历表情数据并格式化
        for expression in expressions:
            name = expression.get("name", "未知")
            file = expression.get("file", "未知")
            active = "激活" if expression.get("active", False) else "未激活"

            result.append(f"{name} {file} {active}")

        return "\n".join(result)

    except json.JSONDecodeError:
        return "JSON 格式错误，请检查输入数据。"
    except Exception as e:
        return f"处理数据时出错：{e!s}"


def extract_sound_effects(json_data: Dict) -> str:
    """
    从 JSON 数据中提取并格式化音效列表。

    此函数在内部用于为 LLM 准备可用音效的列表。

    参数:
        json_data (Dict): 从 JSON 解析的字典，包含音效数据，通常来自 API 响应。期望的结构类似：`{"data": {"sounds": ["sound1.wav", "sound2.wav", ...]}}`。

    返回:
        str: 一个字符串，包含每个音效名称，每行一个。如果 'sounds' 数组缺失或为空，则返回 "未找到音效。".如果 JSON 处理失败，则返回错误消息。
    """
    try:
        # 提取sounds数组
        sounds = json_data.get("data", {}).get("sounds", [])

        if not sounds:
            return "未找到音效。"

        return "\n".join(sounds)

    except json.JSONDecodeError:
        return "JSON 格式错误，请检查输入数据。"
    except Exception as e:
        return f"处理数据时出错：{e!s}"


def extract_preformed_animations(json_data: Dict) -> str:
    try:
        animations = json_data.get("data", {}).get("animations", [])
        if not animations:
            return "没有可用的预制动画"

        result = []
        for animation in animations:
            name = animation.get("name", "未知")
            description = animation.get("description", "未知")
            result.append(f"动画名称: {name}，描述: {description}")

            params = animation.get("params", [])
            for param in params:
                p_name = param.get("name", "未知")
                p_desc = param.get("description", "未知")
                p_type = param.get("type", "unknown")
                p_default = param.get("default", "无默认值，必填")
                result.append(f"    - 参数: {p_name}，描述: {p_desc}，类型: {p_type}，默认值: {p_default}")

        return "\n".join(result)

    except Exception as e:
        return f"处理数据时出错：{e}"


def extract_estimated_completion_time(json_data: Dict) -> float:
    try:

        return json_data.get("data", {}).get("estimated_completion_time", 0.0)

    except json.JSONDecodeError:
        logger.warning("JSON 格式错误，请检查输入数据。")
        return 0.0
    except Exception as e:
        logger.warning(f"处理数据时出错：{e!s}")
        return 0.0


@plugin.mount_prompt_inject_method(name="basic_prompt_inject")
async def basic_prompt_inject(_ctx: AgentCtx):
    """
    将关于可用 Live2D 表情和音效的动态信息注入到代理的提示中。

    此方法从 Bilibili Live websocket 客户端获取当前可用的表情和音效列表，
    并将其格式化为提示字符串。这有助于 LLM 理解它可以使用哪些表情和音效
    以及对应的工具。
    """
    chat_key = _ctx.chat_key
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    avilable_expressions = "无可用表情"
    available_sound_effects = "无可用音效"
    available_preformed_animations = "无可用预制动画"
    if ws_client:
        # 获取表情数据
        msg = {
            "type": "get_expressions",
            "data": {},
        }
        avilable_expressions = await ws_client.send_animate_command(msg)
        avilable_expressions = extract_expressions(avilable_expressions)

        # 获取音效数据
        sound_msg = {
            "type": "get_sounds",
            "data": {},
        }
        available_sound_effects = await ws_client.send_animate_command(sound_msg)
        available_sound_effects = extract_sound_effects(available_sound_effects)

        preformed_msg = {
            "type": "list_preformed_animations",
            "data": {},
        }
        available_preformed_animations = await ws_client.send_animate_command(preformed_msg)
        available_preformed_animations = extract_preformed_animations(available_preformed_animations)
    basic_prompt = f"""
    Live2D 模型控制重要说明：
    1.像 `send_text_message`、`set_expression` 和 `play_preformed_animation` 这样的操作并不会立即执行。相反，它们会将任务添加到一个动画队列中，并会返回一个float，代表此任务从delay到执行结束后的总时间，你可以使用此值来精确控制动画的顺序。
    2.必须使用 `send_execute` 命令来执行队列中当前的所有任务。
    3.动画队列（由一系列任务后跟 `send_execute` 定义）会一个接一个地处理。只有在前一个队列完全完成后，新的队列才会开始。
    4.实现延迟和复杂序列：** 您可以通过以下方式创建复杂的动画序列：
        - 在单个任务函数（例如 `set_expression`、`play_preformed_animation`）中使用 `delay` 参数。
        - 策略性地放置 `send_execute` 调用来定义动画的各个片段。`send_execute` 调用之间的延迟实际上是前一个队列中任务的持续时间和延迟的总和。

    可用的预制动画:
    {available_preformed_animations}

    可用表情（格式：名称 文件 状态）：
    {avilable_expressions}

    要使用表情，请调用 `set_expression(_ck, "expression_file_name.exp3.json", duration, delay)`。
    示例：`set_expression(_ck, "Happy.exp3.json", 2.0, 0)` 将“开心”表情设置为持续 2 秒，无初始延迟。

    注意：上面列出的“表情”可能不仅仅包括面部表情。
    它们可以控制模型的其他部分，如道具（例如，枕头）或头发。
    你需要将表情与预制动画结合起来使用，以达到更好的效果。
    请参考列表以了解所有可用的可控表情资源。

    可用meme音效（用于创造节目效果）：
    {available_sound_effects}

    要播放音效，请调用 `play_sound(_ck, "sound_file_name.wav", volume, speed, delay)`。
    音效可以在直播期间创造更好的节目效果。
    但是您不能频繁使用它们，否则会影响直播。
    """
    return basic_prompt  # noqa: RET504


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送文本消息",
    description="发送聊天消息文本，附带缓存消息重复检查",
)
async def send_text_message(_ctx: AgentCtx, chat_key: str, message_text: str, tts_text: str):
    """
    为 Live2D 模型发送文本消息。

    此函数将 'say' 任务添加到动画队列中。当通过 `send_execute` 执行队列时，Live2D 模型将按说出这些文字并伴随文本转语音生成的音频。

    注意：
        - 此函数将任务添加到队列中。请调用 `send_execute` 来触发执行。
        - 此函数不会返回任何值

    参数:
        chat_key (str): 聊天的会话标识符，例如 "bilibili_live-ROOM_ID"。
        message_text (str): 字符串，用于展示字幕的文字，语言要求为中文，不能为空。
        tts_text (str): 字符串，用于文本转语音的文字，语言要求为日语，字符串中只能出现片假名和其他标点符号，不允许使用日文汉字，不能为空。

    返回:
        无
    """
    global SEND_MSG_CACHE

    # 检查消息列表是否为空或者长度不匹配
    if not message_text:
        raise Exception("错误：消息列表不能为空。")

    if not message_text.strip():
        raise Exception("错误：消息内容不能为空。")

    if not tts_text.strip():
        raise Exception("错误：文本转语音内容不能为空。")

    # 拒绝包含 [image:xxx...] 的图片消息
    if re.match(r"^.*\[image:.*\]$", message_text):
        raise Exception(
            "错误：不能直接发送图片消息，请使用 send_msg_file 方法发送图片/文件资源。",
        )

    # 初始化消息缓存
    if chat_key not in SEND_MSG_CACHE:
        SEND_MSG_CACHE[chat_key] = []

    recent_messages = SEND_MSG_CACHE[chat_key][-5:] if SEND_MSG_CACHE[chat_key] else []

    # 检查完全匹配
    if message_text in recent_messages:
        # 清空缓存允许再次发送
        SEND_MSG_CACHE[chat_key] = []
        if config.STRICT_MESSAGE_FILTER:
            raise Exception(
                "错误：最近已发送过相同的消息。请仔细阅读最近的聊天记录，检查是否发送了重复消息。请生成更有趣的回复。如果你完全确定有必要，可以重新发送。禁止刷屏！",
            )
        await message_service.push_system_message(
            chat_key=chat_key,
            agent_messages="系统提示：最近已发送过相同的消息。自动跳过此消息。请仔细阅读最近的聊天记录，检查是否发送了重复消息。如果你完全确定有必要，可以重新发送。禁止刷屏！",
            trigger_agent=False,
        )
        return

    # 检查相似度（仅对超过限定字符的消息进行检查）
    for recent_msg in recent_messages:
        similarity = calculate_text_similarity(message_text, recent_msg, min_length=config.SIMILARITY_CHECK_LENGTH)
        if similarity > config.SIMILARITY_THRESHOLD:
            # 发送系统消息提示避免类似内容
            logger.warning(f"[{chat_key}] 检测到相似度过高的消息: {similarity:.2f}")
            await message_service.push_system_message(
                chat_key=chat_key,
                agent_messages="系统提示：您发送的消息与最近发送的消息过于相似！您的回复应当保持有效性，而不是冗余和繁琐！",
                trigger_agent=False,
            )
            break

    # TODO: 在这里实现实际的消息发送逻辑
    # 此处预留给用户自行实现发送功能
    #推送消息到数据库
    await message_service.push_bot_message(
        chat_key=chat_key,
        agent_messages=message_text,
    )
    
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "say",
            "data": {
                "text": message_text,
                "tts_text": tts_text,
                "delay": 0.0,
            },
        }
        await ws_client.send_animate_command(msg)
    # 更新消息缓存
    SEND_MSG_CACHE[chat_key].append(message_text)
    SEND_MSG_CACHE[chat_key] = SEND_MSG_CACHE[chat_key][-10:]  # 保持最近10条消息


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="设置Live2d表情",
    description="设置Live2d表情",
)
async def set_expression(_ctx: AgentCtx, chat_key: str, expression: str, duration: float, delay: float) -> float:
    """
    设置特定的 Live2D 模型表情。

    此函数将 'emotion' 任务添加到动画队列中。当通过 `send_execute` 执行队列时，
    该表情将应用于 Live2D 模型。

    注意：
        - 此函数将任务添加到队列中。请调用 `send_execute` 来触发执行。

    参数:
        chat_key (str): 会话标识符，例如 "bilibili_live-ROOM_ID"。
        expression (str): 要设置的表情文件名（例如 "happy.exp3.json"）。请参考提示中提供的可用表情列表。
        duration (float): 表情应保持激活的持续时间（秒）。
        - 如果 `duration < 0`，表情将无限期持续。
        - 要关闭一个持续的表情，可以用 `duration = 0` 设置。
        delay (float): 在 `send_execute` 命令（或队列中的前一个任务）开始后，此表情任务开始前的延迟时间（秒）。

    返回:
        一个float值,代表设置的表情从delay到duration结束后持续的总时间，你可以使用此返回值来精确控制动画的顺序
    """

    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "expression",
            "data": {
                "name": expression,
                "duration": duration,
                "delay": delay,
            },
        }
        response = await ws_client.send_animate_command(msg)
        return extract_estimated_completion_time(response)
    return 0.0


# @plugin.mount_sandbox_method(
#     SandboxMethodType.TOOL,
#     name="设置模型面部参数",
#     description="设置模型面部参数",
# )
# async def set_model_face_params(
#     _ctx: AgentCtx,
#     chat_key: str,
#     parameter: str,
#     target: float,
#     duration: float,
#     delay: float,
#     easing: str,
# ) -> float:
#     """
#     设置或动画化特定的 Live2D 模型面部参数。

#     此函数将 'animation' 任务添加到动画队列中，以控制单个面部参数，
#     如嘴巴开合、眼睛眨动或头部角度。当通过 `send_execute` 执行队列时，
#     该参数将被动画化。

#     注意：
#         - 此函数将任务添加到队列中。请调用 `send_execute` 来触发执行。

#     参数:
#         chat_key (str): 会话标识符，例如 "bilibili_live-ROOM_ID"。
#         parameter (str): 要动画化的面部参数名称。请参见下方的“可用面部参数”。
#         target (float): 参数的目标值。有效范围取决于参数。
#         duration (float): 参数从当前值动画到 `target` 值所需的时间（秒）。
#         delay (float): 在 `send_execute` 命令（或队列中的前一个任务）开始后，此动画任务开始前的延迟时间（秒）。
#         easing (str): 用于动画的缓动函数。请参见下方的“可用缓动函数”。

#     可用缓动函数：
#         'linear', 'in_sine', 'out_sine', 'in_out_sine', 'in_back', 'out_back',
#         'in_out_back', 'in_elastic', 'out_elastic', 'in_out_elastic'

#     可用面部参数（及其典型范围）：
#         - 'MouthSmile': 0.0（嘴角向下）到 1.0（嘴角向上）
#         - 'MouthOpen': 0.0（闭合）到 1.0（完全张开）
#         - 'EyeOpenLeft': 0.0（完全睁开）到 1.0（完全闭合）
#         - 'EyeOpenRight': 0.0（完全睁开）到 1.0（完全闭合）
#         - 'Brows': 0.0（皱眉）到 1.0（扬眉）
#         - 'FaceAngleY': -30.0（向下看）到 30.0（向上看）
#         - 'FaceAngleX': -30.0（面向模型右侧）到 30.0（面向模型左侧）
#         - 'FaceAngleZ': -90.0（向模型右侧倾斜）到 90.0（向模型左侧倾斜）

#     您可以在一次 `send_execute` 之前组合多个 `set_model_face_params` 调用（以及其他任务）
#     来创建复杂的面部动画。

#     示例（先眨眼后微笑）：
#         # 阶段 1：眨左眼（持续0.3秒），然后微笑（持续0.3秒，在眨眼结束后开始）
#         set_model_face_params(_ck, "EyeOpenLeft", 1.0, 0.3, 0.0, "in_sine")  # 眨眼立即开始
#         set_model_face_params(_ck, "MouthSmile", 1.0, 0.3, 0.3, "in_sine") # 微笑在0.3秒后开始
#         send_execute(_ck, 1) # 执行此序列一次

#     返回:
#         一个float值,代表设置的参数动作从delay到duration结束后持续的总时间，你可以使用此返回值来精确控制动画的顺序
#     """
#     room_id = chat_key.replace("bilibili_live-", "")
#     ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
#     if ws_client:
#         msg = {
#             "type": "animation",
#             "data": {
#                 "parameter": parameter,
#                 "target": target,
#                 "duration": duration,
#                 "delay": delay,
#                 "easing": easing,
#             },
#         }
#         response = await ws_client.send_animate_command(msg)
#         return extract_estimated_completion_time(response)
#     return 0.0


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="播放音效",
    description="播放音效",
)
async def play_sound(_ctx: AgentCtx, chat_key: str, sound_name: str, volume: float, speed: float, delay: float) -> float:
    """
    播放一个音效。
    注意：
        - 此函数将任务添加到队列中。请调用 `send_execute` 来触发执行。
    参数:
        chat_key (str): 会话标识符，例如 "bilibili_live-ROOM_ID"。
        sound_name (str): 要播放的声音的路径。
        volume (float): 声音的音量（0.0-1.0）。
        speed (float): 声音的速度（0.0-1.0）。
        delay (float): 在 `send_execute` 命令（或队列中的前一个任务）开始后，此声音任务开始前的延迟时间（秒）。

    返回:
        一个float值,代表播放的音频从delay到结束持续的总时间，你可以使用此返回值来精确控制动画的顺序
    """
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "sound_play",
            "data": {
                "path": sound_name,
                "volume": volume,
                "speed": speed,
                "delay": delay,
            },
        }
        response = await ws_client.send_animate_command(msg)
        return extract_estimated_completion_time(response)
    return 0.0


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="播放预制动画",
    description="播放预制动画",
)
async def play_preformed_animation(_ctx: AgentCtx, chat_key: str, animation_name: str, params: Dict, delay: float) -> float:
    """
    播放一个预制动画。
    注意：
        - 此函数将任务添加到队列中。请调用 `send_execute` 来触发执行。
        - 此函数只作用于面部参数等，若要实现更好展示效果请搭配`set_model_face_params`使用
    参数:
        chat_key (str): 会话标识符，例如 "bilibili_live-ROOM_ID"。
        animation_name (str): 要播放的预制动画的名称。
        params (Dict): 预制动画的参数。dict的key为参数名称，value为参数值。
        delay (float): 在 `send_execute` 命令（或队列中的前一个任务）开始后，此预制动画任务开始前的延迟时间（秒）。

    返回:
        一个float值,代表播放的预制动画从开始到结束持续的总时间，你可以使用此返回值来精确控制动画的顺序

    示例:
        play_preformed_animation(
            _ck,
            "wink",
            {
                "duration": 0.5,
            },
            0.0
        )
    """
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "play_preformed_animation",
            "data": {
                "name": animation_name,
                "params": params,
                "delay": delay,
            },
        }
        response = await ws_client.send_animate_command(msg)
        return extract_estimated_completion_time(response)
    return 0.0


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送执行指令",
    description="发送执行指令",
)
async def send_execute(_ctx: AgentCtx, chat_key: str, loop: int):
    """
    执行所有已排队的 Live2D 动画任务。

    此函数触发执行自上次 `send_execute` 调用以来（或者如果从未调用过 `send_execute`，
    则从开始以来）已添加到动画队列中的所有 'say'、'emotion' 和 'animation' 任务。

    注意：
        - 此函数执行当前队列中的所有任务。

    参数:
        chat_key (str): 会话标识符，例如 "bilibili_live-ROOM_ID"。
        loop (int): 重复执行当前队列中整个任务序列的次数。例如，`loop=1` 将执行当前队列，然后再次执行它。值为 `0` 表示执行一次。

    行为：
        - 系统会等待上一个 `send_execute` 队列完全完成后才开始下一个队列。这允许创建不同的动画片段。
        - 如果 `loop` 大于 0，在此 `send_execute` 之前定义的所有任务集将重复 `loop` 次。

    返回:
        无
    """
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "execute",
            "data": {
                "loop": loop,
            },
        }
        await ws_client.send_animate_command(msg)


@plugin.mount_cleanup_method()
async def clean_up():
    """
    清理插件资源，特别是清除消息缓存。

    此函数通常在插件卸载或应用程序关闭时调用。
    它将 `SEND_MSG_CACHE` 重置为空字典。
    """
    global SEND_MSG_CACHE
    SEND_MSG_CACHE = {}
